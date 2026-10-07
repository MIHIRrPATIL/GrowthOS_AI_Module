"""
Mock LLM Adapter
Provides deterministic, zero-latency, offline responses conforming to LLMPort.
Enables comprehensive automated testing with zero API tokens or network calls.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import re

from domain.metrics import DigestReport, MetricResult, TimeWindow
from domain.nlp import (
    QueryIntent,
    QueryClassification,
    StructuredAnswer,
    EvidenceCitation
)
from ports.llm import LLMPort


class MockLLMAdapter(LLMPort):
    """
    Offline deterministic LLM adapter for testing and standard deterministic operations.
    """

    def __init__(self):
        self.provider_name = "mock_fallback"
        self.model = "mock_offline_engine"
        self.is_mock = True
        # Override table to simulate hallucination or custom responses during testing
        self.custom_explanations: Dict[str, str] = {}
        self.custom_classifications: Dict[str, QueryClassification] = {}

    def classify_query(
        self,
        query: str,
        metric_catalog: List[Dict[str, Any]],
        vertical: str = "ecommerce_d2c",
        as_of: Optional[datetime] = None
    ) -> QueryClassification:
        query_lower = query.lower().strip()

        # Check for pre-programmed override
        if query_lower in self.custom_classifications:
            return self.custom_classifications[query_lower]

        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        current_window = TimeWindow(
            start=now - timedelta(days=7),
            end=now
        )
        prior_window = TimeWindow(
            start=now - timedelta(days=14),
            end=now - timedelta(days=7)
        )

        # 1. Specific Step Drop Off (Checked before generic drop-off to avoid masking)
        if "step 2" in query_lower:
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else QueryIntent.METRIC_LOOKUP,
                target_metric="checkout_step_2_drop_off_rate",
                time_window=current_window,
                prior_window=prior_window if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else None,
                vertical=vertical,
                confidence=0.95
            )
        if "step 1" in query_lower:
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else QueryIntent.METRIC_LOOKUP,
                target_metric="checkout_step_1_drop_off_rate",
                time_window=current_window,
                prior_window=prior_window if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else None,
                vertical=vertical,
                confidence=0.95
            )
        if "step 3" in query_lower:
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else QueryIntent.METRIC_LOOKUP,
                target_metric="checkout_step_3_drop_off_rate",
                time_window=current_window,
                prior_window=prior_window if any(w in query_lower for w in ["performing", "compared", "vs", "over last", "prior"]) else None,
                vertical=vertical,
                confidence=0.95
            )

        # 2. Exploratory Funnel Drop Off
        if any(w in query_lower for w in ["drop off", "drop-off", "checkout friction", "friction", "where"]):
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.FUNNEL_DROP_OFF,
                target_metric="checkout_step_2_drop_off_rate",
                time_window=current_window,
                prior_window=prior_window,
                vertical=vertical,
                confidence=0.95
            )

        # 3. Cart Abandonment
        if any(w in query_lower for w in ["abandoned cart", "cart abandonment", "abandoning carts"]):
            has_comp = any(w in query_lower for w in ["compared to", "vs", "over last", "prior", "last week"])
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if has_comp else (QueryIntent.ANOMALY_DIAGNOSIS if "why" in query_lower else QueryIntent.METRIC_LOOKUP),
                target_metric="cart_abandonment_rate",
                time_window=current_window,
                prior_window=prior_window if has_comp else None,
                vertical=vertical,
                confidence=0.92
            )

        # 4. Conversion Rate (Checkout vs Overall)
        if "checkout conversion" in query_lower:
            has_comp = any(w in query_lower for w in ["compared to", "vs", "over last", "prior", "last week"])
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if has_comp else QueryIntent.METRIC_LOOKUP,
                target_metric="checkout_conversion_rate",
                time_window=current_window,
                prior_window=prior_window if has_comp else None,
                vertical=vertical,
                confidence=0.92
            )
        if any(w in query_lower for w in ["conversion", "converting"]):
            has_comp = any(w in query_lower for w in ["compared to", "vs", "over last", "prior", "last week"])
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.PERIOD_COMPARISON if has_comp else QueryIntent.METRIC_LOOKUP,
                target_metric="overall_conversion_rate",
                time_window=current_window,
                prior_window=prior_window if has_comp else None,
                vertical=vertical,
                confidence=0.90
            )

        # 5. SaaS Trial Conversion
        if any(w in query_lower for w in ["trial", "paid conversion", "subscription"]):
            return QueryClassification(
                query_text=query,
                intent=QueryIntent.METRIC_LOOKUP,
                target_metric="trial_to_paid_conversion_rate",
                time_window=current_window,
                prior_window=None,
                vertical="saas_subscription",
                confidence=0.94
            )

        # 6. Unsupported / Out-of-catalog
        return QueryClassification(
            query_text=query,
            intent=QueryIntent.UNSUPPORTED,
            target_metric=None,
            time_window=current_window,
            vertical=vertical,
            confidence=0.20,
            clarification_needed="The query could not be mapped to an approved business metric in the catalog."
        )

    def explain_digest(
        self,
        report: DigestReport,
        vertical: str = "ecommerce_d2c"
    ) -> str:
        # Check custom override
        if report.tenant_id in self.custom_explanations:
            return self.custom_explanations[report.tenant_id]

        anomalies = getattr(report, "idle_cart_anomalies", getattr(report, "anomalies", []))
        if not report.flags and not anomalies:
            return "All key growth metrics are performing within normal baseline tolerances with zero active anomalies."

        sentences: List[str] = []
        for flag in report.flags:
            metric_label = flag.metric_name.replace("_", " ")
            cur_pct = (flag.current_value or 0.0) * 100.0 if (flag.current_value or 0.0) <= 1.0 else (flag.current_value or 0.0)
            prior_pct = (flag.prior_value or 0.0) * 100.0 if (flag.prior_value or 0.0) <= 1.0 else (flag.prior_value or 0.0)
            chg = getattr(flag, "delta_pct", getattr(flag, "pct_change", 0.0)) or 0.0
            sample = getattr(flag, "current_sample_size", getattr(flag, "sample_size", 0))
            direction = "increased" if chg > 0 else "decreased"

            s = (
                f"{metric_label.capitalize()} {direction} to {cur_pct:.1f}% ({chg:+.1f}% vs prior {prior_pct:.1f}%) "
                f"across {sample} sessions [citation: metric={flag.metric_name} value={flag.current_value:.4f} sample={sample}]."
            )
            sentences.append(s)

        for anom in anomalies:
            cust_id = getattr(anom, "customer_id", None)
            if cust_id:
                val = getattr(anom, "cart_total_inr", getattr(anom, "cart_value", 0.0))
                mins = int(getattr(anom, "idle_duration_minutes", getattr(anom, "idle_minutes", 0)))
                s = (
                    f"Customer {cust_id} has an abandoned high-value cart of INR {val:.2f} "
                    f"idle for {mins} minutes [citation: metric=idle_cart_value value={val:.2f} sample=1]."
                )
                sentences.append(s)

        return " ".join(sentences)

    def synthesize_answer(
        self,
        query: str,
        classification: QueryClassification,
        metrics: List[MetricResult]
    ) -> StructuredAnswer:
        if not metrics:
            return StructuredAnswer(
                query_text=query,
                intent=classification.intent,
                executive_summary="No computed metric data was available for the requested parameters.",
                analytical_breakdown=["Data sample count is zero for the selected time window."],
                technical_trace={"metric_count": 0, "status": "no_data"}
            )

        primary = metrics[0]
        metric_name = primary.metric_name.replace("_", " ")

        if primary.value is not None:
            cur_pct = primary.value * 100.0 if primary.value <= 1.0 else primary.value
            exec_summary = (
                f"The current {metric_name} is {cur_pct:.1f}% based on {primary.sample_size} recorded events."
            )
            val_str = f"{cur_pct:.2f}%"
        else:
            cur_pct = 0.0
            exec_summary = (
                f"The current {metric_name} has insufficient data or zero activity ({primary.sample_size} recorded events)."
            )
            val_str = "N/A"

        # 2. Analytical Breakdown
        analytics: List[str] = [
            f"Computed value: {val_str} (numerator: {primary.numerator}, denominator: {primary.denominator}).",
            f"Sample size met: {'Yes' if primary.min_sample_met else 'No (Insufficient data)'}."
        ]
        if len(metrics) > 1:
            prior = metrics[1]
            if prior.value is not None and primary.value is not None:
                prior_pct = prior.value * 100.0 if prior.value <= 1.0 else prior.value
                diff = cur_pct - prior_pct
                analytics.append(f"Period comparison: {cur_pct:.1f}% vs prior {prior_pct:.1f}% (delta: {diff:+.1f}%).")
            else:
                analytics.append("Prior period comparison unavailable due to zero or insufficient sample.")

        # 3. Technical Trace
        tech_trace = {
            "metric_name": primary.metric_name,
            "tenant_id": primary.tenant_id,
            "window_start": primary.window.start.isoformat(),
            "window_end": primary.window.end.isoformat(),
            "calculation_method": "deterministic_set_difference_ratio",
            "source_events": ["cart.item_added", "checkout.step_completed"]
        }

        # 4. Citations
        citations = []
        if primary.value is not None:
            citations.append(
                EvidenceCitation(
                    citation_id=f"cit_{primary.metric_name}",
                    claim_text=f"{metric_name} is {cur_pct:.1f}%",
                    metric_name=primary.metric_name,
                    computed_value=primary.value,
                    sample_size=primary.sample_size,
                    is_verified=True
                )
            )

        return StructuredAnswer(
            query_text=query,
            intent=classification.intent,
            executive_summary=exec_summary,
            analytical_breakdown=analytics,
            technical_trace=tech_trace,
            citations=citations
        )
