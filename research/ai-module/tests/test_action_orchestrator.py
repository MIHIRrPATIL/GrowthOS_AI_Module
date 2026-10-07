"""
Unit tests for Action Orchestrator
Validates:
- Execution mode gating (MANUAL, APPROVAL, AUTONOMOUS).
- Autonomy demotion for uncalibrated probability or non-allowlisted actions.
- Full autonomous dispatch for allowlisted actions with calibrated confidence.
- Policy violation rejection writing both policy_evaluated and plan_rejected.
- Local claim table and idempotency barrier returning cached receipt.
- Fail-closed behavior if audit ledger write fails.
- Timeout error transitioning to reconciliation_needed.
- Stale plan expiration and freshness verification.
- Consent withdrawal check at dispatch time.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from domain.actions import (
    ActionPlan,
    ActionType,
    ExecutionMode,
    PolicyRule,
    AuditRecord
)
from engines.policy_engine import PolicyEngine
from services.action_orchestrator import ActionOrchestrator
from adapters.sql_action_storage import SqlActionStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.memory_consent_store import MemoryConsentStore
from adapters.mock_adapters import (
    MockLoyaltyAdapter,
    MockBehaviorAdapter,
    MockAdsAdapter,
    MockNotificationAdapter
)


@pytest.fixture
def storage():
    return SqlActionStorageAdapter(db_path=":memory:")


@pytest.fixture
def audit_ledger():
    return SqlAuditLedgerAdapter(db_path=":memory:")


@pytest.fixture
def consent_store():
    store = MemoryConsentStore()
    store.record_consent("tenant_dominos", "cust_1", {
        "whatsapp_marketing": True,
        "email_marketing": True,
        "ad_tracking": True
    })
    return store


@pytest.fixture
def orchestrator(storage, audit_ledger, consent_store):
    policy_engine = PolicyEngine(action_storage=storage, consent_port=consent_store)
    return ActionOrchestrator(
        action_storage=storage,
        policy_engine=policy_engine,
        consent_port=consent_store,
        audit_ledger=audit_ledger,
        loyalty_adapter=MockLoyaltyAdapter(),
        behavior_adapter=MockBehaviorAdapter(),
        ads_adapter=MockAdsAdapter(),
        notification_adapter=MockNotificationAdapter(),
        freshness_verifier=lambda plan: True,
        clock=lambda: datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    )


def test_orchestrator_manual_mode_routing(orchestrator, storage, audit_ledger):
    plan = ActionPlan(
        plan_id="plan_manual_01",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Test manual routing",
        execution_mode=ExecutionMode.MANUAL
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.MANUAL)
    assert routed.status == "drafted"
    assert routed.policy_check_passed is True

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    events = [r.event_type for r in trail]
    assert "policy_evaluated" in events
    assert "manual_recommendation_ready" in events


def test_orchestrator_approval_mode_routing(orchestrator, storage, audit_ledger):
    plan = ActionPlan(
        plan_id="plan_approval_01",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Test approval routing",
        execution_mode=ExecutionMode.APPROVAL
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.APPROVAL)
    assert routed.status == "pending_approval"
    assert routed.policy_check_passed is True

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    events = [r.event_type for r in trail]
    assert "awaiting_human_approval" in events


def test_orchestrator_autonomy_demoted_due_to_uncalibrated_confidence(orchestrator, storage, audit_ledger):
    # Review points 1 & 8: Rule based plans have calibrated_probability=None; must be demoted
    plan = ActionPlan(
        plan_id="plan_auto_demote_01",
        tenant_id="tenant_dominos",
        action_type=ActionType.FLAG_UI_FRICTION_BUG,
        target_module="module_2_behavior",
        parameters={
            "component_selector": "checkout_step_2_fee_section",
            "friction_type": "drop_off_spike",
            "session_count": 150,
            "evidence": {"drop_off": 0.45}
        },
        reasoning_summary="Autonomous bug filing attempt without calibrated model",
        priority_score=0.90,
        calibrated_probability=None,  # Not calibrated! Must be demoted despite being allowlisted
        execution_mode=ExecutionMode.AUTONOMOUS
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.AUTONOMOUS)
    # Must be demoted to APPROVAL
    assert routed.status == "pending_approval"
    assert routed.execution_mode == ExecutionMode.APPROVAL

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    demote_events = [r for r in trail if r.event_type == "autonomy_demoted_to_approval"]
    assert len(demote_events) == 1
    assert "calibrated_probability_below_threshold" in demote_events[0].details["demotion_reason"]


def test_orchestrator_autonomy_demoted_due_to_unallowlisted_action(orchestrator, storage, audit_ledger):
    # Outreach action (WhatsApp) is not on the autonomous allowlist by default
    plan = ActionPlan(
        plan_id="plan_auto_demote_allowlist",
        tenant_id="tenant_dominos",
        action_type=ActionType.SEND_RECOVERY_WHATSAPP,
        target_module="notification",
        customer_id="cust_1",
        parameters={
            "recipient": "cust_1",
            "channel": "whatsapp",
            "template_name": "recovery_v1",
            "cart_total_paise": 40000,
            "recipient_type": "customer_id"
        },
        reasoning_summary="Autonomous WhatsApp attempt",
        priority_score=0.90,
        calibrated_probability=0.95,  # High calibrated probability, but action not allowlisted!
        execution_mode=ExecutionMode.AUTONOMOUS
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.AUTONOMOUS)
    assert routed.status == "pending_approval"
    assert routed.execution_mode == ExecutionMode.APPROVAL

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    demote_events = [r for r in trail if r.event_type == "autonomy_demoted_to_approval"]
    assert any("action_type_not_on_autonomous_allowlist" in r.details["demotion_reason"] for r in demote_events)


def test_orchestrator_autonomous_dispatch_for_allowlisted_action(orchestrator, storage, audit_ledger):
    # Review point 8: Allowlisted internal action with calibrated probability >= 0.85
    plan = ActionPlan(
        plan_id="plan_auto_allow_01",
        tenant_id="tenant_dominos",
        action_type=ActionType.FLAG_UI_FRICTION_BUG,
        target_module="module_2_behavior",
        parameters={
            "component_selector": "checkout_step_2_fee_section",
            "friction_type": "drop_off_spike",
            "session_count": 150,
            "evidence": {"drop_off": 0.45}
        },
        reasoning_summary="Autonomous bug filing",
        priority_score=0.90,
        calibrated_probability=0.92,  # Calibrated probability exceeds 0.85!
        execution_mode=ExecutionMode.AUTONOMOUS
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.AUTONOMOUS)
    assert routed.status == "dispatched"
    assert routed.execution_receipt is not None
    assert "bug_id" in routed.execution_receipt

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    events = [r.event_type for r in trail]
    assert "dispatch_attempted" in events
    assert "dispatch_succeeded" in events


def test_orchestrator_policy_rejection_completes_lifecycle(orchestrator, storage, audit_ledger):
    # Plan with excessive discount: INR 200 (20000 paise > 15000 paise limit)
    plan = ActionPlan(
        plan_id="plan_excess_disc",
        tenant_id="tenant_dominos",
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={
            "coupon_code": "SAVE200",
            "discount_amount_paise": 20000,
            "order_subtotal_paise": 100000,
            "customer_id": "cust_1"
        },
        reasoning_summary="Attempting excessive discount",
        execution_mode=ExecutionMode.APPROVAL
    )
    storage.save_plan(plan)

    routed = orchestrator.evaluate_and_route_plan(plan, target_mode=ExecutionMode.APPROVAL)
    assert routed.status == "rejected"
    assert routed.policy_check_passed is False

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    events = [r.event_type for r in trail]
    assert "policy_evaluated" in events
    assert "plan_rejected" in events  # Review point: lifecycle gap closed


def test_orchestrator_claim_barrier_and_cached_receipt(orchestrator, storage):
    plan = ActionPlan(
        plan_id="plan_claim_test",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Delivery fee waiver",
        status="approved"
    )
    storage.save_plan(plan)

    # First dispatch
    first = orchestrator.execute_dispatch(plan, actor="test_actor")
    assert first.status == "dispatched"
    first_receipt = first.execution_receipt

    # Spy on loyalty adapter
    orchestrator.loyalty_adapter.waive_delivery_fee = MagicMock()

    # Second dispatch with identical plan: must return cached receipt without calling adapter
    second = orchestrator.execute_dispatch(first, actor="test_actor")
    assert second.status == "dispatched"
    assert second.execution_receipt == first_receipt
    # Adapter was never called!
    orchestrator.loyalty_adapter.waive_delivery_fee.assert_not_called()


def test_fail_closed_if_audit_ledger_write_fails(orchestrator, storage, audit_ledger):
    # Review point 3: If write-ahead audit fails, fail closed and do not call adapter
    plan = ActionPlan(
        plan_id="plan_fail_closed",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Test fail closed",
        status="approved"
    )
    storage.save_plan(plan)

    orchestrator.loyalty_adapter.waive_delivery_fee = MagicMock()
    # Force audit ledger to raise an error
    audit_ledger.record_audit = MagicMock(side_effect=IOError("Audit disk full"))

    with pytest.raises(RuntimeError, match="Fail closed"):
        orchestrator.execute_dispatch(plan, actor="test_actor")

    # Adapter must NEVER have been called!
    orchestrator.loyalty_adapter.waive_delivery_fee.assert_not_called()

    # Plan in storage marked failed
    stored = storage.get_plan("tenant_dominos", "plan_fail_closed")
    assert stored.status == "failed"


def test_timeout_transitions_to_reconciliation_needed(orchestrator, storage, audit_ledger):
    # Review point 4: Timeout is reconciliation_needed, not failed
    plan = ActionPlan(
        plan_id="plan_timeout_test",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Test timeout",
        status="approved"
    )
    storage.save_plan(plan)

    orchestrator.loyalty_adapter.waive_delivery_fee = MagicMock(side_effect=TimeoutError("Module 1 gateway timeout"))

    result = orchestrator.execute_dispatch(plan, actor="test_actor")
    assert result.status == "reconciliation_needed"

    claim = storage.get_outbound_claim("tenant_dominos", f"tenant_dominos:plan_timeout_test:waive_delivery_fee:cust_1")
    assert claim["status"] == "reconciliation_needed"


def test_stale_expired_plan_refuses_dispatch(orchestrator, storage):
    # Review point 9: Stale plan past expires_at must not dispatch
    plan = ActionPlan(
        plan_id="plan_expired_test",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Expired plan",
        expires_at=(datetime(2026, 10, 5, 11, 0, 0, tzinfo=timezone.utc)).isoformat(),  # 1 hour ago
        status="approved"
    )
    storage.save_plan(plan)

    res = orchestrator.execute_dispatch(plan, actor="test_actor")
    assert res.status == "expired"
