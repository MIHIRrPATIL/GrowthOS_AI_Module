"""
Unit tests for EvidenceLinker and DigestExplanationEngine
Validates:
- Factual verification of numeric claims against computed metrics.
- Pruning of hallucinated numbers.
- Pruning of inverted polarity statements.
- Pruning of unreferenced metrics.
- Integration with DigestExplanationEngine producing grounded summaries.
"""

import pytest
from datetime import datetime, timezone, timedelta

from domain.metrics import DigestFlag, DigestReport, TimeWindow
from engines.evidence_linker import EvidenceLinker
from engines.digest_explanation_engine import DigestExplanationEngine
from adapters.mock_llm import MockLLMAdapter


@pytest.fixture
def sample_flags():
    flagged_time = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    return [
        DigestFlag(
            dedupe_key="tenant_dominos:checkout_step_2_drop_off_rate:week_over_week:20261005",
            tenant_id="tenant_dominos",
            metric_name="checkout_step_2_drop_off_rate",
            period="week_over_week",
            polarity="lower_is_better",
            current_value=0.44,
            prior_value=0.12,
            current_sample_size=310,
            prior_sample_size=300,
            unit="ratio",
            threshold_pct=10.0,
            severity="high",
            adverse=True,
            flagged_at=flagged_time,
            status="active"
        ),
        DigestFlag(
            dedupe_key="tenant_dominos:visitor_to_checkout_conversion_rate:week_over_week:20261005",
            tenant_id="tenant_dominos",
            metric_name="visitor_to_checkout_conversion_rate",
            period="week_over_week",
            polarity="higher_is_better",
            current_value=0.032,
            prior_value=0.045,
            current_sample_size=1200,
            prior_sample_size=1150,
            unit="ratio",
            threshold_pct=10.0,
            severity="medium",
            adverse=True,
            flagged_at=flagged_time,
            status="active"
        )
    ]


def test_evidence_linker_verifies_accurate_claims(sample_flags):
    linker = EvidenceLinker()
    raw_text = (
        "Checkout step 2 drop off rate increased to 44.0% (+266.7% vs prior 12.0%) across 310 sessions "
        "[citation: metric=checkout_step_2_drop_off_rate value=0.4400 sample=310]."
    )

    verified_text, citations, dropped = linker.verify_and_link(
        text=raw_text,
        flags=sample_flags
    )

    assert len(dropped) == 0
    assert len(citations) == 1
    assert citations[0].metric_name == "checkout_step_2_drop_off_rate"
    assert citations[0].is_verified is True
    assert "increased to 44.0%" in verified_text
    # Citation tag is removed from user-facing text
    assert "[citation:" not in verified_text


def test_evidence_linker_prunes_hallucinated_numbers(sample_flags):
    linker = EvidenceLinker()
    # LLM hallucinates 88.5% instead of 44.0%
    hallucinated_text = (
        "Checkout step 2 drop off rate spiked to 88.5% across 310 sessions "
        "[citation: metric=checkout_step_2_drop_off_rate value=0.8850 sample=310]."
    )

    verified_text, citations, dropped = linker.verify_and_link(
        text=hallucinated_text,
        flags=sample_flags
    )

    # Hallucinated sentence must be dropped!
    assert len(dropped) == 1
    assert "value mismatch" in dropped[0]
    assert verified_text == ""
    assert len(citations) == 0


def test_evidence_linker_prunes_polarity_contradiction(sample_flags):
    linker = EvidenceLinker()
    # True change is +266.7% (an increase), but text claims it "dropped"
    inverted_text = (
        "Checkout step 2 drop off rate dropped significantly to 44.0% "
        "[citation: metric=checkout_step_2_drop_off_rate value=0.4400 sample=310]."
    )

    verified_text, citations, dropped = linker.verify_and_link(
        text=inverted_text,
        flags=sample_flags
    )

    assert len(dropped) == 1
    assert "Direction mismatch" in dropped[0]
    assert verified_text == ""


def test_evidence_linker_prunes_unsupported_metrics(sample_flags):
    linker = EvidenceLinker()
    # Bounce rate does not exist in sample_flags
    unsupported_text = (
        "Website bounce rate surged to 75.0% [citation: metric=bounce_rate value=0.7500 sample=500]."
    )

    verified_text, citations, dropped = linker.verify_and_link(
        text=unsupported_text,
        flags=sample_flags
    )

    assert len(dropped) == 1
    assert "Unknown metric 'bounce_rate'" in dropped[0]
    assert verified_text == ""


def test_digest_explanation_engine_end_to_end(sample_flags):
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    cur_win = TimeWindow(start=now - timedelta(days=7), end=now)
    prior_win = TimeWindow(start=now - timedelta(days=14), end=now - timedelta(days=7))
    report = DigestReport(
        report_id="rep_test_001",
        tenant_id="tenant_dominos",
        vertical_template_id="ecommerce_d2c",
        period="week_over_week",
        current_window=cur_win,
        prior_window=prior_win,
        threshold_pct=10.0,
        generated_at=now,
        current_metrics={},
        prior_metrics={},
        flags=sample_flags
    )

    llm = MockLLMAdapter()
    engine = DigestExplanationEngine(llm_port=llm)

    explanation = engine.generate_explanation(report)

    assert explanation.tenant_id == "tenant_dominos"
    assert "Checkout Step 2 Drop Off Rate" in explanation.headline
    assert len(explanation.citations) >= 1
    assert len(explanation.unsupported_claims_dropped) == 0
    assert "Checkout step 2 drop off rate increased" in explanation.detailed_narrative


def test_digest_explanation_engine_captures_hallucinations_in_unsupported_list(sample_flags):
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    cur_win = TimeWindow(start=now - timedelta(days=7), end=now)
    prior_win = TimeWindow(start=now - timedelta(days=14), end=now - timedelta(days=7))
    report = DigestReport(
        report_id="rep_test_002",
        tenant_id="tenant_dominos",
        vertical_template_id="ecommerce_d2c",
        period="week_over_week",
        current_window=cur_win,
        prior_window=prior_win,
        threshold_pct=10.0,
        generated_at=now,
        current_metrics={},
        prior_metrics={},
        flags=sample_flags
    )

    llm = MockLLMAdapter()
    # Inject a hallucinated narrative into the mock LLM
    llm.custom_explanations["tenant_dominos"] = (
        "Checkout step 2 drop off rate increased to 44.0% [citation: metric=checkout_step_2_drop_off_rate value=0.4400 sample=310]. "
        "User churn rate exploded to 99.0% [citation: metric=churn_rate value=0.9900 sample=100]."
    )

    engine = DigestExplanationEngine(llm_port=llm)
    explanation = engine.generate_explanation(report)

    # First sentence is verified
    assert "Checkout step 2 drop off rate increased to 44.0%" in explanation.detailed_narrative
    # Second hallucinated sentence is pruned and logged
    assert len(explanation.unsupported_claims_dropped) == 1
    assert "Unknown metric 'churn_rate'" in explanation.unsupported_claims_dropped[0]
