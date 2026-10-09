"""
Unit & Integration Test Suite for Background Schedulers and Outbound Adapters
GrowthOS Module 4: AI Growth Brain

Validates:
1. HttpLoyaltyAdapter & HttpNotificationGatewayAdapter (HMAC, circuit breaker, idempotency)
2. IdleCartSweepWorker (Idle detection, identity resolution, propensity gating, orchestrator dispatch)
3. AttributionClosingWorker (24h window expiration, conversion tracking, incremental lift calculation)

Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import datetime, timezone, timedelta
import uuid
import httpx

from adapters.loyalty_waivers_adapter import HttpLoyaltyAdapter
from adapters.notification_gateway_adapter import HttpNotificationGatewayAdapter
from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_identity_resolver import SqlIdentityResolver
from adapters.sql_action_storage import SqlActionStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.memory_consent_store import MemoryConsentStore
from engines.policy_engine import PolicyEngine
from services.action_orchestrator import ActionOrchestrator
from services.idle_cart_sweep_worker import IdleCartSweepWorker, SweepReport
from services.attribution_closing_worker import AttributionClosingWorker, AttributionReport
from domain.events import EventEnvelope
from domain.actions import PolicyRule, ActionPlan, ActionType, ExecutionMode
from domain.identity import IdentityType


# ==============================================================================
# Outbound Adapters Tests
# ==============================================================================

def test_loyalty_adapter_offline_dispatch_and_idempotency():
    adapter = HttpLoyaltyAdapter(base_url=None)
    key = "idem_test_loyalty_01"

    receipt1 = adapter.waive_delivery_fee(
        customer_id="cust_101",
        fee_amount=50.0,
        points_deducted=0,
        idempotency_key=key
    )
    assert receipt1["status"] == "success"
    assert receipt1["customer_id"] == "cust_101"

    # Second dispatch with identical idempotency key returns cached receipt
    receipt2 = adapter.waive_delivery_fee(
        customer_id="cust_101",
        fee_amount=50.0,
        points_deducted=0,
        idempotency_key=key
    )
    assert receipt2["waiver_id"] == receipt1["waiver_id"]


def test_loyalty_adapter_circuit_breaker_trip():
    # Configure adapter pointing to a non-existent endpoint with 2 failure threshold
    adapter = HttpLoyaltyAdapter(
        base_url="http://localhost:59999",
        circuit_breaker_threshold=2,
        circuit_breaker_reset_seconds=30.0,
        timeout_seconds=0.2
    )

    # 1st failure
    with pytest.raises(Exception):
        adapter.waive_delivery_fee("cust_101", 50.0, 0, "key_cb_1")

    # 2nd failure trips circuit breaker
    with pytest.raises(Exception):
        adapter.waive_delivery_fee("cust_101", 50.0, 0, "key_cb_2")

    # 3rd call immediately rejected by open circuit breaker
    with pytest.raises(RuntimeError) as exc_info:
        adapter.waive_delivery_fee("cust_101", 50.0, 0, "key_cb_3")
    assert "Circuit breaker OPEN" in str(exc_info.value)


def test_notification_gateway_offline_dispatch_and_phone_hashing():
    adapter = HttpNotificationGatewayAdapter(base_url=None)
    key = "idem_test_notif_01"

    receipt = adapter.send_recovery_message(
        recipient="+919876543210",
        channel="whatsapp",
        template_name="abandoned_cart_reminder",
        parameters={"cart_url": "https://store.growthos.io/cart"},
        idempotency_key=key
    )
    assert receipt["status"] == "delivered"
    assert receipt["channel"] == "whatsapp"
    assert receipt["recipient_masked"] == "***3210"
    assert len(receipt["recipient_hash"]) == 16


# ==============================================================================
# Idle Cart Sweep Worker Tests
# ==============================================================================

@pytest.fixture
def sweep_environment():
    tenant_id = "tenant_sweep_test"
    event_storage = SqlEventStorageAdapter(":memory:")
    identity_resolver = SqlIdentityResolver(":memory:")
    action_storage = SqlActionStorageAdapter(":memory:")
    audit_ledger = SqlAuditLedgerAdapter(":memory:")
    consent_store = MemoryConsentStore()
    policy_engine = PolicyEngine(action_storage=action_storage)
    loyalty_adapter = HttpLoyaltyAdapter(base_url=None)
    notif_adapter = HttpNotificationGatewayAdapter(base_url=None)

    # Save policy rule with waive_delivery_fee permitted for autonomous execution
    rule = PolicyRule(
        tenant_id=tenant_id,
        autonomous_action_allowlist=["waive_delivery_fee", "send_recovery_whatsapp"],
        autonomous_confidence_threshold=0.70
    )
    action_storage.save_policy_rule(rule)

    orchestrator = ActionOrchestrator(
        action_storage=action_storage,
        policy_engine=policy_engine,
        consent_port=consent_store,
        audit_ledger=audit_ledger,
        loyalty_adapter=loyalty_adapter,
        behavior_adapter=None,
        ads_adapter=None,
        notification_adapter=notif_adapter
    )

    worker = IdleCartSweepWorker(
        event_storage=event_storage,
        identity_resolver=identity_resolver,
        orchestrator=orchestrator
    )

    return {
        "tenant_id": tenant_id,
        "event_storage": event_storage,
        "identity_resolver": identity_resolver,
        "action_storage": action_storage,
        "audit_ledger": audit_ledger,
        "worker": worker
    }


def test_idle_cart_sweep_identifies_and_dispatches_eligible_cart(sweep_environment):
    env = sweep_environment
    tenant_id = env["tenant_id"]
    now = datetime(2026, 10, 9, 14, 0, 0, tzinfo=timezone.utc)

    # Register canonical identity
    env["identity_resolver"].link_identities(
        tenant_id=tenant_id,
        source_type="anonymous_id",
        source_id="anon_user_1",
        target_type="customer_id",
        target_id="cust_user_1",
        link_reason="login"
    )

    # Ingest cart events idle for 25 minutes (occurred at 13:35)
    cart_time = now - timedelta(minutes=25)
    env["event_storage"].store_event(
        EventEnvelope(
            tenant_id=tenant_id,
            event_id="evt_view_1",
            project_id="proj_1",
            source_module="web",
            event_name="product_viewed",
            occurred_at=(cart_time - timedelta(minutes=5)).isoformat(),
            received_at=(cart_time - timedelta(minutes=5)).isoformat(),
            session_id="sess_eligible_01",
            anonymous_id="anon_user_1",
            customer_id="cust_user_1"
        )
    )
    env["event_storage"].store_event(
        EventEnvelope(
            tenant_id=tenant_id,
            event_id="evt_cart_1",
            project_id="proj_1",
            source_module="web",
            event_name="add_to_cart",
            occurred_at=cart_time.isoformat(),
            received_at=cart_time.isoformat(),
            session_id="sess_eligible_01",
            anonymous_id="anon_user_1",
            customer_id="cust_user_1",
            properties={
                "cart_total_paise": 65000, # INR 650 (qualifies for waiver)
                "funnel_stage": "cart_drawer"
            }
        )
    )

    # Ingest anonymous unauthenticated guest cart (should be suppressed by Invariant 14)
    env["event_storage"].store_event(
        EventEnvelope(
            tenant_id=tenant_id,
            event_id="evt_cart_anon",
            project_id="proj_1",
            source_module="web",
            event_name="add_to_cart",
            occurred_at=cart_time.isoformat(),
            received_at=cart_time.isoformat(),
            session_id="sess_anon_02",
            anonymous_id="anon_unknown_99",
            customer_id=None,
            properties={"cart_total_paise": 55000}
        )
    )

    # Execute Sweep
    report = env["worker"].sweep_tenant(tenant_id=tenant_id, as_of=now)
    assert isinstance(report, SweepReport)
    assert report.scanned_sessions_count == 2
    assert report.suppressed_anonymous_count == 1
    assert report.eligible_sessions_count == 1
    assert (report.dispatched_plans_count + report.holdout_plans_count) == 1


# ==============================================================================
# Attribution Closing Worker Tests
# ==============================================================================

def test_attribution_closing_worker_measures_lift():
    tenant_id = "tenant_attr_test"
    event_storage = SqlEventStorageAdapter(":memory:")
    action_storage = SqlActionStorageAdapter(":memory:")
    audit_ledger = SqlAuditLedgerAdapter(":memory:")

    closing_worker = AttributionClosingWorker(
        action_storage=action_storage,
        event_storage=event_storage,
        audit_ledger=audit_ledger,
        attribution_window_hours=24.0
    )

    now = datetime(2026, 10, 9, 14, 0, 0, tzinfo=timezone.utc)
    t_minus_26h = now - timedelta(hours=26)
    t_minus_20h = now - timedelta(hours=20)

    # 1. Dispatched Plan that converted within 24h
    plan_conv = ActionPlan(
        plan_id="plan_dispatched_conv",
        tenant_id=tenant_id,
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_001",
        parameters={"fee_amount": 50.0},
        reasoning_summary="Test conversion",
        priority_score=0.8,
        signal_dedupe_key="sig_001",
        execution_mode=ExecutionMode.AUTONOMOUS,
        status="dispatched",
        dispatched_at=t_minus_26h.isoformat(),
        created_at=t_minus_26h.isoformat(),
        is_holdout=False
    )
    action_storage.save_plan(plan_conv)

    # Add order completed event for cust_001 at t - 20h (within 24h of dispatch)
    event_storage.store_event(
        EventEnvelope(
            tenant_id=tenant_id,
            event_id="evt_order_001",
            project_id="proj_1",
            source_module="web",
            event_name="order_completed",
            occurred_at=t_minus_20h.isoformat(),
            received_at=t_minus_20h.isoformat(),
            session_id="sess_order_01",
            anonymous_id="anon_001",
            customer_id="cust_001"
        )
    )

    # 2. Dispatched Plan that did NOT convert (expired)
    plan_exp = ActionPlan(
        plan_id="plan_dispatched_exp",
        tenant_id=tenant_id,
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_002",
        parameters={"fee_amount": 50.0},
        reasoning_summary="Test expiry",
        priority_score=0.8,
        signal_dedupe_key="sig_002",
        execution_mode=ExecutionMode.AUTONOMOUS,
        status="dispatched",
        dispatched_at=t_minus_26h.isoformat(),
        created_at=t_minus_26h.isoformat(),
        is_holdout=False
    )
    action_storage.save_plan(plan_exp)

    # 3. Holdout Plan that did NOT convert
    plan_hold = ActionPlan(
        plan_id="plan_holdout_exp",
        tenant_id=tenant_id,
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        customer_id="cust_003",
        parameters={"fee_amount": 50.0},
        reasoning_summary="Test holdout",
        priority_score=0.8,
        signal_dedupe_key="sig_003",
        execution_mode=ExecutionMode.AUTONOMOUS,
        status="holdout",
        created_at=t_minus_26h.isoformat(),
        is_holdout=True
    )
    action_storage.save_plan(plan_hold)

    # Close attribution
    report = closing_worker.close_attribution(tenant_id=tenant_id, as_of=now)
    assert isinstance(report, AttributionReport)
    assert report.evaluated_plans_count == 3
    assert report.treated_converted_count == 1
    assert report.treated_expired_count == 1
    assert report.holdout_converted_count == 0
    assert report.holdout_expired_count == 1
    # Treated rate = 1/2 = 50%, Holdout rate = 0/1 = 0% -> Lift = +50%
    assert report.treated_conversion_rate == 0.50
    assert report.holdout_conversion_rate == 0.00
    assert report.incremental_lift_pct == 50.0

    # Verify updated plan statuses
    p1 = action_storage.get_plan(tenant_id, "plan_dispatched_conv")
    assert p1.status == "converted"
    p2 = action_storage.get_plan(tenant_id, "plan_dispatched_exp")
    assert p2.status == "expired"
    p3 = action_storage.get_plan(tenant_id, "plan_holdout_exp")
    assert p3.status == "holdout_expired"
