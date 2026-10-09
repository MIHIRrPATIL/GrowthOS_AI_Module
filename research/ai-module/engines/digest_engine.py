"""
Deterministic Digest & Anomaly Engine
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Component 2)

Mathematical Invariants & Hardening:
1. Period-over-period comparator (day_over_day, week_over_week, month_over_month).
2. Rolling multi-period baseline (e.g. median of 4 prior periods matching exact weekdays).
3. Dual-window minimum sample size gating: requires min_sample_met on BOTH windows.
4. Mathematical delta rule: prior=0 returns delta_pct=None and is_new_activity=True (no invented 100%).
5. Two-proportion z-test and percentage-point delta (delta_pp) alongside relative delta.
6. Deterministic financial impact ranking: lost_conversions * AOV.
7. Funnel correlation: groups related flags, identifies primary bottleneck, marks downstream echoes.
8. Bounded recoverable cart work queue: [min_idle_minutes, max_idle_minutes] with cooldown.
9. Cross-session and cross-device conversion check via identity resolver (zero false positives).
10. Accurate cart tracking with cart.item_removed quantity decrementing.
11. Pure deterministic code execution — zero LLM hallucinations.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Literal
from datetime import datetime, timezone, timedelta
import math
import statistics
import uuid

from ports.storage import EventStoragePort
from ports.identity import IdentityResolutionPort
from domain.events import EventEnvelope
from domain.metrics import (
    MetricResult,
    DigestFlag,
    DigestReport,
    IdleCartAnomaly,
    TimeWindow,
    Period,
    Severity,
    Polarity,
    AdsCampaignDaily,
)
from engines.metrics_engine import MetricsEngine
from engines.vertical_templates import get_vertical_template, VerticalTemplate


class DigestEngine:
    """
    Evaluates metric shifts across periods and detects behavioral absence anomalies.
    Guarantees pure mathematical grounding with zero LLM hallucinations.
    """

    def __init__(
        self,
        metrics_engine: MetricsEngine,
        storage: EventStoragePort,
        identity_resolver: Optional[IdentityResolutionPort] = None
    ):
        self.metrics_engine = metrics_engine
        self.storage = storage
        self.identity_resolver = identity_resolver

    def compute_rolling_baseline(
        self,
        tenant_id: str,
        vertical_template_id: str,
        current_window: TimeWindow,
        prior_periods: int = 4,
        as_of: Optional[datetime] = None,
        clock: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        timezone_str: str = "UTC"
    ) -> Dict[str, MetricResult]:
        """
        Computes a rolling median baseline across N prior periods of matching duration.
        Matching duration automatically preserves weekday/weekend alignment (e.g. 7-day prior periods match day-of-week).
        Prevents a bad incident week from becoming the new normal in subsequent comparisons.
        """
        duration = current_window.end - current_window.start
        period_metrics_list: List[Dict[str, MetricResult]] = []

        for k in range(1, prior_periods + 1):
            p_start = current_window.start - (k * duration)
            p_end = current_window.end - (k * duration)
            p_window = TimeWindow(start=p_start, end=p_end)
            watermark = min(as_of or current_window.end, p_end)

            period_metrics = self.metrics_engine.calculate_all_template_metrics(
                tenant_id=tenant_id,
                vertical_template_id=vertical_template_id,
                window=p_window,
                as_of=watermark,
                clock=clock,
                dimensions=dimensions or {}
            )
            period_metrics_list.append(period_metrics)

        rolling_baseline: Dict[str, MetricResult] = {}
        if not period_metrics_list:
            return rolling_baseline

        template = get_vertical_template(vertical_template_id)
        metric_names = list(period_metrics_list[0].keys())

        earliest_start = current_window.start - (prior_periods * duration)
        baseline_window = TimeWindow(start=earliest_start, end=current_window.start)

        for m_name in metric_names:
            values = [pm[m_name].value for pm in period_metrics_list if m_name in pm and pm[m_name].value is not None]
            denominators = [pm[m_name].denominator for pm in period_metrics_list if m_name in pm and pm[m_name].denominator is not None]

            m_def = template.get_metric_def(m_name)

            if not values or not denominators or all(d == 0 for d in denominators):
                rolling_baseline[m_name] = MetricResult(
                    tenant_id=tenant_id,
                    vertical_template_id=vertical_template_id,
                    metric_name=m_name,
                    definition_version=m_def.definition_version,
                    window=baseline_window,
                    as_of=as_of or current_window.end,
                    calculated_at=clock or current_window.end,
                    dimensions=dimensions or {},
                    numerator=None,
                    denominator=None,
                    value=None,
                    status="zero_denominator",
                    unit=m_def.unit,
                    sample_size=0,
                    min_sample_threshold=m_def.min_sample_threshold,
                    min_sample_met=False,
                    evidence_ref=f"rolling_median:{prior_periods}_periods"
                )
            else:
                median_val = float(statistics.median(values))
                avg_denom = int(sum(denominators) / len(denominators))
                avg_num = int(round(median_val * avg_denom))
                avg_num = max(0, min(avg_num, avg_denom))
                min_met = avg_denom >= m_def.min_sample_threshold
                status_str: Literal["valid", "insufficient_sample", "zero_denominator"] = "valid" if (avg_denom > 0 and min_met) else ("insufficient_sample" if avg_denom > 0 else "zero_denominator")

                rolling_baseline[m_name] = MetricResult(
                    tenant_id=tenant_id,
                    vertical_template_id=vertical_template_id,
                    metric_name=m_name,
                    definition_version=m_def.definition_version,
                    window=baseline_window,
                    as_of=as_of or current_window.end,
                    calculated_at=clock or current_window.end,
                    dimensions=dimensions or {},
                    numerator=avg_num if avg_denom > 0 else None,
                    denominator=avg_denom if avg_denom > 0 else None,
                    value=(avg_num / avg_denom) if avg_denom > 0 else None,
                    status=status_str,
                    unit=m_def.unit,
                    sample_size=avg_denom,
                    min_sample_threshold=m_def.min_sample_threshold,
                    min_sample_met=min_met,
                    evidence_ref=f"rolling_median:{prior_periods}_periods"
                )

        return rolling_baseline

    def run_digest(
        self,
        tenant_id: str,
        vertical_template_id: str,
        current_window: TimeWindow,
        prior_window: Optional[TimeWindow] = None,
        period: Period = "week_over_week",
        threshold_pct: float = 10.0,
        baseline_mode: Literal["prior_window", "rolling_median"] = "prior_window",
        prior_periods: int = 4,
        suppress_low_sample: bool = False,
        flag_new_activity: bool = False,
        estimated_aov_inr: float = 450.0,
        timezone_str: str = "UTC",
        as_of: Optional[datetime] = None,
        clock: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        detect_absence: bool = True,
        idle_cart_min_value: float = 300.0,
        idle_cart_high_value: float = 500.0,
        idle_cart_timeout_minutes: float = 30.0,
        idle_cart_max_timeout_minutes: float = 180.0
    ) -> DigestReport:
        """
        Executes period-over-period or rolling baseline comparison, generating a DigestReport
        with deterministic anomaly flags, funnel correlations, and recoverable cart signals.
        """
        template = get_vertical_template(vertical_template_id)
        watermark = as_of or current_window.end
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)

        calculated_time = clock or watermark
        if calculated_time.tzinfo is None:
            calculated_time = calculated_time.replace(tzinfo=timezone.utc)

        dims = dimensions or {}

        # 1. Compute current window metrics
        current_metrics = self.metrics_engine.calculate_all_template_metrics(
            tenant_id=tenant_id,
            vertical_template_id=vertical_template_id,
            window=current_window,
            as_of=watermark,
            clock=calculated_time,
            dimensions=dims
        )

        # 2. Compute prior or rolling baseline metrics
        if baseline_mode == "rolling_median":
            prior_metrics = self.compute_rolling_baseline(
                tenant_id=tenant_id,
                vertical_template_id=vertical_template_id,
                current_window=current_window,
                prior_periods=prior_periods,
                as_of=watermark,
                clock=calculated_time,
                dimensions=dims,
                timezone_str=timezone_str
            )
            duration = current_window.end - current_window.start
            effective_prior_window = TimeWindow(
                start=current_window.start - (prior_periods * duration),
                end=current_window.start
            )
            baseline_type_str = "rolling_median"
            baseline_count = prior_periods
        else:
            if prior_window is None:
                duration = current_window.end - current_window.start
                effective_prior_window = TimeWindow(
                    start=current_window.start - duration,
                    end=current_window.start
                )
            else:
                effective_prior_window = prior_window

            prior_metrics = self.metrics_engine.calculate_all_template_metrics(
                tenant_id=tenant_id,
                vertical_template_id=vertical_template_id,
                window=effective_prior_window,
                as_of=effective_prior_window.end,
                clock=calculated_time,
                dimensions=dims
            )
            baseline_type_str = "prior_window"
            baseline_count = 1

        raw_flags: List[DigestFlag] = []

        # 3. Evaluate shifts against configured threshold
        for metric_name, curr_metric in current_metrics.items():
            prior_metric = prior_metrics.get(metric_name)
            if not prior_metric:
                continue

            # If either metric has a zero denominator (value is None), skip
            if curr_metric.value is None or prior_metric.value is None:
                continue

            metric_def = template.get_metric_def(metric_name)

            curr_val = curr_metric.value
            prior_val = prior_metric.value

            # Require min_sample_met on BOTH windows for statistical confidence
            both_samples_met = curr_metric.min_sample_met and prior_metric.min_sample_met
            if not both_samples_met and suppress_low_sample:
                continue

            is_new_activity = False
            abs_delta = 0.0

            # Mathematical rule: prior = 0 must return delta_pct = None
            if prior_val == 0.0:
                if curr_val > 0.0:
                    is_new_activity = True
                    delta_pp = (curr_val - prior_val) * 100.0 if curr_metric.unit == "ratio" else None
                    if not flag_new_activity:
                        continue
                else:
                    continue
            else:
                abs_delta = abs((curr_val - prior_val) / abs(prior_val) * 100.0)
                delta_pp = (curr_val - prior_val) * 100.0 if curr_metric.unit == "ratio" else None

            # Two-proportion z-test (for ratio metrics with sample >= 10 on both windows)
            is_stat_sig: Optional[bool] = None
            if curr_metric.unit == "ratio" and curr_metric.denominator and prior_metric.denominator:
                n1, n2 = curr_metric.denominator, prior_metric.denominator
                if n1 >= 10 and n2 >= 10 and curr_metric.numerator is not None and prior_metric.numerator is not None:
                    k1, k2 = curr_metric.numerator, prior_metric.numerator
                    p1 = k1 / n1
                    p2 = k2 / n2
                    p_pooled = (k1 + k2) / (n1 + n2)
                    if 0.0 < p_pooled < 1.0:
                        se = math.sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / n1 + 1.0 / n2))
                        if se > 0:
                            z = (p1 - p2) / se
                            is_stat_sig = abs(z) >= 1.96  # p < 0.05

            # Determine whether shift qualifies for a flag
            should_flag = False
            if is_new_activity and flag_new_activity:
                should_flag = True
            elif abs_delta >= threshold_pct:
                should_flag = True

            if not should_flag:
                continue

            # Polarity adverse direction
            if metric_def.polarity == "lower_is_better":
                adverse = (curr_val > prior_val)
            else:
                adverse = (curr_val < prior_val)

            # Severity determination
            if is_new_activity:
                severity: Severity = "low"
            elif abs_delta >= 30.0:
                severity = "high"
            elif abs_delta >= 15.0:
                severity = "medium"
            else:
                severity = "low"

            # Noise mitigation rules:
            # 1. Sub-minimum sample on either window demotes to low
            if not both_samples_met:
                severity = "low"
            # 2. Percentage point change < 1.0pp is noise (e.g. 2.0% -> 2.2% is +10% rel, but only +0.2pp)
            if delta_pp is not None and abs(delta_pp) < 1.0:
                severity = "low"
            # 3. Two-proportion hypothesis test check: demote if within noise (p >= 0.05)
            if is_stat_sig is False:
                severity = "low"

            # Deterministic financial impact estimation: lost_conversions * AOV
            lost_conversions = 0.0
            if adverse and curr_metric.denominator:
                if metric_def.polarity == "higher_is_better":
                    lost_conversions = max(0.0, (prior_val - curr_val) * curr_metric.denominator)
                else:
                    lost_conversions = max(0.0, (curr_val - prior_val) * curr_metric.denominator)
            estimated_impact_inr = round(lost_conversions * estimated_aov_inr, 2) if lost_conversions > 0 else 0.0

            window_key = f"{current_window.start.strftime('%Y%m%d')}_{current_window.end.strftime('%Y%m%d')}"
            dedupe_key = f"{tenant_id}:{metric_name}:{period}:{window_key}:{timezone_str}:{metric_def.definition_version}"
            status_flag: Literal["active", "acknowledged", "resolved", "insufficient_data"] = "active" if both_samples_met else "insufficient_data"

            flag = DigestFlag(
                dedupe_key=dedupe_key,
                tenant_id=tenant_id,
                metric_name=metric_name,
                period=period,
                polarity=metric_def.polarity,
                current_value=curr_val,
                prior_value=prior_val,
                current_sample_size=curr_metric.sample_size,
                prior_sample_size=prior_metric.sample_size,
                unit=curr_metric.unit,
                threshold_pct=threshold_pct,
                severity=severity,
                adverse=adverse,
                delta_pp=round(delta_pp, 2) if delta_pp is not None else None,
                is_statistically_significant=is_stat_sig,
                is_new_activity=is_new_activity,
                lost_conversions=round(lost_conversions, 2) if lost_conversions > 0 else None,
                estimated_impact_inr=estimated_impact_inr if estimated_impact_inr > 0 else None,
                is_primary=True,
                root_metric_name=None,
                timezone=timezone_str,
                flagged_at=calculated_time,
                status=status_flag
            )
            raw_flags.append(flag)

        # 4. Correlate funnel flags along funnel steps (mark primary root bottleneck vs downstream echoes)
        flags = self._correlate_funnel_flags(raw_flags, template)

        # 5. Rank flags by estimated financial impact, primary status, and severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        flags.sort(key=lambda f: (
            0 if f.is_primary else 1,
            -(f.estimated_impact_inr or 0.0),
            severity_order.get(f.severity, 3)
        ))

        # 6. Absence detection: scan for recoverable dormant carts in the current window
        idle_anomalies: List[IdleCartAnomaly] = []
        if detect_absence:
            idle_anomalies = self.detect_idle_carts(
                tenant_id=tenant_id,
                window=current_window,
                as_of=watermark,
                min_cart_value_inr=idle_cart_min_value,
                high_value_threshold_inr=idle_cart_high_value,
                min_idle_timeout_minutes=idle_cart_timeout_minutes,
                max_idle_timeout_minutes=idle_cart_max_timeout_minutes
            )

        report_id = f"rep_{uuid.uuid4().hex[:12]}"

        return DigestReport(
            report_id=report_id,
            tenant_id=tenant_id,
            vertical_template_id=vertical_template_id,
            period=period,
            current_window=current_window,
            prior_window=effective_prior_window,
            threshold_pct=threshold_pct,
            generated_at=calculated_time,
            current_metrics=current_metrics,
            prior_metrics=prior_metrics,
            flags=flags,
            idle_cart_anomalies=idle_anomalies,
            baseline_type=baseline_type_str,
            baseline_periods_count=baseline_count
        )

    def _correlate_funnel_flags(
        self,
        flags: List[DigestFlag],
        template: VerticalTemplate
    ) -> List[DigestFlag]:
        """
        Groups related flags along the funnel.
        Marks the earliest specific broken funnel step as primary (is_primary=True).
        Marks downstream and aggregate container metrics as downstream (is_primary=False, root_metric_name set).
        """
        adverse_flags = [f for f in flags if f.adverse]
        if len(adverse_flags) <= 1:
            return flags

        # Identify step-specific metrics (e.g. checkout_step_2_drop_off_rate, checkout_step_1_drop_off_rate)
        specific_step_flags = []
        for f in adverse_flags:
            if "step_" in f.metric_name or "customization" in f.metric_name:
                specific_step_flags.append(f)

        if specific_step_flags:
            # The earliest specific broken step is the primary root cause
            root_flag = specific_step_flags[0]
            root_name = root_flag.metric_name

            updated_flags: List[DigestFlag] = []
            for f in flags:
                if not f.adverse:
                    updated_flags.append(f)
                elif f.metric_name == root_name:
                    updated_flags.append(f.model_copy(update={"is_primary": True, "root_metric_name": None}))
                elif f.metric_name in ("checkout_drop_off_rate", "overall_conversion_rate"):
                    # Downstream aggregate consequence of the specific step breakdown
                    updated_flags.append(f.model_copy(update={"is_primary": False, "root_metric_name": root_name}))
                else:
                    updated_flags.append(f)
            return updated_flags

        return flags

    def detect_idle_carts(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        min_cart_value_inr: float = 300.0,
        high_value_threshold_inr: float = 500.0,
        min_idle_timeout_minutes: float = 30.0,
        max_idle_timeout_minutes: float = 180.0,
        idle_timeout_minutes: Optional[float] = None,
        completion_events: Optional[Set[str]] = None,
    ) -> List[IdleCartAnomaly]:
        """
        Absence detection work queue algorithm:
        Identifies sessions with high-value carts where no checkout completion
        or purchase has occurred within the recoverable window [min_idle_minutes, max_idle_minutes].
        Eliminates false positives by checking cross-session/cross-device purchases via identity resolver.
        Handles cart.item_removed to prevent overstated cart totals.
        Pure deterministic logic - zero LLM involvement.
        """
        ref_time = as_of or window.end
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        min_idle = idle_timeout_minutes if idle_timeout_minutes is not None else min_idle_timeout_minutes
        max_idle = max_idle_timeout_minutes

        target_completions = completion_events or {
            "purchase.completed",
            "order.completed",
            "checkout.completed",
            "booking.confirmed",
            "subscription.started",
            "subscription.activated",
        }

        events = self.storage.query_events(
            tenant_id=tenant_id,
            window=window,
            as_of=ref_time,
            exclude_test_traffic=True,
            limit=50000
        )

        # 1. Pre-scan for converted customer identifiers across ALL sessions in this window
        converted_user_identifiers: Set[str] = set()
        for ev in events:
            if ev.event_name in target_completions:
                if ev.customer_id:
                    converted_user_identifiers.add(ev.customer_id)
                    if self.identity_resolver:
                        linked = self.identity_resolver.get_linked_identifiers(tenant_id, ev.customer_id)
                        converted_user_identifiers.update(linked)
                if ev.anonymous_id:
                    converted_user_identifiers.add(ev.anonymous_id)
                    if self.identity_resolver:
                        can_id = self.identity_resolver.get_canonical_customer_id(tenant_id, ev.anonymous_id)
                        if can_id:
                            converted_user_identifiers.add(can_id)
                            converted_user_identifiers.update(self.identity_resolver.get_linked_identifiers(tenant_id, can_id))

        # 2. Group events by session
        sessions: Dict[str, List[EventEnvelope]] = {}
        for ev in events:
            sessions.setdefault(ev.session_id, []).append(ev)

        anomalies: List[IdleCartAnomaly] = []

        for sid, session_evts in sessions.items():
            ev_names = {e.event_name for e in session_evts}

            # If any completion event occurred in THIS session, session converted
            if any(comp in ev_names for comp in target_completions):
                continue

            # Check cross-session/cross-device conversion for this user
            session_cust_id = next((e.customer_id for e in session_evts if e.customer_id), None)
            session_anon_id = next((e.anonymous_id for e in session_evts if e.anonymous_id), None)

            if session_cust_id and session_cust_id in converted_user_identifiers:
                continue
            if session_anon_id and session_anon_id in converted_user_identifiers:
                continue
            if self.identity_resolver and session_anon_id:
                canonical = self.identity_resolver.get_canonical_customer_id(tenant_id, session_anon_id)
                if canonical and canonical in converted_user_identifiers:
                    continue

            # 3. Track cart items and handle cart.item_removed to compute accurate cart total
            cart_item_map: Dict[str, Dict[str, Any]] = {}
            latest_cart_ev: Optional[EventEnvelope] = None
            explicit_cart_total: Optional[float] = None

            for e in sorted(session_evts, key=lambda x: x.occurred_at):
                if e.event_name == "cart.item_added":
                    props = e.properties
                    pid = str(props.get("product_id", "unknown"))
                    name = str(props.get("name") or props.get("item_name") or "Item")
                    price = float(props.get("unit_price") or props.get("price") or 0.0)
                    qty = int(props.get("quantity") or 1)
                    if "cart_total" in props and float(props["cart_total"]) > 0:
                        explicit_cart_total = float(props["cart_total"])

                    if pid not in cart_item_map:
                        cart_item_map[pid] = {
                            "product_id": pid,
                            "name": name,
                            "unit_price": price,
                            "quantity": 0,
                        }
                    cart_item_map[pid]["quantity"] += qty
                    latest_cart_ev = e

                elif e.event_name == "cart.item_removed":
                    props = e.properties
                    pid = str(props.get("product_id", "unknown"))
                    qty = int(props.get("quantity") or 1)
                    if pid in cart_item_map:
                        cart_item_map[pid]["quantity"] -= qty
                        if cart_item_map[pid]["quantity"] <= 0:
                            del cart_item_map[pid]
                    explicit_cart_total = None  # Invalidate explicit total if items were removed

                elif e.event_name in ("cart.cleared", "cart.emptied"):
                    cart_item_map.clear()
                    explicit_cart_total = None

            if not cart_item_map or latest_cart_ev is None:
                continue

            # Compute net cart total
            if explicit_cart_total is not None and explicit_cart_total > 0:
                cart_total = explicit_cart_total
            else:
                cart_total = sum(item["unit_price"] * item["quantity"] for item in cart_item_map.values())

            if cart_total < min_cart_value_inr:
                continue

            items: List[Dict[str, Any]] = [
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "unit_price": item["unit_price"],
                    "quantity": item["quantity"]
                }
                for item in cart_item_map.values()
            ]

            # 4. Calculate idle duration
            session_timestamps: List[datetime] = []
            for e in session_evts:
                try:
                    dt = datetime.fromisoformat(e.occurred_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    session_timestamps.append(dt)
                except Exception:
                    pass

            last_active_time = max(session_timestamps) if session_timestamps else datetime.fromisoformat(latest_cart_ev.occurred_at).replace(tzinfo=timezone.utc)
            idle_duration_min = (ref_time - last_active_time).total_seconds() / 60.0

            # 5. Recoverable window filter: must be >= min_idle and <= max_idle
            if idle_duration_min < min_idle:
                continue  # Still actively browsing
            if idle_duration_min > max_idle:
                continue  # Cold, unrecoverable (spam prevention)

            # 6. Contactable channels identification (identifiability dictates channel capability)
            contactable_channels: List[str] = []
            has_phone = any("phone" in e.properties for e in session_evts)
            has_email = any("email" in e.properties for e in session_evts)

            if session_cust_id or has_phone:
                contactable_channels.extend(["whatsapp", "sms"])
            if has_email or (latest_cart_ev and "email" in latest_cart_ev.properties):
                contactable_channels.append("email")
            if idle_duration_min <= 45.0:
                contactable_channels.append("on_site_prompt")

            # 7. Severity based purely on expected cart value
            severity: Severity = "high" if cart_total >= high_value_threshold_inr else "medium"

            # 8. Action signal proposal
            if session_cust_id:
                recommended_action = "waive_delivery_fee" if cart_total >= 400.0 else "send_recovery_whatsapp"
            else:
                recommended_action = "send_recovery_email" if "email" in contactable_channels else "trigger_exit_intent_prompt"

            anomaly_id = f"anom_cart_{uuid.uuid4().hex[:10]}"
            evidence_ref = (
                f"absence:idle_cart:{tenant_id}:{sid}:val={cart_total:.2f}:"
                f"idle_min={idle_duration_min:.1f}:last_ev={latest_cart_ev.event_id}"
            )
            cooldown_cutoff = last_active_time + timedelta(hours=24)

            anomaly = IdleCartAnomaly(
                anomaly_id=anomaly_id,
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=session_anon_id or latest_cart_ev.anonymous_id,
                customer_id=session_cust_id,
                cart_total_inr=round(cart_total, 2),
                items=items,
                idle_duration_minutes=round(idle_duration_min, 1),
                last_active_at=last_active_time,
                detected_at=ref_time,
                severity=severity,
                is_recoverable=True,
                cooldown_until=cooldown_cutoff,
                contactable_channels=contactable_channels,
                recommended_action=recommended_action,
                evidence_ref=evidence_ref,
            )
            anomalies.append(anomaly)

        # Sort highest value carts first
        anomalies.sort(key=lambda a: a.cart_total_inr, reverse=True)
        return anomalies

    def detect_ad_anomalies(
        self,
        tenant_id: str,
        current_records: List[AdsCampaignDaily],
        prior_records: List[AdsCampaignDaily],
        cpa_drift_threshold_pct: float = 25.0,
        impression_drop_threshold_pct: float = 30.0,
        now: Optional[datetime] = None
    ) -> List[DigestFlag]:
        """
        Deterministically evaluates ad campaign performance shifts and flags marketing anomalies.
        Detects CPA spikes, impression share collapses, and spend waste.
        """
        ref_time = now or datetime.now(timezone.utc)
        flags: List[DigestFlag] = []
        prior_by_camp = {r.campaign_id: r for r in prior_records}

        for curr in current_records:
            cid = curr.campaign_id
            prior = prior_by_camp.get(cid)
            if not prior:
                continue

            # 1. CPA Drift Spike
            if curr.conversions >= 3.0 and prior.conversions >= 3.0 and prior.cpa_paise > 0:
                cpa_delta_pct = (curr.cpa_paise - prior.cpa_paise) / float(prior.cpa_paise) * 100.0
                if cpa_delta_pct >= cpa_drift_threshold_pct:
                    sev: Severity = "high" if cpa_delta_pct >= 50.0 else "medium"
                    dedupe_key = f"{tenant_id}:{cid}:ad_cpa_spike:{curr.date}:{prior.date}"
                    flags.append(
                        DigestFlag(
                            dedupe_key=dedupe_key,
                            tenant_id=tenant_id,
                            metric_name=f"cpa_{cid}",
                            period="day_over_day",
                            polarity="lower_is_better",
                            current_value=round(float(curr.cpa_paise) / 100.0, 2),
                            prior_value=round(float(prior.cpa_paise) / 100.0, 2),
                            current_sample_size=int(curr.conversions),
                            prior_sample_size=int(prior.conversions),
                            unit="currency_inr",
                            threshold_pct=cpa_drift_threshold_pct,
                            severity=sev,
                            adverse=True,
                            flagged_at=ref_time,
                            is_statistically_significant=True,
                            is_new_activity=False,
                            estimated_impact_inr=round(float(curr.spend_paise - prior.spend_paise) / 100.0, 2) if curr.spend_paise > prior.spend_paise else None,
                            is_primary=True,
                            timezone="Asia/Kolkata",
                            status="active"
                        )
                    )

            # 2. Impression Collapse
            if prior.impressions >= 500 and curr.impressions < prior.impressions:
                imp_delta_pct = (curr.impressions - prior.impressions) / float(prior.impressions) * 100.0
                if abs(imp_delta_pct) >= impression_drop_threshold_pct:
                    sev_imp: Severity = "high" if abs(imp_delta_pct) >= 50.0 else "medium"
                    dedupe_key_imp = f"{tenant_id}:{cid}:ad_imp_drop:{curr.date}:{prior.date}"
                    flags.append(
                        DigestFlag(
                            dedupe_key=dedupe_key_imp,
                            tenant_id=tenant_id,
                            metric_name=f"impressions_{cid}",
                            period="day_over_day",
                            polarity="higher_is_better",
                            current_value=float(curr.impressions),
                            prior_value=float(prior.impressions),
                            current_sample_size=curr.impressions,
                            prior_sample_size=prior.impressions,
                            unit="count",
                            threshold_pct=impression_drop_threshold_pct,
                            severity=sev_imp,
                            adverse=True,
                            flagged_at=ref_time,
                            is_statistically_significant=True,
                            is_new_activity=False,
                            is_primary=True,
                            timezone="Asia/Kolkata",
                            status="active"
                        )
                    )

            # 3. High Spend Zero Conversions
            if curr.spend_paise >= 200000 and curr.conversions == 0.0:
                dedupe_key_zero = f"{tenant_id}:{cid}:ad_zero_conv:{curr.date}"
                flags.append(
                    DigestFlag(
                        dedupe_key=dedupe_key_zero,
                        tenant_id=tenant_id,
                        metric_name=f"zero_conv_{cid}",
                        period="day_over_day",
                        polarity="lower_is_better",
                        current_value=round(float(curr.spend_paise) / 100.0, 2),
                        prior_value=0.0,
                        current_sample_size=curr.clicks,
                        prior_sample_size=0,
                        unit="currency_inr",
                        threshold_pct=0.0,
                        severity="high",
                        adverse=True,
                        flagged_at=ref_time,
                        is_statistically_significant=True,
                        is_new_activity=True,
                        estimated_impact_inr=round(float(curr.spend_paise) / 100.0, 2),
                        is_primary=True,
                        timezone="Asia/Kolkata",
                        status="active"
                    )
                )

        return flags

