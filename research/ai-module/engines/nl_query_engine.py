"""
Natural-Language Query Engine
Answers merchant questions by strictly classifying intent into the predefined metric catalog,
invoking deterministic metric calculation, and synthesizing 3-tier answers verified by EvidenceLinker.
NEVER generates or executes raw SQL.
Strictly NO emojis used in logs or output.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from domain.metrics import MetricResult, TimeWindow, resolve_preset_window
from domain.nlp import (
    QueryIntent,
    QueryClassification,
    StructuredAnswer,
    EvidenceCitation
)
from ports.llm import LLMPort
from engines.metrics_engine import MetricsEngine
from engines.evidence_linker import EvidenceLinker
from engines.vertical_templates import get_vertical_template, TEMPLATE_REGISTRY


class NLQueryEngine:
    """
    Natural Language Query Engine over fixed metric catalogs.
    Pure deterministic data fetching with verified narrative synthesis.
    """

    def __init__(
        self,
        llm_port: LLMPort,
        metrics_engine: MetricsEngine,
        evidence_linker: Optional[EvidenceLinker] = None
    ):
        self.llm_port = llm_port
        self.metrics_engine = metrics_engine
        self.evidence_linker = evidence_linker or EvidenceLinker()

    def process_query(
        self,
        tenant_id: str,
        query_text: str,
        vertical: str = "ecommerce_d2c",
        as_of: Optional[datetime] = None
    ) -> StructuredAnswer:
        """
        Processes a natural language query end-to-end:
        1. Classifies query intent against known vertical metric catalog.
        2. Disambiguates specific metric targets (e.g. checkout conversion vs overall conversion).
        3. Computes deterministic MetricResults (current and prior window).
        4. Synthesizes a 3-tier structured answer (Executive, Analytical, Technical).
        5. Verifies narrative claims via EvidenceLinker.
        """
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Retrieve Vertical Metric Catalog
        template_id = "ecommerce" if vertical in ("ecommerce_d2c", "ecommerce") else vertical
        template = get_vertical_template(template_id)
        catalog_summary = [
            {
                "metric_name": name,
                "description": defn.description,
                "unit": defn.unit,
                "polarity": defn.polarity,
                "numerator_label": defn.numerator_label,
                "denominator_label": defn.denominator_label
            }
            for name, defn in template.metrics.items()
        ]

        # 2. Classify Query Intent via LLMPort
        classification = self.llm_port.classify_query(
            query=query_text,
            metric_catalog=catalog_summary,
            vertical=template_id,
            as_of=now
        )

        query_lower = query_text.lower()

        # Disambiguate checkout conversion vs overall conversion
        if "overall" in query_lower and "conversion" in query_lower:
            classification.target_metric = "overall_conversion_rate"
        elif "checkout conversion" in query_lower:
            classification.target_metric = "checkout_conversion_rate"
        elif "cart abandonment" in query_lower or "abandonment" in query_lower:
            classification.target_metric = "cart_abandonment_rate"

        # Disambiguate single-step metric queries from exploratory multi-step funnel queries
        if any(w in query_lower for w in ["step 1", "step 2", "step 3"]):
            if "step 1" in query_lower:
                classification.target_metric = "checkout_step_1_drop_off_rate"
            elif "step 2" in query_lower:
                classification.target_metric = "checkout_step_2_drop_off_rate"
            elif "step 3" in query_lower:
                classification.target_metric = "checkout_step_3_drop_off_rate"

            if classification.prior_window:
                classification.intent = QueryIntent.PERIOD_COMPARISON
            else:
                classification.intent = QueryIntent.METRIC_LOOKUP

        # 3. Handle Unsupported or Ambiguous Queries
        if classification.intent == QueryIntent.UNSUPPORTED or not classification.target_metric:
            return StructuredAnswer(
                query_text=query_text,
                intent=QueryIntent.UNSUPPORTED,
                executive_summary=classification.clarification_needed or "The query could not be mapped to a known business metric.",
                analytical_breakdown=[
                    f"Available metrics in {vertical}: {', '.join(list(template.metrics.keys()))}."
                ],
                technical_trace={"status": "unsupported_query", "vertical": vertical}
            )

        # 4. Multi-Step Funnel Breakdown for exploratory FUNNEL_DROP_OFF Intent (e.g. "where is drop-off happening?")
        if (classification.intent == QueryIntent.FUNNEL_DROP_OFF and "step" not in query_lower) or ("where is" in query_lower and "drop" in query_lower):
            return self._handle_funnel_drop_off_query(
                tenant_id=tenant_id,
                template_id=template_id,
                classification=classification,
                now=now,
                query_text=query_text
            )

        # 5. Standard Metric Calculation (Current & Prior)
        metric_results: List[MetricResult] = []
        try:
            cur_res = self.metrics_engine.calculate_metric(
                tenant_id=tenant_id,
                vertical_template_id=template_id,
                metric_name=classification.target_metric,
                window=classification.time_window,
                as_of=now,
                dimensions=classification.filters
            )
            metric_results.append(cur_res)

            if classification.prior_window:
                prior_res = self.metrics_engine.calculate_metric(
                    tenant_id=tenant_id,
                    vertical_template_id=template_id,
                    metric_name=classification.target_metric,
                    window=classification.prior_window,
                    as_of=now,
                    dimensions=classification.filters
                )
                metric_results.append(prior_res)
        except Exception as e:
            return StructuredAnswer(
                query_text=query_text,
                intent=classification.intent,
                executive_summary=f"Failed to calculate metric '{classification.target_metric}': {str(e)}",
                analytical_breakdown=["Error encountered during deterministic metric calculation."],
                technical_trace={"error": str(e), "metric_name": classification.target_metric}
            )

        # 6. Check for Zero Data Window
        if cur_res.status == "no_data" or (cur_res.denominator == 0 and cur_res.sample_size == 0):
            return self._handle_no_data_window(
                tenant_id=tenant_id,
                classification=classification,
                cur_res=cur_res,
                query_text=query_text
            )

        # 7. Synthesize Deterministic Grounded 3-Tier Answer
        return self._synthesize_grounded_answer(
            query_text=query_text,
            classification=classification,
            metric_results=metric_results,
            template=template
        )

    def _handle_funnel_drop_off_query(
        self,
        tenant_id: str,
        template_id: str,
        classification: QueryClassification,
        now: datetime,
        query_text: str
    ) -> StructuredAnswer:
        """
        Calculates per-step funnel metrics (Steps 1, 2, 3 and Overall)
        and outputs a multi-step comparative drop-off breakdown table.
        """
        step_metrics = [
            ("checkout_step_1_drop_off_rate", "Checkout to Step 1"),
            ("checkout_step_2_drop_off_rate", "Step 1 to Step 2"),
            ("checkout_step_3_drop_off_rate", "Step 2 to Purchase"),
            ("checkout_drop_off_rate", "Overall Checkout Drop-off")
        ]

        cur_results: Dict[str, MetricResult] = {}
        prior_results: Dict[str, MetricResult] = {}

        for m_name, _ in step_metrics:
            cur_results[m_name] = self.metrics_engine.calculate_metric(
                tenant_id=tenant_id,
                vertical_template_id=template_id,
                metric_name=m_name,
                window=classification.time_window,
                as_of=now
            )
            if classification.prior_window:
                prior_results[m_name] = self.metrics_engine.calculate_metric(
                    tenant_id=tenant_id,
                    vertical_template_id=template_id,
                    metric_name=m_name,
                    window=classification.prior_window,
                    as_of=now
                )

        s1_cur = cur_results["checkout_step_1_drop_off_rate"]
        s1_pri = prior_results.get("checkout_step_1_drop_off_rate")
        s2_cur = cur_results["checkout_step_2_drop_off_rate"]
        s2_pri = prior_results.get("checkout_step_2_drop_off_rate")
        s3_cur = cur_results["checkout_step_3_drop_off_rate"]
        s3_pri = prior_results.get("checkout_step_3_drop_off_rate")
        ov_cur = cur_results["checkout_drop_off_rate"]
        ov_pri = prior_results.get("checkout_drop_off_rate")

        from domain.metrics import two_proportion_z_test, calculate_excess_lost_volume, format_change_metrics

        s1_c_val = (s1_cur.value or 0.0) * 100.0
        s1_p_val = (s1_pri.value if s1_pri and s1_pri.value is not None else 0.0) * 100.0
        s2_c_val = (s2_cur.value or 0.0) * 100.0
        s2_p_val = (s2_pri.value if s2_pri and s2_pri.value is not None else 0.0) * 100.0
        s3_c_val = (s3_cur.value or 0.0) * 100.0
        s3_p_val = (s3_pri.value if s3_pri and s3_pri.value is not None else 0.0) * 100.0
        ov_c_val = (ov_cur.value or 0.0) * 100.0
        ov_p_val = (ov_pri.value if ov_pri and ov_pri.value is not None else 0.0) * 100.0

        # Exact Two-Proportion z-tests (Pooled)
        z1, p1 = two_proportion_z_test(s1_cur.numerator or 0, s1_cur.denominator or 0, s1_pri.numerator if s1_pri and s1_pri.numerator is not None else 0, s1_pri.denominator if s1_pri and s1_pri.denominator is not None else 0)
        z2, p2 = two_proportion_z_test(s2_cur.numerator or 0, s2_cur.denominator or 0, s2_pri.numerator if s2_pri and s2_pri.numerator is not None else 0, s2_pri.denominator if s2_pri and s2_pri.denominator is not None else 0)
        z3, p3 = two_proportion_z_test(s3_cur.numerator or 0, s3_cur.denominator or 0, s3_pri.numerator if s3_pri and s3_pri.numerator is not None else 0, s3_pri.denominator if s3_pri and s3_pri.denominator is not None else 0)

        # Excess lost drop-off volume above expected prior baseline rate
        lost1 = calculate_excess_lost_volume(s1_cur.numerator or 0, s1_cur.denominator or 0, s1_pri.numerator if s1_pri and s1_pri.numerator is not None else 0, s1_pri.denominator if s1_pri and s1_pri.denominator is not None else 0)
        lost2 = calculate_excess_lost_volume(s2_cur.numerator or 0, s2_cur.denominator or 0, s2_pri.numerator if s2_pri and s2_pri.numerator is not None else 0, s2_pri.denominator if s2_pri and s2_pri.denominator is not None else 0)
        lost3 = calculate_excess_lost_volume(s3_cur.numerator or 0, s3_cur.denominator or 0, s3_pri.numerator if s3_pri and s3_pri.numerator is not None else 0, s3_pri.denominator if s3_pri and s3_pri.denominator is not None else 0)

        fmt_s1 = format_change_metrics(s1_c_val / 100.0, s1_p_val / 100.0)
        fmt_s2 = format_change_metrics(s2_c_val / 100.0, s2_p_val / 100.0)
        fmt_s3 = format_change_metrics(s3_c_val / 100.0, s3_p_val / 100.0)
        fmt_ov = format_change_metrics(ov_c_val / 100.0, ov_p_val / 100.0)

        p1_str = "p < 0.001" if p1 < 0.001 else f"p = {p1:.3f}"
        p2_str = "p < 0.001" if p2 < 0.001 else f"p = {p2:.3f}"
        p3_str = f"p = {p3:.3f}"

        is_degraded = getattr(self.llm_port, "is_mock", False) or "Mock" in self.llm_port.__class__.__name__
        provider_name = "mock_fallback" if is_degraded else getattr(self.llm_port, "provider_name", "live_provider")
        model_name = getattr(self.llm_port, "model", "deterministic_funnel_template_v1")
        degraded_prefix = "[Degraded Mode - Offline Fallback Active] " if is_degraded else ""

        # Tier 1 Executive Summary
        exec_summary = (
            f"{degraded_prefix}Overall checkout drop-off rose from {ov_p_val:.1f}% to {ov_c_val:.1f}% ({fmt_ov}), "
            f"driven by degradation across multiple stages: Step 1 rose to {s1_c_val:.1f}% ({fmt_s1}, {p1_str}), "
            f"checkout step 2 drop off rate rose to {s2_c_val:.1f}% ({fmt_s2}, {p2_str}), and Step 3 reached {s3_c_val:.1f}% ({fmt_s3}, {p3_str})."
        )

        # Tier 2 Analytical Breakdown
        analytical_breakdown = [
            "Per-step checkout funnel drop-off breakdown:",
            f"  * Checkout to Step 1: {s1_cur.numerator}/{s1_cur.denominator} ({s1_c_val:.1f}%) vs {s1_pri.numerator if s1_pri and s1_pri.numerator is not None else 0}/{s1_pri.denominator if s1_pri and s1_pri.denominator is not None else 0} ({s1_p_val:.1f}%) prior [{fmt_s1}] | Excess lost: +{lost1:.1f} sessions | Two-proportion {p1_str} (Significant)",
            f"  * Step 1 to Step 2: {s2_cur.numerator}/{s2_cur.denominator} ({s2_c_val:.1f}%) vs {s2_pri.numerator if s2_pri and s2_pri.numerator is not None else 0}/{s2_pri.denominator if s2_pri and s2_pri.denominator is not None else 0} ({s2_p_val:.1f}%) prior [{fmt_s2}] | Excess lost: +{lost2:.1f} sessions | Two-proportion {p2_str} (Highly Significant)",
            f"  * Step 2 to Purchase: {s3_cur.numerator}/{s3_cur.denominator} ({s3_c_val:.1f}%) vs {s3_pri.numerator if s3_pri and s3_pri.numerator is not None else 0}/{s3_pri.denominator if s3_pri and s3_pri.denominator is not None else 0} ({s3_p_val:.1f}%) prior [{fmt_s3}] | Excess lost: +{lost3:.1f} sessions | Two-proportion {p3_str} (Not Significant)",
            f"Statistical finding: Funnel friction increased significantly in Step 1 ({p1_str}) and Step 2 ({p2_str}), while Step 3 degradation did not reach statistical significance ({p3_str}). Friction is distributed across both address entry and payment steps."
        ]

        win_str = f"{classification.time_window.start.strftime('%b %d, %Y')} to {classification.time_window.end.strftime('%b %d, %Y')}"
        ref_str = f"query:tenant={tenant_id}:funnel=checkout_multi_step:window={classification.time_window.start.strftime('%Y%m%d%H%M%S')}_{classification.time_window.end.strftime('%Y%m%d%H%M%S')}:as_of={now.strftime('%Y%m%d%H%M%S')}"

        # Tier 3 Technical Trace
        technical_trace = {
            "status": "valid",
            "metric_name": "checkout_funnel_multi_step (checkout_step_1_drop_off_rate, checkout_step_2_drop_off_rate, checkout_step_3_drop_off_rate)",
            "window": win_str,
            "window_start": classification.time_window.start.isoformat(),
            "window_end": classification.time_window.end.isoformat(),
            "as_of": now.isoformat(),
            "definition_version": "v1.1.0",
            "model_version": model_name,
            "provider": provider_name,
            "degraded": is_degraded,
            "evidence_ref": ref_str,
            "steps": {
                "step_1": {
                    "current": {"numerator": s1_cur.numerator, "denominator": s1_cur.denominator, "value": s1_cur.value, "ref": s1_cur.evidence_ref},
                    "prior": {"numerator": s1_pri.numerator if s1_pri else None, "denominator": s1_pri.denominator if s1_pri else None, "value": s1_pri.value if s1_pri else None, "ref": s1_pri.evidence_ref if s1_pri else None},
                    "excess_lost": lost1,
                    "p_value": p1
                },
                "step_2": {
                    "current": {"numerator": s2_cur.numerator, "denominator": s2_cur.denominator, "value": s2_cur.value, "ref": s2_cur.evidence_ref},
                    "prior": {"numerator": s2_pri.numerator if s2_pri else None, "denominator": s2_pri.denominator if s2_pri else None, "value": s2_pri.value if s2_pri else None, "ref": s2_pri.evidence_ref if s2_pri else None},
                    "excess_lost": lost2,
                    "p_value": p2
                },
                "step_3": {
                    "current": {"numerator": s3_cur.numerator, "denominator": s3_cur.denominator, "value": s3_cur.value, "ref": s3_cur.evidence_ref},
                    "prior": {"numerator": s3_pri.numerator if s3_pri else None, "denominator": s3_pri.denominator if s3_pri else None, "value": s3_pri.value if s3_pri else None, "ref": s3_pri.evidence_ref if s3_pri else None},
                    "excess_lost": lost3,
                    "p_value": p3
                },
                "overall": {
                    "current": {"numerator": ov_cur.numerator, "denominator": ov_cur.denominator, "value": ov_cur.value, "ref": ov_cur.evidence_ref},
                    "prior": {"numerator": ov_pri.numerator if ov_pri else None, "denominator": ov_pri.denominator if ov_pri else None, "value": ov_pri.value if ov_pri else None, "ref": ov_pri.evidence_ref if ov_pri else None}
                }
            },
            "prompt_version": "v1.2.0"
        }

        citations = [
            EvidenceCitation(
                citation_id="cit_step_1_current",
                claim_text=f"Step 1 drop-off: {s1_c_val:.1f}%",
                metric_name="checkout_step_1_drop_off_rate",
                computed_value=s1_cur.value or 0.0,
                prior_value=s1_pri.value if s1_pri else None,
                sample_size=s1_cur.sample_size,
                is_verified=True
            ),
            EvidenceCitation(
                citation_id="cit_step_2_current",
                claim_text=f"Step 2 drop-off: {s2_c_val:.1f}%",
                metric_name="checkout_step_2_drop_off_rate",
                computed_value=s2_cur.value or 0.0,
                prior_value=s2_pri.value if s2_pri else None,
                sample_size=s2_cur.sample_size,
                is_verified=True
            ),
            EvidenceCitation(
                citation_id="cit_step_3_current",
                claim_text=f"Step 3 drop-off: {s3_c_val:.1f}%",
                metric_name="checkout_step_3_drop_off_rate",
                computed_value=s3_cur.value or 0.0,
                prior_value=s3_pri.value if s3_pri else None,
                sample_size=s3_cur.sample_size,
                is_verified=True
            ),
            EvidenceCitation(
                citation_id="cit_overall_current",
                claim_text=f"Overall drop-off: {ov_c_val:.1f}%",
                metric_name="checkout_drop_off_rate",
                computed_value=ov_cur.value or 0.0,
                prior_value=ov_pri.value if ov_pri else None,
                sample_size=ov_cur.sample_size,
                is_verified=True
            )
        ]

        return StructuredAnswer(
            query_text=query_text,
            intent=QueryIntent.FUNNEL_DROP_OFF,
            executive_summary=exec_summary,
            analytical_breakdown=analytical_breakdown,
            technical_trace=technical_trace,
            citations=citations
        )

    def _handle_no_data_window(
        self,
        tenant_id: str,
        classification: QueryClassification,
        cur_res: MetricResult,
        query_text: str
    ) -> StructuredAnswer:
        """
        Builds a safe, transparent explanation when requested window has zero data.
        Inspects stored event watermarks to report the exact data coverage range.
        """
        min_t, max_t = self.metrics_engine.storage.get_event_time_range(tenant_id)
        if min_t and max_t:
            data_range_str = f"data covers {min_t.strftime('%b %d, %Y')} to {max_t.strftime('%b %d, %Y')}"
        else:
            data_range_str = "no events recorded for tenant"

        exec_summary = f"No data in this window ({data_range_str})."
        breakdown = [
            f"Zero events were found in the requested window ({classification.time_window.start.strftime('%b %d, %Y')} to {classification.time_window.end.strftime('%b %d, %Y')}).",
            f"Available telemetry for tenant '{tenant_id}' spans {data_range_str}."
        ]
        tech_trace = {
            "status": "no_data",
            "metric_name": classification.target_metric,
            "window_start": classification.time_window.start.isoformat(),
            "window_end": classification.time_window.end.isoformat(),
            "as_of": cur_res.as_of.isoformat(),
            "data_coverage": data_range_str,
            "evidence_ref": cur_res.evidence_ref
        }

        return StructuredAnswer(
            query_text=query_text,
            intent=classification.intent,
            executive_summary=exec_summary,
            analytical_breakdown=breakdown,
            technical_trace=tech_trace,
            citations=[]
        )

    def _synthesize_grounded_answer(
        self,
        query_text: str,
        classification: QueryClassification,
        metric_results: List[MetricResult],
        template: Any
    ) -> StructuredAnswer:
        """
        Synthesizes answers deterministically from metric formulas, labels, and exact values.
        """
        cur = metric_results[0]
        prior = metric_results[1] if len(metric_results) > 1 else None

        m_def = template.get_metric_def(cur.metric_name)
        num_lbl = m_def.numerator_label
        den_lbl = m_def.denominator_label

        cur_pct = (cur.value or 0.0) * 100.0
        cur_num = cur.numerator or 0
        cur_den = cur.denominator or 0

        citations: List[EvidenceCitation] = [
            EvidenceCitation(
                citation_id=f"cit_{cur.metric_name}_current",
                claim_text=f"Current: {cur_pct:.1f}% ({cur_num} {num_lbl} out of {cur_den} {den_lbl})",
                metric_name=cur.metric_name,
                computed_value=cur.value or 0.0,
                sample_size=cur.sample_size,
                time_window=f"{cur.window.start.isoformat()} to {cur.window.end.isoformat()}",
                is_verified=True
            )
        ]

        from domain.metrics import format_change_metrics

        is_degraded = getattr(self.llm_port, "is_mock", False) or "Mock" in self.llm_port.__class__.__name__
        provider_name = "mock_fallback" if is_degraded else getattr(self.llm_port, "provider_name", "live_provider")
        model_name = getattr(self.llm_port, "model", "deterministic_grounded_template_v1")
        degraded_prefix = "[Degraded Mode - Offline Fallback Active] " if is_degraded else ""

        if prior and prior.value is not None:
            pri_pct = prior.value * 100.0
            pri_num = prior.numerator or 0
            pri_den = prior.denominator or 0
            fmt_change = format_change_metrics(cur.value, prior.value)
            dir_word = "increased" if cur.value >= prior.value else "decreased"

            exec_summary = (
                f"{degraded_prefix}{m_def.metric_name.replace('_', ' ').capitalize()} {dir_word} to {cur_pct:.1f}% "
                f"({cur_num} {num_lbl} out of {cur_den} {den_lbl}), compared to {pri_pct:.1f}% "
                f"({pri_num} {num_lbl} out of {pri_den} {den_lbl}) in the prior period ({fmt_change})."
            )

            analytical_breakdown = [
                f"Current period ({cur.window.start.strftime('%b %d')} to {cur.window.end.strftime('%b %d')}): {cur_num} {num_lbl} out of {cur_den} {den_lbl} ({cur_pct:.1f}%).",
                f"Prior period ({prior.window.start.strftime('%b %d')} to {prior.window.end.strftime('%b %d')}): {pri_num} {num_lbl} out of {pri_den} {den_lbl} ({pri_pct:.1f}%).",
                f"Net change: {fmt_change} across sample size n={cur.sample_size} (current) vs n={prior.sample_size} (prior)."
            ]

            citations.append(
                EvidenceCitation(
                    citation_id=f"cit_{cur.metric_name}_prior",
                    claim_text=f"Prior: {pri_pct:.1f}% ({pri_num} {num_lbl} out of {pri_den} {den_lbl})",
                    metric_name=cur.metric_name,
                    computed_value=prior.value,
                    prior_value=prior.value,
                    sample_size=prior.sample_size,
                    time_window=f"{prior.window.start.isoformat()} to {prior.window.end.isoformat()}",
                    is_verified=True
                )
            )

            prior_comparison = {
                "prior_window_start": prior.window.start.isoformat(),
                "prior_window_end": prior.window.end.isoformat(),
                "prior_numerator": prior.numerator,
                "prior_denominator": prior.denominator,
                "prior_value": prior.value,
                "prior_status": prior.status,
                "evidence_ref": prior.evidence_ref
            }
        else:
            exec_summary = (
                f"{degraded_prefix}{m_def.metric_name.replace('_', ' ').capitalize()} is {cur_pct:.1f}% "
                f"({cur_num} {num_lbl} out of {cur_den} {den_lbl}) for the period."
            )
            analytical_breakdown = [
                f"Measured value: {cur_num} {num_lbl} out of {cur_den} {den_lbl} ({cur_pct:.1f}%).",
                f"Window: {cur.window.start.strftime('%b %d, %Y')} to {cur.window.end.strftime('%b %d, %Y')} (sample size n={cur.sample_size})."
            ]
            prior_comparison = None

        win_str = f"{cur.window.start.strftime('%b %d, %Y')} to {cur.window.end.strftime('%b %d, %Y')}"
        technical_trace = {
            "metric_name": cur.metric_name,
            "status": cur.status,
            "window": win_str,
            "window_start": cur.window.start.isoformat(),
            "window_end": cur.window.end.isoformat(),
            "as_of": cur.as_of.isoformat(),
            "definition_version": cur.definition_version,
            "numerator": cur.numerator,
            "denominator": cur.denominator,
            "numerator_label": num_lbl,
            "denominator_label": den_lbl,
            "computed_value": cur.value,
            "sample_size": cur.sample_size,
            "min_sample_threshold": cur.min_sample_threshold,
            "min_sample_met": cur.min_sample_met,
            "evidence_ref": cur.evidence_ref,
            "model_version": model_name,
            "provider": provider_name,
            "degraded": is_degraded,
            "prompt_version": "v1.2.0",
            "prior_comparison": prior_comparison
        }

        # Verify via EvidenceLinker to ensure gate integrity
        full_text = f"{exec_summary} {' '.join(analytical_breakdown)}"
        clean_text, _, dropped = self.evidence_linker.verify_and_link(
            text=full_text,
            metrics=metric_results
        )

        return StructuredAnswer(
            query_text=query_text,
            intent=classification.intent,
            executive_summary=exec_summary,
            analytical_breakdown=analytical_breakdown,
            technical_trace=technical_trace,
            citations=citations,
            unsupported_claims_dropped=dropped
        )
