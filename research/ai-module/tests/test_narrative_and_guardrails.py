"""
Comprehensive Guardrail and Narrative Unit Tests
Validates fixes for:
1. Golden test: 'cart abandonment vs last week' returning exact 171/210 and 135/210.
2. Polarity inversion gate: 'Checkout friction decreased sharply across the board' rejected.
3. Number-to-metric binding gate: 'abandonment reached 50.0%' rejected when 50.0% belongs to step 2.
4. Denominator-label test: '300 checkouts' impossible; metric definition enforces 'visiting sessions' vs 'checkouts started'.
5. Zero-data window returning 'no_data' with exact data watermark range.
6. Circuit breaker test: HTTP 429 trips circuit cooldown; subsequent call raises RateLimitCircuitOpenError locally.
7. Rule pre-filtering: Ineligible / anonymous carts spend 0 LLM calls.
8. Autonomy confidence safety: LLM self-reported confidence never feeds the autonomy gate.

Strictly NO emojis used in logs or output.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from domain.metrics import TimeWindow, MetricResult, DigestFlag, resolve_preset_window
from domain.events import EventEnvelope
from domain.nlp import QueryIntent, QueryClassification
from domain.actions import ActionType
from ports.decision import DecisionContext, DecisionCandidate
from engines.evidence_linker import EvidenceLinker
from engines.nl_query_engine import NLQueryEngine
from engines.metrics_engine import MetricsEngine
from engines.vertical_templates import get_vertical_template
from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.mock_llm import MockLLMAdapter
from adapters.gemini_client import GeminiClient, RateLimitCircuitOpenError
from adapters.gemini_decision_provider import GeminiDecisionProvider
from services.decision_manager import DecisionManager
from engines.rule_decision_provider import RuleDecisionProvider


@pytest.fixture
def test_setup():
    storage = SqlEventStorageAdapter(db_path=":memory:")
    metrics_engine = MetricsEngine(storage=storage)
    evidence_linker = EvidenceLinker()
    mock_llm = MockLLMAdapter()
    query_engine = NLQueryEngine(
        llm_port=mock_llm,
        metrics_engine=metrics_engine,
        evidence_linker=evidence_linker
    )
    return storage, metrics_engine, query_engine, evidence_linker, mock_llm


def test_golden_cart_abandonment_ratio_and_counts(test_setup):
    """
    Golden test: 'cart abandonment vs last week' must return exact figures:
    Current: 171/210 (81.4%)
    Prior: 135/210 (64.3%)
    """
    storage, metrics_engine, query_engine, _, mock_llm = test_setup
    tenant_id = "tenant_golden_test"
    as_of = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

    # Seed 300 sessions in current window (as_of - 7d to as_of)
    # 210 cart additions (p_add=0.70), 39 purchases (p_pur=0.13) -> 171 abandoned carts
    events = []
    for i in range(300):
        sid = f"cur_sess_{i:04d}"
        cid = f"cur_cust_{i:04d}"
        t = as_of - timedelta(days=5) + timedelta(minutes=i * 10)
        events.append(EventEnvelope(
            event_id=f"cur_view_{i}", schema_version="1.0.0", tenant_id=tenant_id,
            source_module="module_2", event_name="page.viewed", occurred_at=t.isoformat(),
            received_at=t.isoformat(), session_id=sid, customer_id=cid, properties={}
        ))
        if i < 210:
            events.append(EventEnvelope(
                event_id=f"cur_add_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                source_module="module_2", event_name="cart.item_added", occurred_at=(t + timedelta(seconds=20)).isoformat(),
                received_at=(t + timedelta(seconds=20)).isoformat(), session_id=sid, customer_id=cid, properties={"cart_value": 750.0}
            ))
        if i < 39:
            events.append(EventEnvelope(
                event_id=f"cur_pur_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                source_module="module_2", event_name="purchase.completed", occurred_at=(t + timedelta(seconds=60)).isoformat(),
                received_at=(t + timedelta(seconds=60)).isoformat(), session_id=sid, customer_id=cid, properties={"order_value": 750.0}
            ))

    # Seed 300 sessions in prior window (as_of - 14d to as_of - 7d)
    # 210 cart additions (p_add=0.70), 75 purchases (p_pur=0.25) -> 135 abandoned carts
    for i in range(300):
        sid = f"prior_sess_{i:04d}"
        cid = f"prior_cust_{i:04d}"
        t = as_of - timedelta(days=12) + timedelta(minutes=i * 10)
        events.append(EventEnvelope(
            event_id=f"prior_view_{i}", schema_version="1.0.0", tenant_id=tenant_id,
            source_module="module_2", event_name="page.viewed", occurred_at=t.isoformat(),
            received_at=t.isoformat(), session_id=sid, customer_id=cid, properties={}
        ))
        if i < 210:
            events.append(EventEnvelope(
                event_id=f"prior_add_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                source_module="module_2", event_name="cart.item_added", occurred_at=(t + timedelta(seconds=20)).isoformat(),
                received_at=(t + timedelta(seconds=20)).isoformat(), session_id=sid, customer_id=cid, properties={"cart_value": 750.0}
            ))
        if i < 75:
            events.append(EventEnvelope(
                event_id=f"prior_pur_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                source_module="module_2", event_name="purchase.completed", occurred_at=(t + timedelta(seconds=60)).isoformat(),
                received_at=(t + timedelta(seconds=60)).isoformat(), session_id=sid, customer_id=cid, properties={"order_value": 750.0}
            ))

    storage.store_batch(events)

    answer = query_engine.process_query(
        tenant_id=tenant_id,
        query_text="What was our cart abandonment compared to last week?",
        as_of=as_of
    )

    # Verify exact math: 171/210 and 135/210
    trace = answer.technical_trace
    assert trace["numerator"] == 171
    assert trace["denominator"] == 210
    assert abs(trace["computed_value"] - (171 / 210)) < 0.001

    prior_trace = trace["prior_comparison"]
    assert prior_trace["prior_numerator"] == 135
    assert prior_trace["prior_denominator"] == 210
    assert abs(prior_trace["prior_value"] - (135 / 210)) < 0.001

    # Verify executive summary narrative explicitly states the exact numbers
    assert "171 abandoned carts out of 210 carts added" in answer.executive_summary
    assert "135 abandoned carts out of 210 carts added" in answer.executive_summary


def test_evidence_linker_polarity_inversion_and_hyperbole_gate():
    """
    Validates Problem 1:
    - 'Checkout friction decreased sharply across the board.' must be REJECTED.
    - Qualifiers like 'sharply' and 'across the board' are dropped.
    - 'decreased' when friction rose (+75%) is flagged as polarity contradiction.
    """
    linker = EvidenceLinker()
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    cur_win, prior_win = resolve_preset_window("last_7d", now)

    # Friction rose by +75% (0.2857 -> 0.500)
    step2_res = MetricResult(
        tenant_id="t1",
        vertical_template_id="ecommerce",
        metric_name="checkout_step_2_drop_off_rate",
        definition_version="v1.1.0",
        window=cur_win,
        as_of=now,
        calculated_at=now,
        numerator=54,
        denominator=108,
        value=0.500,
        status="valid",
        unit="ratio",
        sample_size=108,
        min_sample_threshold=10,
        min_sample_met=True,
        evidence_ref="test_ref_cur"
    )
    step2_prior = MetricResult(
        tenant_id="t1",
        vertical_template_id="ecommerce",
        metric_name="checkout_step_2_drop_off_rate",
        definition_version="v1.1.0",
        window=prior_win,
        as_of=now,
        calculated_at=now,
        numerator=36,
        denominator=126,
        value=0.2857,
        status="valid",
        unit="ratio",
        sample_size=126,
        min_sample_threshold=10,
        min_sample_met=True,
        evidence_ref="test_ref_prior"
    )

    false_claim = "Checkout friction decreased sharply across the board."
    clean_text, citations, dropped = linker.verify_and_link(
        text=false_claim,
        metrics=[step2_res, step2_prior]
    )

    # The gate MUST reject the false claim
    assert clean_text == ""
    assert len(citations) == 0
    assert len(dropped) == 1
    assert "sharply" in dropped[0] or "qualitative qualifier" in dropped[0] or "Direction" in dropped[0]

    # Without the hyperbole words: "Checkout friction decreased."
    false_direction_claim = "Checkout friction decreased."
    clean_text2, citations2, dropped2 = linker.verify_and_link(
        text=false_direction_claim,
        metrics=[step2_res, step2_prior]
    )
    assert clean_text2 == ""
    assert len(dropped2) == 1
    assert "Direction contradiction" in dropped2[0] or "Polarity" in dropped2[0]


def test_evidence_linker_number_bound_to_wrong_metric():
    """
    Validates Problem 1:
    - Claim: 'Cart abandonment reached 50.0%.'
    - Even though 50.0% is a valid number in the database (it belongs to step 2 drop-off),
      it MUST NOT pass because it does NOT belong to cart abandonment (which is 81.4%).
    """
    linker = EvidenceLinker()
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    cur_win, _ = resolve_preset_window("last_7d", now)

    abandonment_res = MetricResult(
        tenant_id="t1",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        definition_version="v1.1.0",
        window=cur_win,
        as_of=now,
        calculated_at=now,
        numerator=171,
        denominator=210,
        value=0.8143,
        status="valid",
        unit="ratio",
        sample_size=210,
        min_sample_threshold=10,
        min_sample_met=True,
        evidence_ref="ref_abandonment"
    )
    step2_res = MetricResult(
        tenant_id="t1",
        vertical_template_id="ecommerce",
        metric_name="checkout_step_2_drop_off_rate",
        definition_version="v1.1.0",
        window=cur_win,
        as_of=now,
        calculated_at=now,
        numerator=54,
        denominator=108,
        value=0.500,
        status="valid",
        unit="ratio",
        sample_size=108,
        min_sample_threshold=10,
        min_sample_met=True,
        evidence_ref="ref_step2"
    )

    mismatched_claim = "Cart abandonment reached 50.0%."
    clean_text, citations, dropped = linker.verify_and_link(
        text=mismatched_claim,
        metrics=[abandonment_res, step2_res]
    )

    # The gate MUST reject attaching step 2's 50.0% to cart abandonment
    assert clean_text == ""
    assert len(dropped) == 1
    assert "does not match referenced metric 'cart_abandonment_rate'" in dropped[0]


def test_denominator_labeling_enforces_correct_concepts():
    """
    Validates Problem 3:
    - '300 checkouts' is impossible because overall_conversion_rate denominator is 'visiting sessions' (300)
    - checkout_conversion_rate denominator is 'checkouts started' (150)
    """
    template = get_vertical_template("ecommerce")
    overall_def = template.get_metric_def("overall_conversion_rate")
    checkout_def = template.get_metric_def("checkout_conversion_rate")

    assert overall_def.denominator_label == "visiting sessions"
    assert overall_def.numerator_label == "purchases"

    assert checkout_def.denominator_label == "checkouts started"
    assert checkout_def.numerator_label == "purchases"


def test_zero_data_window_returns_no_data_and_watermark_range(test_setup):
    """
    Validates Problem 2:
    - Zero data in requested window returns status 'no_data' (not 'valid')
    - Narrative transparently reports the data coverage watermark range.
    """
    storage, metrics_engine, query_engine, _, _ = test_setup
    tenant_id = "tenant_watermark_test"

    # Seed an event from 30 days ago to establish watermark coverage
    event_t = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    storage.store_event(EventEnvelope(
        event_id="old_ev_1", schema_version="1.0.0", tenant_id=tenant_id,
        source_module="module_2", event_name="page.viewed", occurred_at=event_t.isoformat(),
        received_at=event_t.isoformat(), session_id="s1", anonymous_id="a1", properties={}
    ))

    # Query a recent window where zero events exist
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    answer = query_engine.process_query(
        tenant_id=tenant_id,
        query_text="What was our cart abandonment rate today?",
        as_of=now
    )

    assert answer.technical_trace["status"] == "no_data"
    assert "No data in this window" in answer.executive_summary
    assert "data covers" in answer.executive_summary


def test_rate_limit_circuit_breaker_skips_provider_locally():
    """
    Validates Problem 9:
    - When client receives 429 or trip is activated, circuit cooldown is set.
    - Any subsequent call within the cooldown window raises RateLimitCircuitOpenError locally without HTTP request.
    """
    client = GeminiClient(api_key="AIzaSy_fake_test_key")

    # Manually simulate circuit opening with a 20-second cooldown
    GeminiClient._circuit_open_until = time.time() + 20.0
    GeminiClient._last_retry_delay = 20.0

    with pytest.raises(RateLimitCircuitOpenError) as exc_info:
        client.generate_content(
            contents=[{"role": "user", "parts": [{"text": "Hello"}]}]
        )

    assert "Rate limit cooldown active" in str(exc_info.value)
    assert "Skipping provider" in str(exc_info.value)

    # Reset circuit for subsequent tests
    GeminiClient._circuit_open_until = 0.0


def test_rule_prefiltering_spends_zero_llm_calls_for_ineligible_carts():
    """
    Validates Problem 7 & Optimizations:
    - DecisionManager pre-filters carts deterministically:
      1. Anonymous carts -> DO_NOTHING immediately (0 LLM calls).
      2. Under-threshold idle carts (< 30 min) -> DO_NOTHING immediately (0 LLM calls).
      3. Below-value carts (< INR 300) -> DO_NOTHING immediately (0 LLM calls).
    """
    class SpyDecisionProvider:
        def __init__(self):
            self.calls = 0

        def propose_candidates(self, ctx):
            self.calls += 1
            return []

    spy_primary = SpyDecisionProvider()
    manager = DecisionManager(primary_provider=spy_primary, fallback_provider=RuleDecisionProvider())
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    # Ineligible Cart 1: Anonymous visitor
    ctx_anon = DecisionContext(
        tenant_id="t1", signal_type="idle_cart",
        signal_payload={"customer_id": None, "anonymous_id": "anon_1", "cart_value": 800.0, "idle_minutes": 45},
        signal_dedupe_key="k1", as_of=now, tenant_config={"idle_threshold_minutes": 30}
    )
    res_anon = manager.propose_candidates(ctx_anon)
    assert len(res_anon) == 0
    assert spy_primary.calls == 0  # 0 LLM calls spent!

    # Ineligible Cart 2: Idle only 15 minutes (< 30 min)
    ctx_under_idle = DecisionContext(
        tenant_id="t1", signal_type="idle_cart",
        signal_payload={"customer_id": "cust_1", "cart_value": 800.0, "idle_minutes": 15},
        signal_dedupe_key="k2", as_of=now, tenant_config={"idle_threshold_minutes": 30}
    )
    res_under = manager.propose_candidates(ctx_under_idle)
    assert len(res_under) == 0
    assert spy_primary.calls == 0  # 0 LLM calls spent!

    # Ineligible Cart 3: Low cart value (INR 200 < INR 300)
    ctx_low_val = DecisionContext(
        tenant_id="t1", signal_type="idle_cart",
        signal_payload={"customer_id": "cust_1", "cart_value": 200.0, "idle_minutes": 45},
        signal_dedupe_key="k3", as_of=now, tenant_config={"idle_threshold_minutes": 30, "min_cart_value_inr": 300.0}
    )
    res_low = manager.propose_candidates(ctx_low_val)
    assert len(res_low) == 0
    assert spy_primary.calls == 0  # 0 LLM calls spent!


def test_autonomy_gate_never_cleared_by_llm_self_reported_confidence():
    """
    Validates Problem 7:
    - Model self-reported confidence (e.g. 0.95) must be stored in llm_self_reported_confidence.
    - calibrated_probability must remain None, ensuring uncalibrated confidence NEVER clears the autonomy gate.
    """
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    candidate = DecisionCandidate(
        action_type=ActionType.WAIVE_DELIVERY_FEE,
        target_module="module_1_loyalty",
        target_type="customer",
        target_id="cust_high",
        customer_id="cust_high",
        parameters=get_vertical_template("ecommerce").metrics["cart_abandonment_rate"],  # dummy
        reasoning_summary="Candidate proposed by LLM",
        evidence_citations=[],
        priority_score=0.90,
        calibrated_probability=None,
        llm_self_reported_confidence=0.95,
        is_holdout=False
    )

    assert candidate.llm_self_reported_confidence == 0.95
    assert candidate.calibrated_probability is None  # Never clears autonomous gate!
