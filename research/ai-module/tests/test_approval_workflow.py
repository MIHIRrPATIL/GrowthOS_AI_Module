"""
Unit tests for Human Approval Workflow
Validates:
- End-to-end approval triggering validated state transition and dispatch.
- End-to-end plan rejection with reason logging.
- Optimistic locking preventing simultaneous double approvals.
- Role-based authorization checks for approvers.
- Multi-tenant boundary enforcement on approval attempts.
"""

import pytest
from datetime import datetime, timezone

from domain.actions import (
    ActionPlan,
    ActionType,
    ExecutionMode
)
from engines.policy_engine import PolicyEngine
from services.action_orchestrator import ActionOrchestrator
from services.approval_service import ApprovalService
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
    store.record_consent("tenant_dominos", "cust_1", {"whatsapp_marketing": True})
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


@pytest.fixture
def approval_service(storage, audit_ledger, orchestrator):
    return ApprovalService(
        action_storage=storage,
        audit_ledger=audit_ledger,
        orchestrator=orchestrator
    )


def test_human_approval_end_to_end(storage, audit_ledger, approval_service):
    # Setup pending plan
    plan = ActionPlan(
        plan_id="plan_to_approve",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Pending fee waiver",
        status="pending_approval",
        version=1
    )
    storage.save_plan(plan)

    # Human approves
    approved_plan = approval_service.approve_plan(
        tenant_id="tenant_dominos",
        plan_id="plan_to_approve",
        approver_id="usr_manager_1",
        approver_role="merchant_admin",
        expected_version=1
    )

    assert approved_plan.status == "dispatched"
    assert approved_plan.approved_by == "usr_manager_1"
    assert approved_plan.execution_receipt is not None

    # Audit records reflect approval and dispatch
    trail = audit_ledger.get_audit_trail("tenant_dominos")
    events = [r.event_type for r in trail]
    assert "plan_approved" in events
    assert "dispatch_attempted" in events
    assert "dispatch_succeeded" in events


def test_human_rejection_end_to_end(storage, audit_ledger, approval_service):
    plan = ActionPlan(
        plan_id="plan_to_reject",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Fee waiver",
        status="pending_approval",
        version=1
    )
    storage.save_plan(plan)

    rejected_plan = approval_service.reject_plan(
        tenant_id="tenant_dominos",
        plan_id="plan_to_reject",
        rejector_id="usr_manager_1",
        reason="Budget frozen by finance team",
        rejector_role="merchant_admin",
        expected_version=1
    )

    assert rejected_plan.status == "rejected"

    trail = audit_ledger.get_audit_trail("tenant_dominos")
    rejection_records = [r for r in trail if r.event_type == "plan_rejected"]
    assert len(rejection_records) == 1
    assert rejection_records[0].details["rejection_reason"] == "Budget frozen by finance team"


def test_concurrent_double_approval_optimistic_lock(storage, approval_service):
    # Review point 4: Two simultaneous approvals cannot both pass
    plan = ActionPlan(
        plan_id="plan_race_test",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Fee waiver",
        status="pending_approval",
        version=1
    )
    storage.save_plan(plan)

    # First approver succeeds
    approval_service.approve_plan(
        tenant_id="tenant_dominos",
        plan_id="plan_race_test",
        approver_id="usr_alice",
        approver_role="merchant_admin",
        expected_version=1
    )

    # Second approver attempting with expected_version=1 must be rejected by atomic lock
    with pytest.raises(RuntimeError, match="Concurrent modification"):
        approval_service.approve_plan(
            tenant_id="tenant_dominos",
            plan_id="plan_race_test",
            approver_id="usr_bob",
            approver_role="merchant_admin",
            expected_version=1
        )


def test_unauthorized_role_rejected(storage, approval_service):
    plan = ActionPlan(
        plan_id="plan_auth_test",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Fee waiver",
        status="pending_approval",
        version=1
    )
    storage.save_plan(plan)

    with pytest.raises(PermissionError, match="not authorized"):
        approval_service.approve_plan(
            tenant_id="tenant_dominos",
            plan_id="plan_auth_test",
            approver_id="usr_unauthorized",
            approver_role="viewer",
            expected_version=1
        )


def test_cross_tenant_approval_rejected(storage, approval_service):
    # Plan belongs to tenant_dominos
    plan = ActionPlan(
        plan_id="plan_dominos_01",
        tenant_id="tenant_dominos",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_1",
        parameters={"fee_amount_paise": 5000, "customer_id": "cust_1"},
        reasoning_summary="Fee waiver",
        status="pending_approval",
        version=1
    )
    storage.save_plan(plan)

    # Attempt approval under tenant_pizzahut must fail (not found)
    with pytest.raises(ValueError, match="not found"):
        approval_service.approve_plan(
            tenant_id="tenant_pizzahut",
            plan_id="plan_dominos_01",
            approver_id="usr_hacker",
            approver_role="merchant_admin",
            expected_version=1
        )
