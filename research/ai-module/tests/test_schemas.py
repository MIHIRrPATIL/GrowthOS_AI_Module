"""
Unit tests for tightened domain contracts, time windows, and mathematical grounding schemas.
Validates:
1. extra="forbid" and frozen=True strict enforcement.
2. Required tenant_id and vertical_template_id (fail-loud semantics).
3. Explicit UTC TimeWindow ordering and data watermark.
4. Exact numerator/denominator ratio consistency and computed delta_pct.
5. Zero division safety when prior_value == 0.
6. Dynamic flags_count on DigestReport.
"""

import pytest
from datetime import datetime, timezone, timedelta
import json
from pydantic import ValidationError

from domain.events import (
    EventEnvelope,
    PageMetadata,
    DeviceMetadata,
    ConsentState,
)
from domain.metrics import (
    MetricResult,
    DigestFlag,
    DigestReport,
    TimeWindow,
)
from domain.actions import (
    ActionType,
    ExecutionMode,
    PolicyRule,
    ActionPlan,
    AuditRecord,
)


def test_event_envelope_creation_and_strictness():
    # Valid instantiation requires tenant_id (or workspace_id alias)
    event = EventEnvelope(
        tenant_id="ws_dominos_in",
        event_name="product.viewed",
        customer_id="CUST-48291",
        properties={"product_id": "PRD-PIZZA-FARMHOUSE", "price": 459.00}
    )

    assert event.event_id.startswith("evt_")
    assert event.schema_version == "1.0.0"
    assert event.tenant_id == "ws_dominos_in"
    assert event.customer_id == "CUST-48291"
    assert event.get_idempotency_key() == event.event_id
    assert event.get_user_identifier() == "CUST-48291"
    assert event.consent.outreach is True

    # Missing tenant_id must fail loudly
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_name="product.viewed",
            customer_id="CUST-48291"
        )

    # Typo in field name must be rejected by extra="forbid"
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate({
            "tenant_id": "ws_dominos_in",
            "event_name": "product.viewed",
            "custmer_id": "CUST-48291",  # typo
        })


def test_time_window_validation():
    t_start = datetime(2026, 9, 25, 0, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, 0, 0, 0, tzinfo=timezone.utc)

    window = TimeWindow(start=t_start, end=t_end)
    assert window.start == t_start
    assert window.end == t_end

    # Invalid window: end == start must raise ValueError
    with pytest.raises(ValidationError):
        TimeWindow(start=t_start, end=t_start)

    # Invalid window: end < start must raise ValueError
    with pytest.raises(ValidationError):
        TimeWindow(start=t_end, end=t_start)

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        TimeWindow.model_validate({
            "start": t_start,
            "end": t_end,
            "extra_field": "bad",
        })


def test_metric_result_strictness_and_grounding():
    t_start = datetime(2026, 9, 25, 0, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, 0, 0, 0, tzinfo=timezone.utc)
    watermark = datetime(2026, 10, 2, 0, 5, 0, tzinfo=timezone.utc)
    calculated = datetime(2026, 10, 2, 0, 6, 0, tzinfo=timezone.utc)

    window = TimeWindow(start=t_start, end=t_end)

    # Checkout drop-off: 549 drop-offs out of 1240 checkout attempts = 0.4427419
    numerator = 549
    denominator = 1240
    computed_ratio = round(numerator / denominator, 6)

    metric = MetricResult(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        definition_version="v1.2.0",
        window=window,
        as_of=watermark,
        calculated_at=calculated,
        dimensions={"channel": "mobile_web", "city": "Mumbai"},
        numerator=numerator,
        denominator=denominator,
        value=computed_ratio,
        unit="ratio",
        sample_size=denominator,
        min_sample_met=True,
        evidence_ref="query_chk_drop_20261002_001"
    )

    assert metric.tenant_id == "ws_dominos_in"
    assert metric.vertical_template_id == "ecommerce"
    assert metric.numerator == 549
    assert metric.denominator == 1240
    assert metric.sample_size == 1240
    assert metric.value == 0.442742
    assert metric.unit == "ratio"
    assert metric.min_sample_met is True
    assert metric.evidence_ref == "query_chk_drop_20261002_001"

    # Missing tenant_id or vertical_template_id must fail loudly
    with pytest.raises(ValidationError):
        MetricResult(
            vertical_template_id="ecommerce",
            metric_name="checkout_drop_off_rate",
            definition_version="v1.2.0",
            window=window,
            as_of=watermark,
            calculated_at=calculated,
            value=0.44,
            unit="ratio",
            sample_size=1240,
            min_sample_met=True,
            evidence_ref="q1"
        )

    # Extra field forbidden check (e.g. timeframe instead of window)
    with pytest.raises(ValidationError):
        MetricResult.model_validate({
            "tenant_id": "ws_dominos_in",
            "vertical_template_id": "ecommerce",
            "metric_name": "checkout_drop_off_rate",
            "definition_version": "v1.2.0",
            "window": window,
            "as_of": watermark,
            "calculated_at": calculated,
            "value": 0.44,
            "unit": "ratio",
            "sample_size": 1240,
            "min_sample_met": True,
            "evidence_ref": "q1",
            "timeframe": "7d",  # forbidden extra field
        })

    # Model is frozen (immutable)
    with pytest.raises(ValidationError):
        metric.value = 0.50


def test_digest_flag_delta_computation_and_polarity():
    flagged_time = datetime(2026, 10, 2, 6, 0, 0, tzinfo=timezone.utc)

    # Hand Calculation:
    # current_value = 0.4427, prior_value = 0.3810
    # delta_pct = (0.4427 - 0.3810) / 0.3810 * 100 = 16.1942257...%
    current = 0.4427
    prior = 0.3810
    expected_delta = (current - prior) / prior * 100

    flag = DigestFlag(
        dedupe_key="ws_dominos_in:checkout_drop_off_rate:week_over_week:20260925-20261002",
        tenant_id="ws_dominos_in",
        metric_name="checkout_drop_off_rate",
        period="week_over_week",
        polarity="lower_is_better",
        current_value=current,
        prior_value=prior,
        current_sample_size=1240,
        prior_sample_size=1150,
        unit="ratio",
        threshold_pct=10.0,
        severity="medium",
        adverse=True,
        flagged_at=flagged_time,
        status="active"
    )

    assert flag.delta_pct is not None
    assert flag.delta_pct == pytest.approx(expected_delta, rel=1e-4)
    assert flag.delta_pct == pytest.approx(16.1942, rel=1e-3)
    assert flag.adverse is True
    assert flag.severity == "medium"
    assert flag.dedupe_key == "ws_dominos_in:checkout_drop_off_rate:week_over_week:20260925-20261002"

    # Prior value == 0 must compute delta_pct as None (undefined percentage delta)
    flag_zero_prior = DigestFlag(
        dedupe_key="ws_dominos_in:new_user_funnel:week_over_week:20260925-20261002",
        tenant_id="ws_dominos_in",
        metric_name="new_user_funnel",
        period="week_over_week",
        polarity="higher_is_better",
        current_value=0.25,
        prior_value=0.0,
        current_sample_size=100,
        prior_sample_size=0,
        unit="ratio",
        threshold_pct=10.0,
        severity="low",
        adverse=False,
        flagged_at=flagged_time
    )
    assert flag_zero_prior.delta_pct is None

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        DigestFlag.model_validate({
            "dedupe_key": "k1",
            "tenant_id": "ws_dominos_in",
            "metric_name": "checkout_drop_off_rate",
            "period": "week_over_week",
            "polarity": "lower_is_better",
            "current_value": current,
            "prior_value": prior,
            "current_sample_size": 1240,
            "prior_sample_size": 1150,
            "unit": "ratio",
            "threshold_pct": 10.0,
            "severity": "medium",
            "adverse": True,
            "flagged_at": flagged_time,
            "manual_override": True,  # forbidden extra field
        })


def test_digest_report_and_dynamic_flags_count():
    t1 = datetime(2026, 9, 25, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 2, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 18, tzinfo=timezone.utc)

    current_window = TimeWindow(start=t1, end=t2)
    prior_window = TimeWindow(start=t0, end=t1)
    gen_time = datetime(2026, 10, 2, 7, 0, tzinfo=timezone.utc)

    metric_curr = MetricResult(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        definition_version="v1.2.0",
        window=current_window,
        as_of=t2,
        calculated_at=gen_time,
        numerator=549,
        denominator=1240,
        value=549 / 1240,
        unit="ratio",
        sample_size=1240,
        min_sample_met=True,
        evidence_ref="ref_curr"
    )
    metric_prior = MetricResult(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        definition_version="v1.2.0",
        window=prior_window,
        as_of=t1,
        calculated_at=gen_time,
        numerator=438,
        denominator=1150,
        value=438 / 1150,
        unit="ratio",
        sample_size=1150,
        min_sample_met=True,
        evidence_ref="ref_prior"
    )

    flag = DigestFlag(
        dedupe_key="ws_dominos_in:checkout_drop_off_rate:week_over_week:20260925-20261002",
        tenant_id="ws_dominos_in",
        metric_name="checkout_drop_off_rate",
        period="week_over_week",
        polarity="lower_is_better",
        current_value=0.4427,
        prior_value=0.3810,
        current_sample_size=1240,
        prior_sample_size=1150,
        unit="ratio",
        threshold_pct=10.0,
        severity="medium",
        adverse=True,
        flagged_at=gen_time
    )

    report = DigestReport(
        report_id="rep_20261002_001",
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        period="week_over_week",
        current_window=current_window,
        prior_window=prior_window,
        threshold_pct=10.0,
        generated_at=gen_time,
        current_metrics={"checkout_drop_off_rate": metric_curr},
        prior_metrics={"checkout_drop_off_rate": metric_prior},
        flags=[flag]
    )

    assert report.report_id == "rep_20261002_001"
    assert report.flags_count == 1
    assert len(report.flags) == 1
    assert report.current_metrics["checkout_drop_off_rate"].value == pytest.approx(549 / 1240)
    assert report.prior_metrics["checkout_drop_off_rate"].value == pytest.approx(438 / 1150)


def test_policy_rule_boundaries():
    rule = PolicyRule(
        tenant_id="ws_dominos_in",
        max_discount_value_inr=150.0,
        max_discount_pct=25.0,
        contact_cooldown_hours=48,
        autonomous_confidence_threshold=0.85
    )

    assert rule.tenant_id == "ws_dominos_in"
    assert rule.max_discount_value_inr == 150.0
    assert rule.max_discount_pct == 25.0
    assert rule.contact_cooldown_hours == 48
    assert rule.require_customer_consent is True

    # Missing tenant_id must fail loudly
    with pytest.raises(ValidationError):
        PolicyRule(
            max_discount_value_inr=150.0
        )

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        PolicyRule.model_validate({
            "tenant_id": "ws_dominos_in",
            "unsupported_policy": "deny",
        })


def test_action_plan_lifecycle():
    plan = ActionPlan(
        tenant_id="ws_dominos_in",
        customer_id="CUST-48291",
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        parameters={"fee_amount": 60.0, "points_to_deduct": 60},
        reasoning_summary="Waive ₹60 fee for Gold member with ₹588 dormant cart",
        evidence_citations=["Checkout Step 2 drop-off = 44.27%", "Dwell time > 18s"],
        confidence_score=0.92,
        policy_check_passed=True,
        execution_mode=ExecutionMode.APPROVAL,
        status="pending_approval"
    )

    assert plan.plan_id.startswith("plan_")
    assert plan.tenant_id == "ws_dominos_in"
    assert plan.action_type == ActionType.WAIVE_DELIVERY_FEE
    assert plan.target_module == "module_1_loyalty"
    assert plan.confidence_score == 0.92
    assert plan.status == "pending_approval"
    assert len(plan.evidence_citations) == 2


def test_audit_record_creation():
    audit = AuditRecord(
        tenant_id="ws_dominos_in",
        plan_id="plan_abc123",
        actor="ai_growth_brain",
        event_type="plan_drafted",
        details={"confidence": 0.92, "action": "waive_delivery_fee"}
    )

    assert audit.audit_id.startswith("aud_")
    assert audit.tenant_id == "ws_dominos_in"
    assert audit.plan_id == "plan_abc123"
    assert audit.actor == "ai_growth_brain"
    assert audit.event_type == "plan_drafted"
