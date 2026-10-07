"""
Unit Tests for OpenRouter Adapters (Client, Decision Provider, LLM Adapter)
GrowthOS Module 4: AI Growth Brain

Verifies:
1. OpenRouterClient configuration, header generation, JSON extraction, and rate resolution.
2. OpenRouterDecisionProvider action proposal and benchmark prediction logic.
3. OpenRouterLLMAdapter query classification, digest explanation, and answer synthesis.
4. Complete offline isolation (100% mocked network calls).

Strictly NO emojis used in logs or tests.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from domain.metrics import TimeWindow, DigestReport, DigestFlag, MetricResult
from domain.nlp import QueryIntent, QueryClassification, EvidenceCitation
from domain.evaluation import DecisionBenchmarkCase
from domain.actions import ActionType
from ports.decision import DecisionContext
from adapters.openrouter_client import OpenRouterClient
from adapters.openrouter_decision_provider import OpenRouterDecisionProvider
from adapters.openrouter_llm_adapter import OpenRouterLLMAdapter


# =============================================================================
# 1. OpenRouterClient Tests
# =============================================================================

def test_openrouter_client_unconfigured_raises_error():
    client = OpenRouterClient(api_key="")
    assert not client.is_configured()
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not configured"):
        client._get_headers()


def test_openrouter_client_configured_headers():
    client = OpenRouterClient(api_key="sk-or-v1-testkey12345", model="google/gemini-2.0-flash-001")
    assert client.is_configured()
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer sk-or-v1-testkey12345"
    assert "HTTP-Referer" in headers
    assert "Content-Type" in headers


def test_openrouter_client_json_extraction():
    # 1. Plain clean JSON
    plain = '{"key": "value", "count": 42}'
    res1 = OpenRouterClient._extract_json(plain)
    assert res1 == {"key": "value", "count": 42}

    # 2. Markdown fenced JSON
    fenced = '```json\n{"action": "waive_delivery_fee", "confidence": 0.95}\n```'
    res2 = OpenRouterClient._extract_json(fenced)
    assert res2 == {"action": "waive_delivery_fee", "confidence": 0.95}

    # 3. JSON embedded within surrounding text
    surrounded = 'Analysis complete. Here is the decision:\n{"result": "success"}\nEnd of response.'
    res3 = OpenRouterClient._extract_json(surrounded)
    assert res3 == {"result": "success"}

    # 4. Invalid text
    invalid = 'This is completely invalid non-JSON output'
    assert OpenRouterClient._extract_json(invalid) is None


def test_openrouter_client_rate_lookup():
    client = OpenRouterClient()
    rates_gemini = client.get_model_rates("google/gemini-2.0-flash-001")
    assert rates_gemini == (0.10, 0.40)

    rates_claude = client.get_model_rates("anthropic/claude-3.5-sonnet")
    assert rates_claude == (3.00, 15.00)

    rates_llama = client.get_model_rates("meta-llama/llama-3.3-70b-instruct")
    assert rates_llama == (0.12, 0.30)

    # Free variant strip
    rates_free = client.get_model_rates("meta-llama/llama-3.3-70b-instruct:free")
    assert rates_free == (0.12, 0.30)


# =============================================================================
# 2. OpenRouterDecisionProvider Tests
# =============================================================================

def test_openrouter_decision_propose_fee_waiver():
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {
        "text": '{"action_type": "WAIVE_DELIVERY_FEE", "priority_score": 0.92, "confidence_probability": 0.88, "reasoning_summary": "High value cart idle for 25 mins", "evidence_citations": ["cart_value=750"]}',
        "json": {
            "action_type": "WAIVE_DELIVERY_FEE",
            "priority_score": 0.92,
            "confidence_probability": 0.88,
            "reasoning_summary": "High value cart idle for 25 mins",
            "evidence_citations": ["cart_value=750"]
        },
        "latency_ms": 310.0,
        "prompt_tokens": 120,
        "completion_tokens": 40,
        "cost_usd": 0.000028,
        "model": "google/gemini-2.0-flash-001"
    }

    provider = OpenRouterDecisionProvider(client=mock_client)
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


def test_openrouter_decision_propose_anonymous_cart_returns_empty():
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {
        "text": '{"action_type": "DO_NOTHING", "priority_score": 0.0, "confidence_probability": 0.99, "reasoning_summary": "Anonymous user cannot receive fee waiver"}',
        "json": {
            "action_type": "DO_NOTHING",
            "priority_score": 0.0,
            "confidence_probability": 0.99,
            "reasoning_summary": "Anonymous user cannot receive fee waiver"
        },
        "latency_ms": 250.0,
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "cost_usd": 0.000018,
        "model": "google/gemini-2.0-flash-001"
    }

    provider = OpenRouterDecisionProvider(client=mock_client)
    context = DecisionContext(
        tenant_id="tenant_test_01",
        signal_type="idle_cart",
        signal_payload={"anonymous_id": "anon_999", "cart_value": 900.0, "idle_minutes": 30},
        signal_dedupe_key="dedupe_anon",
        as_of=datetime.now(timezone.utc),
        tenant_config={}
    )

    candidates = provider.propose_candidates(context)
    assert len(candidates) == 0


def test_openrouter_predict_benchmark_case():
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {
        "text": '{"selected_option": "waive_delivery_fee", "confidence": 0.94}',
        "json": {"selected_option": "waive_delivery_fee", "confidence": 0.94},
        "latency_ms": 285.5,
        "prompt_tokens": 90,
        "completion_tokens": 15,
        "cost_usd": 0.000015,
        "model": "google/gemini-2.0-flash-001"
    }

    provider = OpenRouterDecisionProvider(client=mock_client)
    case = DecisionBenchmarkCase(
        case_id="case_ar_01",
        task_type="action_routing",
        input_context={"signal_type": "idle_cart", "customer_id": "cust_101", "cart_value": 750.0, "idle_minutes": 25},
        ground_truth="waive_delivery_fee",
        allowed_options=["waive_delivery_fee", "flag_ui_friction_bug", "sync_audience_segment", "do_nothing"],
        description="High value basket idle"
    )

    prediction = provider.predict_benchmark_case(case)
    assert prediction.case_id == "case_ar_01"
    assert prediction.selected_option == "waive_delivery_fee"
    assert prediction.is_correct is True
    assert prediction.stated_probability == 0.94
    assert prediction.latency_ms == 285.5


# =============================================================================
# 3. OpenRouterLLMAdapter Tests
# =============================================================================

def test_openrouter_llm_classify_query():
    mock_client = MagicMock()
    now_iso = "2026-10-05T12:00:00+00:00"
    mock_client.chat_completion.return_value = {
        "text": json.dumps({
            "intent": "funnel_drop_off",
            "target_metric": "checkout_step_2_drop_off_rate",
            "start_time_iso": "2026-09-28T00:00:00+00:00",
            "end_time_iso": "2026-10-05T00:00:00+00:00",
            "confidence": 0.96,
            "clarification_needed": None
        }),
        "json": {
            "intent": "funnel_drop_off",
            "target_metric": "checkout_step_2_drop_off_rate",
            "start_time_iso": "2026-09-28T00:00:00+00:00",
            "end_time_iso": "2026-10-05T00:00:00+00:00",
            "confidence": 0.96,
            "clarification_needed": None
        },
        "latency_ms": 320.0,
        "prompt_tokens": 150,
        "completion_tokens": 40,
        "cost_usd": 0.000031,
        "model": "google/gemini-2.0-flash-001"
    }

    catalog = [
        {"metric_name": "checkout_step_2_drop_off_rate", "description": "Drop off at step 2"},
        {"metric_name": "overall_conversion_rate", "description": "Overall conversion"}
    ]

    adapter = OpenRouterLLMAdapter(client=mock_client)
    res = adapter.classify_query(
        query="Where is checkout drop off happening?",
        metric_catalog=catalog,
        vertical="ecommerce"
    )

    assert res.intent == QueryIntent.FUNNEL_DROP_OFF
    assert res.target_metric == "checkout_step_2_drop_off_rate"
    assert res.confidence == 0.96


def test_openrouter_llm_unsupported_query():
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {
        "text": json.dumps({
            "intent": "unsupported",
            "target_metric": None,
            "confidence": 0.99,
            "clarification_needed": "We only provide eCommerce funnel metrics."
        }),
        "json": {
            "intent": "unsupported",
            "target_metric": None,
            "confidence": 0.99,
            "clarification_needed": "We only provide eCommerce funnel metrics."
        },
        "latency_ms": 220.0,
        "prompt_tokens": 120,
        "completion_tokens": 25,
        "cost_usd": 0.000022,
        "model": "google/gemini-2.0-flash-001"
    }

    adapter = OpenRouterLLMAdapter(client=mock_client)
    res = adapter.classify_query(
        query="What is the weather tomorrow?",
        metric_catalog=[{"metric_name": "overall_conversion_rate"}],
        vertical="ecommerce"
    )

    assert res.intent == QueryIntent.UNSUPPORTED
    assert res.target_metric is None
    assert "eCommerce funnel metrics" in (res.clarification_needed or "")
