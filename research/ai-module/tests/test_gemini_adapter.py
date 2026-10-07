"""
Unit Tests for Google Gemini Adapters (Client, Decision Provider, LLM Adapter)
GrowthOS Module 4: AI Growth Brain

Verifies:
1. GeminiClient configuration, header generation, JSON extraction, and rate resolution.
2. GeminiDecisionProvider action candidate proposal and benchmark evaluation.
3. GeminiLLMAdapter query classification, digest explanation, and answer synthesis.
4. Offline isolation (100% mocked network calls).

Strictly NO emojis used in logs or tests.
"""

import pytest
import json
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from domain.metrics import TimeWindow, DigestReport, DigestFlag, MetricResult
from domain.nlp import QueryIntent, QueryClassification
from domain.evaluation import DecisionBenchmarkCase
from domain.actions import ActionType
from ports.decision import DecisionContext
from adapters.gemini_client import GeminiClient
from adapters.gemini_decision_provider import GeminiDecisionProvider
from adapters.gemini_llm_adapter import GeminiLLMAdapter


# =============================================================================
# 1. GeminiClient Tests
# =============================================================================

def test_gemini_client_unconfigured_raises_error():
    client = GeminiClient(api_key="")
    assert not client.is_configured()
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        client._get_headers()


def test_gemini_client_configured_headers():
    client = GeminiClient(api_key="AIzaSyTestKey1234567890", model="gemini-2.5-flash")
    assert client.is_configured()
    headers = client._get_headers()
    assert headers["x-goog-api-key"] == "AIzaSyTestKey1234567890"
    assert headers["Content-Type"] == "application/json"


def test_gemini_client_model_normalization():
    assert GeminiClient._normalize_model_name("google/gemini-2.5-flash") == "gemini-2.5-flash"
    assert GeminiClient._normalize_model_name("models/gemini-2.5-flash") == "gemini-2.5-flash"
    assert GeminiClient._normalize_model_name("gemini-2.5-flash:free") == "gemini-2.5-flash"
    assert GeminiClient._normalize_model_name("gemini-2.5-flash") == "gemini-2.5-flash"


def test_gemini_client_rate_lookup():
    client = GeminiClient()
    rates_flash = client.get_model_rates("gemini-2.5-flash")
    assert rates_flash == (0.075, 0.30)

    rates_lite = client.get_model_rates("gemini-2.5-flash-lite")
    assert rates_lite == (0.0375, 0.15)

    rates_pro = client.get_model_rates("gemini-2.5-pro")
    assert rates_pro == (1.25, 5.00)


def test_gemini_client_json_extraction():
    # 1. Plain clean JSON
    plain = '{"key": "value", "count": 42}'
    res1 = GeminiClient._extract_json(plain)
    assert res1 == {"key": "value", "count": 42}

    # 2. Markdown fenced JSON
    fenced = '```json\n{"action": "waive_delivery_fee", "confidence": 0.95}\n```'
    res2 = GeminiClient._extract_json(fenced)
    assert res2 == {"action": "waive_delivery_fee", "confidence": 0.95}

    # 3. JSON embedded within surrounding text
    surrounded = 'Reasoning summary:\n{"action_type": "WAIVE_DELIVERY_FEE", "confidence": 0.90}\nCompleted.'
    res3 = GeminiClient._extract_json(surrounded)
    assert res3 == {"action_type": "WAIVE_DELIVERY_FEE", "confidence": 0.90}

    # 4. Invalid text
    invalid = 'This is non JSON raw explanation.'
    assert GeminiClient._extract_json(invalid) is None


# =============================================================================
# 2. GeminiDecisionProvider Tests
# =============================================================================

def test_gemini_decision_propose_fee_waiver():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": '{"action_type": "WAIVE_DELIVERY_FEE", "priority_score": 0.92, "confidence_probability": 0.88, "reasoning_summary": "High value cart idle for 25 mins", "evidence_citations": ["cart_value=750"]}',
        "json": {
            "action_type": "WAIVE_DELIVERY_FEE",
            "priority_score": 0.92,
            "confidence_probability": 0.88,
            "reasoning_summary": "High value cart idle for 25 mins",
            "evidence_citations": ["cart_value=750"]
        },
        "latency_ms": 280.0,
        "prompt_tokens": 120,
        "completion_tokens": 40,
        "cost_usd": 0.000028,
        "model": "gemini-2.5-flash"
    }

    provider = GeminiDecisionProvider(client=mock_client)
    now = datetime.now(timezone.utc)
    context = DecisionContext(
        tenant_id="tenant_test_01",
        signal_type="idle_cart",
        signal_payload={"customer_id": "cust_123", "cart_value": 750.0, "idle_minutes": 25},
        signal_dedupe_key="dedupe_123",
        as_of=now,
        tenant_config={"fee_waiver_amount_paise": 5000}
    )

    candidates = provider.propose_candidates(context)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.action_type == ActionType.WAIVE_DELIVERY_FEE
    assert cand.target_id == "cust_123"
    assert cand.llm_self_reported_confidence == 0.88
    assert cand.calibrated_probability is None
    assert cand.parameters.fee_amount_paise == 5000


def test_gemini_decision_propose_anonymous_cart_returns_empty():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": '{"action_type": "DO_NOTHING", "priority_score": 0.0, "confidence_probability": 0.99, "reasoning_summary": "Anonymous user cannot receive fee waiver"}',
        "json": {
            "action_type": "DO_NOTHING",
            "priority_score": 0.0,
            "confidence_probability": 0.99,
            "reasoning_summary": "Anonymous user cannot receive fee waiver"
        },
        "latency_ms": 210.0,
        "prompt_tokens": 100,
        "completion_tokens": 30,
        "cost_usd": 0.00002,
        "model": "gemini-2.5-flash"
    }

    provider = GeminiDecisionProvider(client=mock_client)
    now = datetime.now(timezone.utc)
    context = DecisionContext(
        tenant_id="tenant_test_01",
        signal_type="idle_cart",
        signal_payload={"anonymous_id": "anon_999", "cart_value": 850.0, "idle_minutes": 30},
        signal_dedupe_key="dedupe_anon",
        as_of=now
    )

    candidates = provider.propose_candidates(context)
    assert len(candidates) == 0


def test_gemini_decision_predict_benchmark_case():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": '{"selected_option": "flag_ui_friction_bug", "confidence": 0.94, "reasoning": "Checkout step 2 drop off surged +35%"}',
        "json": {
            "selected_option": "flag_ui_friction_bug",
            "confidence": 0.94,
            "reasoning": "Checkout step 2 drop off surged +35%"
        },
        "latency_ms": 320.0,
        "prompt_tokens": 150,
        "completion_tokens": 35,
        "cost_usd": 0.00003,
        "model": "gemini-2.5-flash"
    }

    provider = GeminiDecisionProvider(client=mock_client)
    case = DecisionBenchmarkCase(
        case_id="bench_01",
        task_type="action_routing",
        input_context={"drop_off_delta": 0.35},
        ground_truth="flag_ui_friction_bug",
        allowed_options=["waive_delivery_fee", "flag_ui_friction_bug", "sync_audience_segment", "do_nothing"],
        description="Checkout delivery option bug"
    )

    pred = provider.predict_benchmark_case(case)
    assert pred.case_id == "bench_01"
    assert pred.selected_option == "flag_ui_friction_bug"
    assert pred.stated_probability == 0.94
    assert pred.is_correct is True
    assert pred.latency_ms == 320.0


# =============================================================================
# 3. GeminiLLMAdapter Tests
# =============================================================================

def test_gemini_llm_classify_query_known_metric():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": '{"intent": "funnel_drop_off", "target_metric": "checkout_drop_off_rate", "confidence": 0.96}',
        "json": {
            "intent": "funnel_drop_off",
            "target_metric": "checkout_drop_off_rate",
            "confidence": 0.96
        },
        "latency_ms": 250.0,
        "model": "gemini-2.5-flash"
    }

    adapter = GeminiLLMAdapter(client=mock_client)
    catalog = [{"metric_name": "checkout_drop_off_rate", "description": "Drop off rate in checkout"}]
    res = adapter.classify_query("Where are users abandoning checkout?", catalog, vertical="ecommerce_d2c")

    assert res.intent == QueryIntent.FUNNEL_DROP_OFF
    assert res.target_metric == "checkout_drop_off_rate"
    assert res.confidence == 0.96


def test_gemini_llm_classify_query_unknown_metric_returns_unsupported():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": '{"intent": "metric_lookup", "target_metric": "hallucinated_metric", "confidence": 0.80}',
        "json": {
            "intent": "metric_lookup",
            "target_metric": "hallucinated_metric",
            "confidence": 0.80
        },
        "latency_ms": 250.0,
        "model": "gemini-2.5-flash"
    }

    adapter = GeminiLLMAdapter(client=mock_client)
    catalog = [{"metric_name": "checkout_drop_off_rate", "description": "Drop off rate in checkout"}]
    res = adapter.classify_query("What is our hallucinated metric?", catalog, vertical="ecommerce_d2c")

    assert res.intent == QueryIntent.UNSUPPORTED
    assert res.target_metric is None


def test_gemini_llm_explain_digest():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": "Cart abandonment increased to 81.4% [citation: metric=cart_abandonment_rate value=0.814 sample=210].",
        "json": None,
        "latency_ms": 290.0,
        "model": "gemini-2.5-flash"
    }

    adapter = GeminiLLMAdapter(client=mock_client)
    now = datetime.now(timezone.utc)
    win_curr = TimeWindow(start=now - timedelta(days=7), end=now)
    win_prior = TimeWindow(start=now - timedelta(days=14), end=now - timedelta(days=7))

    flag = DigestFlag(
        dedupe_key="dedupe_01",
        tenant_id="tenant_01",
        metric_name="cart_abandonment_rate",
        period="week_over_week",
        polarity="lower_is_better",
        current_value=0.814,
        prior_value=0.643,
        current_sample_size=210,
        prior_sample_size=200,
        unit="ratio",
        threshold_pct=15.0,
        severity="high",
        adverse=True,
        flagged_at=now
    )
    report = DigestReport(
        report_id="rep_01",
        tenant_id="tenant_01",
        vertical_template_id="ecommerce",
        period="week_over_week",
        current_window=win_curr,
        prior_window=win_prior,
        threshold_pct=10.0,
        generated_at=now,
        current_metrics={},
        prior_metrics={},
        flags=[flag]
    )

    exp = adapter.explain_digest(report, vertical="ecommerce")
    assert "81.4%" in exp
    assert "[citation: metric=cart_abandonment_rate" in exp


def test_gemini_llm_synthesize_answer():
    mock_client = MagicMock()
    mock_client.generate_content.return_value = {
        "text": json.dumps({
            "executive_summary": "Overall conversion is 13.0%.",
            "analytical_breakdown": ["Current: 13.0% (39/300)", "Prior: 25.0% (75/300)"],
            "technical_trace": {"metric_name": "overall_conversion_rate"},
            "citations": [
                {
                    "citation_id": "cit_overall_conversion_rate_0",
                    "claim_text": "Overall conversion is 13.0%.",
                    "metric_name": "overall_conversion_rate",
                    "computed_value": 0.13,
                    "sample_size": 300,
                    "is_verified": True
                }
            ]
        }),
        "json": {
            "executive_summary": "Overall conversion is 13.0%.",
            "analytical_breakdown": ["Current: 13.0% (39/300)", "Prior: 25.0% (75/300)"],
            "technical_trace": {"metric_name": "overall_conversion_rate"},
            "citations": [
                {
                    "citation_id": "cit_overall_conversion_rate_0",
                    "claim_text": "Overall conversion is 13.0%.",
                    "metric_name": "overall_conversion_rate",
                    "computed_value": 0.13,
                    "sample_size": 300,
                    "is_verified": True
                }
            ]
        },
        "latency_ms": 310.0,
        "model": "gemini-2.5-flash"
    }

    adapter = GeminiLLMAdapter(client=mock_client)
    now = datetime.now(timezone.utc)
    win_curr = TimeWindow(start=now - timedelta(days=7), end=now)

    classification = QueryClassification(
        query_text="What is our overall conversion rate?",
        intent=QueryIntent.METRIC_LOOKUP,
        target_metric="overall_conversion_rate",
        time_window=win_curr
    )

    metric_res = MetricResult(
        tenant_id="tenant_01",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        definition_version="1.0.0",
        window=win_curr,
        as_of=now,
        calculated_at=now,
        value=0.13,
        numerator=39,
        denominator=300,
        sample_size=300,
        min_sample_threshold=30,
        min_sample_met=True,
        status="valid",
        unit="ratio",
        evidence_ref="sha256:abcd1234efgh5678"
    )

    ans = adapter.synthesize_answer("What is our overall conversion rate?", classification, [metric_res])
    assert ans.executive_summary == "Overall conversion is 13.0%."
    assert len(ans.analytical_breakdown) == 2
    assert ans.citations[0].computed_value == 0.13
    assert ans.citations[0].sample_size == 300


# =============================================================================
# 4. Statistical Tests & Fake HTTP Server Simulation
# =============================================================================

def test_two_proportion_z_test_and_excess_lost():
    from domain.metrics import two_proportion_z_test, calculate_excess_lost_volume, format_change_metrics

    # Step 1: 42/150 vs 24/150
    z1, p1 = two_proportion_z_test(42, 150, 24, 150)
    assert 2.45 < z1 < 2.55
    assert 0.010 < p1 < 0.015  # Statistically significant (p < 0.05)
    lost1 = calculate_excess_lost_volume(42, 150, 24, 150)
    assert round(lost1, 1) == 18.0

    # Step 2: 54/108 vs 36/126
    z2, p2 = two_proportion_z_test(54, 108, 36, 126)
    assert 3.35 < z2 < 3.45
    assert p2 < 0.001  # Highly statistically significant
    lost2 = calculate_excess_lost_volume(54, 108, 36, 126)
    assert round(lost2, 1) == 23.1

    # Step 3: 15/54 vs 15/90
    z3, p3 = two_proportion_z_test(15, 54, 15, 90)
    assert 1.55 < z3 < 1.65
    assert p3 > 0.05  # NOT statistically significant (p ~ 0.109)
    lost3 = calculate_excess_lost_volume(15, 54, 15, 90)
    assert round(lost3, 1) == 6.0

    # Step 2 ranks first by excess lost volume (+23.1 > +18.0 > +6.0)
    assert lost2 > lost1 > lost3

    # Format change metrics
    fmt1 = format_change_metrics(0.28, 0.16)
    assert "+12.0 pp" in fmt1 and "+75.0% relative" in fmt1
    fmt2 = format_change_metrics(54 / 108, 36 / 126)
    assert "+21.4 pp" in fmt2 and "+75.0% relative" in fmt2


def test_gemini_client_fake_http_server(monkeypatch):
    import httpx
    import time
    from adapters.gemini_client import RateLimitCircuitOpenError

    client = GeminiClient(api_key="AIzaFakeKeyTest", model="gemini-2.5-flash")

    # Reset circuit breaker
    GeminiClient._circuit_open_until = 0.0

    fake_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"intent": "funnel_drop_off", "confidence": 0.95}'}]
                },
                "finishReason": "STOP"
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 45
        }
    }

    class FakeResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.text = json.dumps(json_data)

        def json(self):
            return self._json

    def mock_post(url, headers=None, json=None):
        return FakeResponse(200, fake_response_data)

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: mock_post(url, **kwargs))

    res = client.generate_content(
        contents=[{"role": "user", "parts": [{"text": "Where is drop off?"}]}],
        json_mode=True
    )

    assert res["json"] == {"intent": "funnel_drop_off", "confidence": 0.95}
    assert res["prompt_tokens"] == 120
    assert res["completion_tokens"] == 45
    assert res["model"] == "gemini-2.5-flash"
    assert res["latency_ms"] >= 0.0

    # Test 429 daily quota circuit breaker handling
    fake_429_data = {
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota).",
            "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "62356s"}]
        }
    }

    def mock_429_post(url, headers=None, json=None):
        return FakeResponse(429, fake_429_data)

    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: mock_429_post(url, **kwargs))

    with pytest.raises(RateLimitCircuitOpenError, match="daily_quota_exhausted"):
        client.generate_content(
            contents=[{"role": "user", "parts": [{"text": "test"}]}],
            json_mode=True
        )

    # Cooldown is capped at 300s (not 62,356s)
    assert GeminiClient._circuit_open_until > time.time()
    assert GeminiClient._circuit_open_until <= time.time() + 301.0

    # Immediate second call is blocked by active circuit breaker
    with pytest.raises(RateLimitCircuitOpenError, match="Rate limit cooldown active"):
        client.generate_content(
            contents=[{"role": "user", "parts": [{"text": "test"}]}],
            json_mode=True
        )

    # Reset circuit breaker
    GeminiClient._circuit_open_until = 0.0

