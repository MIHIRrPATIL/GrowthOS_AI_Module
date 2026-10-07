"""
Unit and Integration Tests for Provider Benchmarking, Calibration, and Decision Manager
Validates:
- Labeled dataset schema conformance.
- Performance scorecards across Rules, LLM, and Jev providers.
- Statistical calibration (ECE, MCE, Brier score) and temperature scaling impact.
- Autonomy gating and confidence suppression for uncalibrated models.
- Seamless fallback to RuleDecisionProvider upon primary provider failure.
- Multi-criteria provider winner selection.
"""

import pytest
from datetime import datetime, timezone

from domain.evaluation import (
    DecisionBenchmarkCase,
    ProviderPerformanceSummary
)
from domain.actions import ActionType
from ports.decision import DecisionContext
from engines.rule_decision_provider import RuleDecisionProvider
from adapters.llm_decision_provider import LLMDecisionProvider
from adapters.jev_decision_provider import JevDecisionProvider
from evaluation.evaluator import BenchmarkEvaluator
from services.decision_manager import DecisionManager


@pytest.fixture
def evaluator():
    return BenchmarkEvaluator()


@pytest.fixture
def rule_provider():
    return RuleDecisionProvider()


@pytest.fixture
def llm_provider():
    return LLMDecisionProvider()


@pytest.fixture
def jev_provider():
    return JevDecisionProvider(temperature_calibration=True)


def test_benchmark_dataset_loading(evaluator):
    """Verifies that all three benchmark datasets load correctly with strict schema validation."""
    qc_cases = evaluator.load_dataset("query_classification")
    ar_cases = evaluator.load_dataset("action_routing")
    es_cases = evaluator.load_dataset("evidence_support")

    assert len(qc_cases) >= 20
    assert len(ar_cases) >= 20
    assert len(es_cases) >= 20

    for c in qc_cases:
        assert isinstance(c, DecisionBenchmarkCase)
        assert c.task_type == "query_classification"
        assert c.ground_truth in c.allowed_options


def test_provider_evaluation_scorecards(evaluator, rule_provider, llm_provider, jev_provider):
    """
    Evaluates Rules, LLM, and Jev on action routing.
    Verifies accuracy, latency profiles, calibration metrics, and costs.
    """
    summary_rules = evaluator.evaluate_provider("rules", rule_provider, "action_routing")
    summary_llm = evaluator.evaluate_provider("llm", llm_provider, "action_routing")
    summary_jev = evaluator.evaluate_provider("jev", jev_provider, "action_routing")

    # 1. Rules scorecard
    assert summary_rules.accuracy >= 0.90
    assert summary_rules.p95_latency_ms < 5.0
    assert summary_rules.cost_per_1000_usd == 0.0

    # 2. LLM scorecard
    assert summary_llm.accuracy >= 0.90
    assert summary_llm.p50_latency_ms >= 200.0
    assert summary_llm.cost_per_1000_usd > 1.0
    assert summary_llm.calibration.expected_calibration_error <= 0.15

    # 3. Jev scorecard
    assert summary_jev.accuracy >= 0.90
    assert summary_jev.p50_latency_ms < 50.0
    assert summary_jev.cost_per_1000_usd < 0.50
    assert summary_jev.calibration.expected_calibration_error <= 0.10
    assert summary_jev.is_eligible_for_autonomous is True


def test_temperature_calibration_impact(evaluator):
    """
    Verifies that temperature scaling reduces Expected Calibration Error (ECE)
    compared to raw uncalibrated overconfident logits.
    """
    calibrated_jev = JevDecisionProvider(temperature_calibration=True)
    uncalibrated_jev = JevDecisionProvider(temperature_calibration=False)

    summary_calibrated = evaluator.evaluate_provider("jev_calibrated", calibrated_jev, "action_routing")
    summary_uncalibrated = evaluator.evaluate_provider("jev_uncalibrated", uncalibrated_jev, "action_routing")

    assert summary_calibrated.calibration.expected_calibration_error < summary_uncalibrated.calibration.expected_calibration_error


def test_decision_manager_fallback(rule_provider):
    """
    Tests that DecisionManager intercepts primary provider failure and falls back
    to RuleDecisionProvider without throwing or dropping candidates.
    """
    failing_llm = LLMDecisionProvider(simulate_failure=True)
    manager = DecisionManager(primary_provider=failing_llm, fallback_provider=rule_provider)

    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={"customer_id": "cust_123", "cart_value": 750.0, "idle_minutes": 25},
        signal_dedupe_key="dedupe_cart_123",
        as_of=datetime.now(timezone.utc),
        tenant_config={"holdout_pct": 0}
    )

    candidates = manager.propose_candidates(context)

    assert len(candidates) == 1
    assert candidates[0].action_type == ActionType.WAIVE_DELIVERY_FEE
    assert manager.fallback_invocation_count == 1
    assert manager.primary_invocation_count == 1


def test_autonomy_gating_uncalibrated_provider(evaluator, rule_provider):
    """
    Tests that if a provider has is_eligible_for_autonomous=False,
    DecisionManager strips calibrated_probability from candidates so ModeGate doesn't grant autonomy.
    """
    uncalibrated_jev = JevDecisionProvider(temperature_calibration=False)
    summary_uncal = evaluator.evaluate_provider("jev_uncal", uncalibrated_jev, "action_routing")
    # Force autonomy ineligible
    summary_uncal = summary_uncal.model_copy(update={"is_eligible_for_autonomous": False})

    manager = DecisionManager(
        primary_provider=uncalibrated_jev,
        fallback_provider=rule_provider,
        performance_summary=summary_uncal
    )

    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={"customer_id": "cust_999", "cart_value": 800.0, "idle_minutes": 30},
        signal_dedupe_key="dedupe_cart_999",
        as_of=datetime.now(timezone.utc),
        tenant_config={"holdout_pct": 0}
    )

    candidates = manager.propose_candidates(context)
    assert len(candidates) == 1
    assert candidates[0].action_type == ActionType.WAIVE_DELIVERY_FEE
    # Must be stripped to None because provider was not certified for autonomy
    assert candidates[0].calibrated_probability is None


def test_select_best_provider_multi_criteria(evaluator, rule_provider, llm_provider, jev_provider):
    """
    Tests that multi-criteria winner selection picks Jev over LLM due to 10x lower latency
    and 25x lower cost while maintaining >= 90% accuracy and ECE <= 0.10.
    """
    summary_rules = evaluator.evaluate_provider("rules", rule_provider, "action_routing")
    summary_llm = evaluator.evaluate_provider("llm", llm_provider, "action_routing")
    summary_jev = evaluator.evaluate_provider("jev", jev_provider, "action_routing")

    instances = {
        "rules": rule_provider,
        "llm": llm_provider,
        "jev": jev_provider
    }

    manager = DecisionManager.select_best_provider(
        summaries=[summary_rules, summary_llm, summary_jev],
        provider_instances=instances,
        fallback_provider=rule_provider
    )

    assert manager.primary_provider == jev_provider
    assert manager.fallback_provider == rule_provider
    assert manager.performance_summary.provider_name == "jev"
