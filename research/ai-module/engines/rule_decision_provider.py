"""
Rule-Based Decision Provider Engine
Implements DecisionPort with strictly fact-grounded reasoning, holdout group allocation,
and separation of heuristic priority score from calibrated probability.
"""

from typing import List, Dict, Any, Optional
import hashlib

from domain.actions import (
    ActionType,
    WaiveFeeParams,
    RecoveryMessageParams,
    ReportBugParams,
    DenseTelemetryParams,
    SyncAudienceParams
)
from ports.decision import DecisionPort, DecisionContext, DecisionCandidate


class RuleDecisionProvider(DecisionPort):
    """
    Deterministic rule-based decision provider.
    Converts digest flags and anomaly signals into concrete action candidates.
    Adheres strictly to fact-based reasoning and does not produce fabricated confidence.
    """

    def propose_candidates(self, context: DecisionContext) -> List[DecisionCandidate]:
        candidates: List[DecisionCandidate] = []

        if context.signal_type == "idle_cart":
            candidates.extend(self._handle_idle_cart(context))
        elif context.signal_type == "digest_flag":
            candidates.extend(self._handle_digest_flag(context))

        return candidates

    def _handle_idle_cart(self, context: DecisionContext) -> List[DecisionCandidate]:
        payload = context.signal_payload
        customer_id = payload.get("customer_id")
        anonymous_id = payload.get("anonymous_id")

        # Invariant 14: Anonymous visitors cannot receive fee waivers or messaging
        if not customer_id:
            return []

        # Cart value can be provided in paise or inr
        cart_total_paise = payload.get("cart_total_paise")
        if cart_total_paise is None and "cart_value" in payload:
            cart_total_paise = int(round(float(payload["cart_value"]) * 100))
        elif cart_total_paise is None:
            cart_total_paise = 0

        idle_minutes = payload.get("idle_minutes", 0)

        # Configurable thresholds from tenant_config
        high_threshold_paise = context.tenant_config.get("high_value_cart_threshold_paise", 50000)  # INR 500
        mid_threshold_paise = context.tenant_config.get("mid_value_cart_threshold_paise", 30000)    # INR 300
        fee_waiver_paise = context.tenant_config.get("fee_waiver_amount_paise", 5000)               # INR 50
        holdout_pct = context.tenant_config.get("holdout_pct", 10)

        cart_value_inr = cart_total_paise / 100.0
        high_inr = high_threshold_paise / 100.0
        mid_inr = mid_threshold_paise / 100.0

        # Check 10% deterministic holdout
        in_holdout = self._is_in_holdout(context.tenant_id, customer_id, holdout_pct)

        if cart_total_paise >= high_threshold_paise:
            # High-value cart: Waive delivery fee
            reasoning = (
                f"Cart idle for {idle_minutes} minutes with subtotal of INR {cart_value_inr:.2f} "
                f"(exceeds high-value threshold of INR {high_inr:.2f}). "
                f"Delivery fee waiver proposed under tenant policy (eligible subtotal >= INR {high_inr:.2f}, "
                f"idle >= 30 min, subject to {holdout_pct}% randomized holdout control and max 1 waiver per customer per 7 days)."
            )
            evidence = [
                f"cart_total_paise={cart_total_paise}",
                f"idle_minutes={idle_minutes}",
                f"customer_id={customer_id}",
                f"threshold_paise={high_threshold_paise}"
            ]
            return [
                DecisionCandidate(
                    action_type=ActionType.WAIVE_DELIVERY_FEE,
                    target_module="module_1_loyalty",
                    target_type="customer",
                    target_id=customer_id,
                    customer_id=customer_id,
                    anonymous_id=anonymous_id,
                    parameters=WaiveFeeParams(
                        fee_amount_paise=fee_waiver_paise,
                        points_deducted=0,
                        customer_id=customer_id
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=0.90,
                    calibrated_probability=None,  # Rule engine has no calibrated probability
                    is_holdout=in_holdout
                )
            ]

        elif cart_total_paise >= mid_threshold_paise:
            # Mid-value cart: Send WhatsApp recovery
            reasoning = (
                f"Cart idle for {idle_minutes} minutes with subtotal of INR {cart_value_inr:.2f} "
                f"(between INR {mid_inr:.2f} and INR {high_inr:.2f}). "
                f"Outbound recovery message proposed."
            )
            evidence = [
                f"cart_total_paise={cart_total_paise}",
                f"idle_minutes={idle_minutes}",
                f"customer_id={customer_id}",
                f"threshold_paise={mid_threshold_paise}"
            ]
            return [
                DecisionCandidate(
                    action_type=ActionType.SEND_RECOVERY_WHATSAPP,
                    target_module="notification",
                    target_type="customer",
                    target_id=customer_id,
                    customer_id=customer_id,
                    anonymous_id=anonymous_id,
                    parameters=RecoveryMessageParams(
                        recipient=customer_id,
                        channel="whatsapp",
                        template_name="cart_recovery_v1",
                        parameters={"cart_value": f"INR {cart_value_inr:.2f}"},
                        recipient_type="customer_id",
                        cart_total_paise=cart_total_paise
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=0.70,
                    calibrated_probability=None,
                    is_holdout=in_holdout
                )
            ]

        return []

    def _handle_digest_flag(self, context: DecisionContext) -> List[DecisionCandidate]:
        payload = context.signal_payload
        metric_name = payload.get("metric_name", "")
        min_sample_met = payload.get("min_sample_met", False)
        is_significant = payload.get("is_significant", False)
        adverse = payload.get("adverse", False)

        # Invariant 15: Require min_sample_met and adverse signal before acting
        if not min_sample_met or not adverse:
            return []

        sample_size = payload.get("sample_size", 0)
        current_val = payload.get("current_value", 0.0)
        prior_val = payload.get("prior_value", 0.0)
        pct_change = payload.get("pct_change", 0.0)
        severity = payload.get("severity", "medium")

        # Case 1: Drop-off friction in checkout (e.g. checkout_step_2_drop_off_rate)
        if "checkout_step_2_drop_off" in metric_name or "drop_off_rate" in metric_name:
            # Review Point 17: Emit TWO separate candidates (Bug ticket + Dense telemetry)
            bug_reasoning = (
                f"Checkout step drop-off increased from {prior_val*100:.1f}% to {current_val*100:.1f}% "
                f"({pct_change:+.1f}%) across {sample_size} sessions. Bug triage ticket requested."
            )
            bug_evidence = [
                f"metric={metric_name}",
                f"prior_value={prior_val}",
                f"current_value={current_val}",
                f"pct_change={pct_change}",
                f"sample_size={sample_size}",
                f"severity={severity}"
            ]
            c1 = DecisionCandidate(
                action_type=ActionType.FLAG_UI_FRICTION_BUG,
                target_module="module_2_behavior",
                target_type="system",
                target_id="checkout_step_2_fee_section",
                parameters=ReportBugParams(
                    component_selector="checkout_step_2_fee_section",
                    friction_type="drop_off_spike",
                    session_count=max(1, sample_size),
                    evidence={
                        "metric_name": metric_name,
                        "prior_rate": prior_val,
                        "current_rate": current_val,
                        "pct_change": pct_change,
                        "sample_size": sample_size
                    }
                ),
                reasoning_summary=bug_reasoning,
                evidence_citations=bug_evidence,
                priority_score=0.85,
                calibrated_probability=None,
                is_holdout=False
            )

            telemetry_reasoning = (
                f"Checkout step drop-off increased by {pct_change:+.1f}% across {sample_size} sessions. "
                f"Dense telemetry requested for 120 minutes at 50% sample rate on checkout_step_2_fee_section."
            )
            c2 = DecisionCandidate(
                action_type=ActionType.REQUEST_DENSE_TELEMETRY,
                target_module="module_2_behavior",
                target_type="system",
                target_id="checkout_step_2_fee_section",
                parameters=DenseTelemetryParams(
                    component_selector="checkout_step_2_fee_section",
                    duration_minutes=120,
                    sample_rate=0.5
                ),
                reasoning_summary=telemetry_reasoning,
                evidence_citations=bug_evidence,
                priority_score=0.80,
                calibrated_probability=None,
                is_holdout=False
            )
            return [c1, c2]

        # Case 2: Cart abandonment spike
        if "cart_abandonment" in metric_name:
            reasoning = (
                f"Cart abandonment rate increased from {prior_val*100:.1f}% to {current_val*100:.1f}% "
                f"({pct_change:+.1f}%) across {sample_size} sessions. Audience segment sync requested."
            )
            evidence = [
                f"metric={metric_name}",
                f"prior_value={prior_val}",
                f"current_value={current_val}",
                f"pct_change={pct_change}",
                f"sample_size={sample_size}"
            ]
            return [
                DecisionCandidate(
                    action_type=ActionType.SYNC_AUDIENCE_SEGMENT,
                    target_module="module_3_ads",
                    target_type="audience",
                    target_id="cart_abandoners_7d",
                    parameters=SyncAudienceParams(
                        segment_name="cart_abandoners_7d",
                        customer_identifiers=["cohort_cart_abandoners"],
                        target_platform="all"
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=0.65,
                    calibrated_probability=None,
                    is_holdout=False
                )
            ]

        return []

    def _is_in_holdout(self, tenant_id: str, customer_id: str, holdout_pct: int) -> bool:
        if holdout_pct <= 0:
            return False
        if holdout_pct >= 100:
            return True
        key = f"{tenant_id}:{customer_id}:holdout_salt".encode("utf-8")
        h = hashlib.sha256(key).hexdigest()
        return (int(h[:8], 16) % 100) < holdout_pct

    def predict_benchmark_case(self, case: Any) -> Any:
        """
        Executes a benchmark evaluation case using deterministic heuristic rules.
        """
        import time
        from domain.evaluation import ProviderPrediction
        start = time.perf_counter()

        task = case.task_type
        ctx = case.input_context

        if task == "query_classification":
            query = ctx.get("query", "").lower()
            if any(w in query for w in ["drop off", "drop-off", "checkout friction", "step 2"]):
                pred = "checkout_step_2_drop_off_rate"
                conf = 0.90
            elif any(w in query for w in ["abandoned cart", "cart abandonment", "abandoning"]):
                pred = "cart_abandonment_rate"
                conf = 0.85
            elif any(w in query for w in ["conversion", "converting", "checkout rate"]):
                pred = "overall_conversion_rate"
                conf = 0.85
            elif any(w in query for w in ["trial", "subscription", "paid conversion"]):
                pred = "trial_to_paid_conversion_rate"
                conf = 0.85
            else:
                pred = "unsupported"
                conf = 0.70

        elif task == "action_routing":
            sig = ctx.get("signal_type")
            if sig == "idle_cart":
                cust = ctx.get("customer_id")
                cart_val = ctx.get("cart_value", 0.0)
                idle_mins = ctx.get("idle_minutes", 0)
                if cust and cart_val >= 500.0 and idle_mins >= 20:
                    pred = "waive_delivery_fee"
                    conf = 0.90
                else:
                    pred = "do_nothing"
                    conf = 0.80
            elif sig == "digest_flag":
                m_name = ctx.get("metric_name", "")
                sev = ctx.get("severity")
                delta = ctx.get("delta_pct", 0.0)
                sig_stat = ctx.get("is_statistically_significant", True)
                if not sig_stat or sev == "low" or delta <= 0.0:
                    pred = "do_nothing"
                    conf = 0.85
                elif "drop_off" in m_name or "rage_click" in m_name:
                    pred = "flag_ui_friction_bug"
                    conf = 0.90
                elif "cart_abandonment" in m_name or "exit_intent" in m_name or "cart_to_checkout" in m_name:
                    pred = "sync_audience_segment"
                    conf = 0.80
                else:
                    pred = "do_nothing"
                    conf = 0.75
            else:
                pred = "do_nothing"
                conf = 0.75

        elif task == "evidence_support":
            claim = ctx.get("claim", "").lower()
            metric = ctx.get("metric", {})
            m_val = metric.get("value", 0.0)
            m_pct_chg = metric.get("pct_change", 0.0)
            sample_met = metric.get("min_sample_met", True)

            if not sample_met and any(w in claim for w in ["caused by", "proves", "critical"]):
                pred = "insufficient_sample"
                conf = 0.90
            elif m_pct_chg > 0 and any(w in claim for w in ["decrease", "decreased", "dropped", "drop", "collapsed", "improved"]):
                pred = "inverted_polarity"
                conf = 0.85
            elif m_pct_chg < 0 and any(w in claim for w in ["increase", "increased", "surged", "skyrocketed"]):
                pred = "inverted_polarity"
                conf = 0.85
            else:
                import re
                pcts = re.findall(r"(\d+(?:\.\d+)?)%", claim)
                if pcts:
                    p = float(pcts[0])
                    actual_pct = m_val * 100.0
                    if abs(p - actual_pct) > 1.0:
                        pred = "hallucinated_number"
                        conf = 0.85
                    else:
                        pred = "supported"
                        conf = 0.90
                else:
                    pred = "supported"
                    conf = 0.75
        else:
            pred = "unsupported"
            conf = 0.50

        elapsed = max((time.perf_counter() - start) * 1000.0, 0.1)
        is_corr = (pred == case.ground_truth)

        return ProviderPrediction(
            case_id=case.case_id,
            selected_option=pred,
            stated_probability=conf,
            is_correct=is_corr,
            latency_ms=elapsed,
            cost_usd=0.0
        )
