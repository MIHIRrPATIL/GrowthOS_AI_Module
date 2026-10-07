"""
Unit tests for mock outbound adapters and idempotency controls
"""

import pytest
from adapters.mock_adapters import (
    MockLoyaltyAdapter,
    MockBehaviorAdapter,
    MockAdsAdapter,
    MockNotificationAdapter,
    MockAuditLedgerAdapter,
)
from domain.actions import AuditRecord


def test_loyalty_adapter_dispatch_and_idempotency():
    loyalty = MockLoyaltyAdapter()
    idemp_key = "idemp_waiver_001"

    # First dispatch
    res1 = loyalty.waive_delivery_fee(
        customer_id="CUST-48291",
        fee_amount=60.0,
        points_deducted=60,
        idempotency_key=idemp_key
    )
    assert res1["status"] == "success"
    assert res1["fee_amount"] == 60.0
    assert len(loyalty.dispatched_fee_waivers) == 1

    # Duplicate replay dispatch with identical idempotency key
    res2 = loyalty.waive_delivery_fee(
        customer_id="CUST-48291",
        fee_amount=60.0,
        points_deducted=60,
        idempotency_key=idemp_key
    )
    assert res2["status"] == "duplicate_skipped"
    # Length must still be 1 (no duplicate deduction)
    assert len(loyalty.dispatched_fee_waivers) == 1

    # Test bonus points
    p_res = loyalty.grant_bonus_points(
        customer_id="CUST-48291",
        points=50,
        reason="Loyalty compensation",
        idempotency_key="idemp_points_001"
    )
    assert p_res["status"] == "success"
    assert len(loyalty.dispatched_point_grants) == 1


def test_behavior_adapter_telemetry_and_bugs():
    behavior = MockBehaviorAdapter()

    res = behavior.request_dense_telemetry(
        component_selector="#btnStartCheckout",
        duration_minutes=30,
        sample_rate=1.0
    )
    assert res["status"] == "active"
    assert len(behavior.dense_telemetry_requests) == 1

    bug = behavior.register_ui_friction_bug(
        component_selector="#btnStartCheckout",
        friction_type="user.rage_click",
        session_count=4,
        evidence={"clicks_per_window": 4}
    )
    assert bug["bug_id"].startswith("BUG-UX-")
    assert bug["status"] == "triaged"
    assert len(behavior.reported_ui_friction_bugs) == 1


def test_ads_adapter_audience_sync_and_budget_shift():
    ads = MockAdsAdapter()

    sync = ads.sync_audience_segment(
        segment_name="dormant_high_intent_carts",
        customer_identifiers=["CUST-48291", "CUST-10492"],
        target_platform="meta"
    )
    assert sync["audience_size"] == 2
    assert sync["status"] == "synced"
    assert len(ads.synced_audiences) == 1

    shift = ads.shift_campaign_budget(
        from_campaign_id="CAMP-UNDERPERF-01",
        to_campaign_id="CAMP-WEEKEND-STUDENTS",
        delta_amount_inr=5000.0,
        idempotency_key="idemp_shift_001"
    )
    assert shift["status"] == "applied"
    assert len(ads.budget_shifts) == 1

    # Idempotent replay check
    shift2 = ads.shift_campaign_budget(
        from_campaign_id="CAMP-UNDERPERF-01",
        to_campaign_id="CAMP-WEEKEND-STUDENTS",
        delta_amount_inr=5000.0,
        idempotency_key="idemp_shift_001"
    )
    assert shift2["status"] == "duplicate_skipped"
    assert len(ads.budget_shifts) == 1


def test_notification_adapter():
    notif = MockNotificationAdapter()

    msg = notif.send_recovery_message(
        recipient="+919876543210",
        channel="whatsapp",
        template_name="dominos_cart_recovery_fee_waiver",
        parameters={"name": "Rahul", "cart_total": 588, "points_used": 60},
        idempotency_key="idemp_msg_001"
    )
    assert msg["status"] == "delivered"
    assert len(notif.sent_messages) == 1

    # Replay check
    dup = notif.send_recovery_message(
        recipient="+919876543210",
        channel="whatsapp",
        template_name="dominos_cart_recovery_fee_waiver",
        parameters={"name": "Rahul", "cart_total": 588, "points_used": 60},
        idempotency_key="idemp_msg_001"
    )
    assert dup["status"] == "duplicate_skipped"
    assert len(notif.sent_messages) == 1


def test_audit_ledger_adapter():
    ledger = MockAuditLedgerAdapter()

    record1 = AuditRecord(
        tenant_id="ws_dominos_in",
        plan_id="plan_001",
        actor="ai_growth_brain",
        event_type="plan_drafted",
        details={"confidence": 0.94}
    )
    record2 = AuditRecord(
        tenant_id="ws_dominos_in",
        plan_id="plan_001",
        actor="human_merchant",
        event_type="plan_approved",
        details={"approver": "merchant_admin"}
    )
    record3 = AuditRecord(
        tenant_id="ws_dominos_in",
        plan_id="plan_002",
        actor="ai_growth_brain",
        event_type="plan_drafted",
        details={"confidence": 0.88}
    )

    ledger.record_audit(record1)
    ledger.record_audit(record2)
    ledger.record_audit(record3)

    assert len(ledger.get_audit_trail()) == 3
    filtered = ledger.get_audit_trail(plan_id="plan_001")
    assert len(filtered) == 2
    assert filtered[0].event_type == "plan_drafted"
    assert filtered[1].event_type == "plan_approved"
