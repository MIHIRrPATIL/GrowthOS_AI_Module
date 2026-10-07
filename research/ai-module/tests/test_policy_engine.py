"""
Deterministic Unit Tests for PolicyEngine
Validates:
1. Exact integer paise financial limits (boundary 15000 paise passes; 15001 fails).
2. Fail-closed percentage discount check (missing subtotal rejected).
3. Fail-closed campaign budget shift check (missing daily budget rejected).
4. Cumulative daily discount spend limit.
5. Per-customer incentive frequency caps (anti-abuse holdouts).
6. Platform-level purpose-specific consent (WhatsApp, Email, Ad Tracking).
7. Contact cooldown window (48h).
8. TRAI/DPDP quiet hours enforcement (21:00 to 09:00 blocked).
9. Confidence score is not treated as a policy violation.
"""

import pytest
from datetime import datetime, timezone, timedelta

from domain.actions import (
    ActionPlan,
    PolicyRule,
    ActionType,
    ExecutionMode
)
from adapters.sql_action_storage import SqlActionStorageAdapter
from adapters.memory_consent_store import MemoryConsentStore
from engines.policy_engine import PolicyEngine


@pytest.fixture
def storage():
    adapter = SqlActionStorageAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


@pytest.fixture
def consent_store():
    return MemoryConsentStore()


@pytest.fixture
def engine(storage, consent_store):
    return PolicyEngine(action_storage=storage, consent_store=consent_store)


@pytest.fixture
def default_rule():
    return PolicyRule(
        tenant_id="tenant_dominos",
        rule_id="rule_001",
        version=1,
        max_discount_value_paise=15000,      # INR 150.00
        max_discount_pct=25.0,
        max_daily_budget_shift_pct=15.0,
        max_daily_discount_budget_paise=5000000, # INR 50,000.00
        contact_cooldown_hours=48,
        max_incentives_per_customer_30d=1,
        autonomous_confidence_threshold=0.85
    )


def test_financial_limit_delivery_fee_waiver(engine, default_rule):
    # Boundary: Exactly 15000 paise (INR 150.00) must PASS
    plan_valid = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount_paise": 15000},
        reasoning_summary="Waive fee at limit",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_valid = engine.evaluate(plan_valid, default_rule)
    assert res_valid.passed is True
    assert len(res_valid.violations) == 0

    # Boundary: 15001 paise (INR 150.01) must FAIL
    plan_exceeded = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount_paise": 15001},
        reasoning_summary="Waive fee over limit",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_exceeded = engine.evaluate(plan_exceeded, default_rule)
    assert res_exceeded.passed is False
    assert any("MAX_DISCOUNT_EXCEEDED" in v for v in res_exceeded.violations)

    # Invalid amount: 0 or negative
    plan_zero = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount_paise": 0},
        reasoning_summary="Zero fee",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_zero = engine.evaluate(plan_zero, default_rule)
    assert res_zero.passed is False
    assert any("INVALID_FEE_AMOUNT" in v for v in res_zero.violations)


def test_discount_coupon_subtotal_percentage_limit(engine, default_rule):
    # 20% discount (1000 paise on 5000 paise subtotal) passes 25% limit
    plan_ok = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        parameters={
            "coupon_code": "SAVE20",
            "discount_amount_paise": 1000,
            "order_subtotal_paise": 5000
        },
        reasoning_summary="20% coupon",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_ok = engine.evaluate(plan_ok, default_rule)
    assert res_ok.passed is True

    # 30% discount (1500 paise on 5000 paise subtotal) fails 25% limit
    plan_over = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        parameters={
            "coupon_code": "SAVE30",
            "discount_amount_paise": 1500,
            "order_subtotal_paise": 5000
        },
        reasoning_summary="30% coupon",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_over = engine.evaluate(plan_over, default_rule)
    assert res_over.passed is False
    assert any("MAX_DISCOUNT_PERCENT_EXCEEDED" in v for v in res_over.violations)

    # Missing order subtotal must fail closed
    plan_missing_subtotal = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        parameters={
            "coupon_code": "SAVE10",
            "discount_amount_paise": 1000
        },
        reasoning_summary="Missing subtotal",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_missing = engine.evaluate(plan_missing_subtotal, default_rule)
    assert res_missing.passed is False
    assert any("MISSING_ORDER_SUBTOTAL" in v for v in res_missing.violations)


def test_campaign_budget_shift_limit(engine, default_rule):
    # 10% shift (100,000 paise on 1,000,000 paise daily budget) passes 15% limit
    plan_ok = ActionPlan(
        tenant_id="tenant_dominos",
        action_type=ActionType.SHIFT_CAMPAIGN_BUDGET,
        target_module="module_3_ads",
        parameters={
            "from_campaign_id": "cmp_a",
            "to_campaign_id": "cmp_b",
            "delta_amount_paise": 100000,
            "current_daily_budget_paise": 1000000
        },
        reasoning_summary="10% shift",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_ok = engine.evaluate(plan_ok, default_rule)
    assert res_ok.passed is True

    # 20% shift fails 15% limit
    plan_over = ActionPlan(
        tenant_id="tenant_dominos",
        action_type=ActionType.SHIFT_CAMPAIGN_BUDGET,
        target_module="module_3_ads",
        parameters={
            "from_campaign_id": "cmp_a",
            "to_campaign_id": "cmp_b",
            "delta_amount_paise": 200000,
            "current_daily_budget_paise": 1000000
        },
        reasoning_summary="20% shift",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_over = engine.evaluate(plan_over, default_rule)
    assert res_over.passed is False
    assert any("MAX_BUDGET_SHIFT_EXCEEDED" in v for v in res_over.violations)

    # Missing campaign daily budget fails closed
    plan_missing = ActionPlan(
        tenant_id="tenant_dominos",
        action_type=ActionType.SHIFT_CAMPAIGN_BUDGET,
        target_module="module_3_ads",
        parameters={
            "from_campaign_id": "cmp_a",
            "to_campaign_id": "cmp_b",
            "delta_amount_paise": 50000
        },
        reasoning_summary="Missing daily budget",
        execution_mode=ExecutionMode.APPROVAL
    )
    res_missing = engine.evaluate(plan_missing, default_rule)
    assert res_missing.passed is False
    assert any("MISSING_CAMPAIGN_BUDGET" in v for v in res_missing.violations)


def test_cumulative_daily_discount_spend_limit(engine, storage, default_rule):
    # Rule daily limit is 5,000,000 paise (INR 50,000)
    rule_tight = default_rule.model_copy(update={"max_daily_discount_budget_paise": 100000}) # INR 1000 cap
    clock = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    date_key = "2026-10-05"

    # Seed existing daily spend of 90,000 paise
    storage.record_daily_spend("tenant_dominos", date_key, discount_paise=90000, budget_shifted_paise=0, timestamp=clock)

    # Plan with 15,000 paise discount pushes total to 105,000 paise (> 100,000) -> MUST FAIL
    plan = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount_paise": 15000},
        reasoning_summary="Fee waiver over cumulative budget",
        execution_mode=ExecutionMode.APPROVAL
    )
    res = engine.evaluate(plan, rule_tight, clock=clock)
    assert res.passed is False
    assert any("DAILY_DISCOUNT_BUDGET_EXCEEDED" in v for v in res.violations)


def test_customer_incentive_abuse_cap(engine, storage, default_rule):
    clock = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)

    # Seed an already dispatched fee waiver for cust_001 5 days ago
    past_plan = ActionPlan(
        tenant_id="tenant_dominos",
        plan_id="plan_past_001",
        customer_id="cust_001",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount_paise": 5000},
        reasoning_summary="Past waiver",
        status="dispatched",
        created_at=(clock - timedelta(days=5)).isoformat()
    )
    storage.save_plan(past_plan)

    # New plan for same customer within 30 days must be rejected (max 1 incentive per 30d)
    new_plan = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_001",
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        parameters={"coupon_code": "CODE", "discount_amount_paise": 5000, "order_subtotal_paise": 25000},
        reasoning_summary="Second incentive attempt",
        execution_mode=ExecutionMode.APPROVAL
    )
    res = engine.evaluate(new_plan, default_rule, clock=clock)
    assert res.passed is False
    assert any("CUSTOMER_INCENTIVE_LIMIT_REACHED" in v for v in res.violations)


def test_purpose_specific_consent_enforcement(engine, consent_store, default_rule):
    clock = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc) # 14:00 UTC = 19:30 IST (outside quiet hours)

    # 1. WhatsApp recovery: requires marketing=True and whatsapp=True
    plan_wa = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_wa_01",
        action_type=ActionType.SEND_RECOVERY_WHATSAPP,
        target_module="notification",
        parameters={"recipient": "+919876543210", "channel": "whatsapp", "template_name": "cart_rec", "cart_total_paise": 45000},
        reasoning_summary="WhatsApp recovery"
    )

    # Case A: Missing consent completely
    res_none = engine.evaluate(plan_wa, default_rule, clock=clock)
    assert res_none.passed is False
    assert any("MISSING_CUSTOMER_CONSENT" in v for v in res_none.violations)

    # Case B: Transactional only (whatsapp=True, marketing=False)
    consent_store.record_consent("tenant_dominos", "cust_wa_01", {"whatsapp": True, "marketing": False})
    res_no_mktg = engine.evaluate(plan_wa, default_rule, clock=clock)
    assert res_no_mktg.passed is False
    assert any("MISSING_CUSTOMER_CONSENT" in v for v in res_no_mktg.violations)

    # Case C: Valid consent (whatsapp=True, marketing=True)
    consent_store.record_consent("tenant_dominos", "cust_wa_01", {"whatsapp": True, "marketing": True})
    res_valid = engine.evaluate(plan_wa, default_rule, clock=clock)
    assert res_valid.passed is True


def test_contact_cooldown_enforcement(engine, storage, consent_store, default_rule):
    clock = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    consent_store.record_consent("tenant_dominos", "cust_cool_01", {"whatsapp": True, "marketing": True})

    # Seed outreach sent 10 hours ago
    storage.record_outreach(
        tenant_id="tenant_dominos",
        log_id="log_001",
        recipient_type="customer_id",
        recipient_id="cust_cool_01",
        channel="whatsapp",
        template_name="cart_rec",
        sent_at=(clock - timedelta(hours=10))
    )

    plan = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_cool_01",
        action_type=ActionType.SEND_RECOVERY_WHATSAPP,
        target_module="notification",
        parameters={"recipient": "+919876543210", "channel": "whatsapp", "template_name": "cart_rec", "cart_total_paise": 45000},
        reasoning_summary="WhatsApp cooldown check"
    )
    res = engine.evaluate(plan, default_rule, clock=clock)
    assert res.passed is False
    assert any("CONTACT_COOLDOWN_ACTIVE" in v for v in res.violations)


def test_quiet_hours_enforcement(engine, consent_store, default_rule):
    consent_store.record_consent("tenant_dominos", "cust_qh_01", {"whatsapp": True, "marketing": True})

    plan = ActionPlan(
        tenant_id="tenant_dominos",
        customer_id="cust_qh_01",
        action_type=ActionType.SEND_RECOVERY_WHATSAPP,
        target_module="notification",
        parameters={"recipient": "+919876543210", "channel": "whatsapp", "template_name": "cart_rec", "cart_total_paise": 45000},
        reasoning_summary="WhatsApp quiet hours check"
    )

    # 1. UTC 17:00 + 5.5 = 22:30 IST (10:30 PM) -> QUIET HOURS BLOCKED
    night_clock = datetime(2026, 10, 5, 17, 0, tzinfo=timezone.utc)
    res_night = engine.evaluate(plan, default_rule, clock=night_clock)
    assert res_night.passed is False
    assert any("QUIET_HOURS_RESTRICTION" in v for v in res_night.violations)

    # 2. UTC 02:00 + 5.5 = 07:30 IST (7:30 AM) -> QUIET HOURS BLOCKED
    early_clock = datetime(2026, 10, 5, 2, 0, tzinfo=timezone.utc)
    res_early = engine.evaluate(plan, default_rule, clock=early_clock)
    assert res_early.passed is False
    assert any("QUIET_HOURS_RESTRICTION" in v for v in res_early.violations)

    # 3. UTC 06:00 + 5.5 = 11:30 IST (11:30 AM) -> ALLOWED
    day_clock = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)
    res_day = engine.evaluate(plan, default_rule, clock=day_clock)
    assert res_day.passed is True


def test_confidence_is_not_a_policy_violation(engine, default_rule):
    # Confidence gating is handled in the orchestrator Mode Gate, NOT in the policy engine
    plan_low_conf = ActionPlan(
        tenant_id="tenant_dominos",
        action_type=ActionType.FLAG_UI_FRICTION_BUG,
        target_module="module_2_behavior",
        parameters={"component_selector": "#checkout_btn", "friction_type": "rage_clicks", "session_count": 5},
        reasoning_summary="Friction bug with 0.40 confidence",
        confidence_score=0.40,
        priority_score=0.40,
        execution_mode=ExecutionMode.AUTONOMOUS
    )
    res = engine.evaluate(plan_low_conf, default_rule)
    # Low confidence does NOT fail policy
    assert res.passed is True
    assert len(res.violations) == 0
