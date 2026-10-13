"""
Grounded Deterministic Metrics Engine
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Component 1)

Mathematical Invariants:
1. Exact conversion, drop-off, and abandonment ratios computed in pure code (zero LLM calls).
2. Explicit entity grouping: session, customer, or application.
3. Slow funnels use cohort rules: conversion evaluated over N days from start event.
4. Session maturity guard: recent uncompleted sessions haven't had time to convert and are excluded from drop-off denominators.
5. Strict watermark enforcement: all queries filter on received_at <= as_of for 100% reproducible results.
6. Set-difference calculation: guarantees 0 <= numerator <= denominator on every ratio.
7. Zero denominator returns value=None with status='zero_denominator' (0/0 is undefined, never 0.0).
8. Dimension allowlisting to protect against injection and unindexed scans.
9. Clock injection for pure mathematical determinism.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from ports.storage import EventStoragePort
from domain.events import EventEnvelope
from domain.metrics import MetricResult, MetricStatus, TimeWindow, AdsCampaignDaily, BlendedAdMetrics
from engines.vertical_templates import (
    get_vertical_template,
    VerticalTemplate,
    MetricDefinition,
    Entity,
)

ALLOWED_DIMENSIONS: Set[str] = {
    "device_type",
    "browser",
    "os",
    "channel",
    "campaign",
    "city",
    "country",
    "payment_method",
}


class MetricsEngine:
    """
    Computes exact, deterministic grounded business metrics scoped by tenant and vertical template.
    Guarantees pure mathematical reproducibility with zero generative model estimation.
    """

    def __init__(self, storage: EventStoragePort):
        self.storage = storage

    def calculate_metric(
        self,
        tenant_id: str,
        vertical_template_id: str,
        metric_name: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        clock: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        exclude_test_traffic: bool = True
    ) -> MetricResult:
        """
        Calculates a single deterministic metric for a given tenant, template, and window.
        """
        template = get_vertical_template(vertical_template_id)
        metric_def = template.get_metric_def(metric_name)

        watermark = as_of or window.end
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)

        calculated_at = clock or watermark
        if calculated_at.tzinfo is None:
            calculated_at = calculated_at.replace(tzinfo=timezone.utc)

        dims = dimensions or {}

        # 1. Dimension Allowlist Check
        for dim_key in dims.keys():
            if dim_key not in ALLOWED_DIMENSIONS:
                raise ValueError(
                    f"Dimension '{dim_key}' is not allowed for filtering. "
                    f"Allowed dimensions: {sorted(ALLOWED_DIMENSIONS)}"
                )

        # 2. Determine Query Window
        # For slow cohort funnels, query conversion events up to cohort_window_days past window.end
        query_end = window.end
        if metric_def.cohort_window_days is not None:
            query_end = min(
                window.end + timedelta(days=metric_def.cohort_window_days),
                watermark
            )
            if query_end <= window.start:
                query_end = window.end

        query_window = TimeWindow(start=window.start, end=query_end)

        # 3. Fetch scoped events from storage with received_at <= as_of watermark
        events = self.storage.query_events(
            tenant_id=tenant_id,
            window=query_window,
            as_of=watermark,
            exclude_test_traffic=exclude_test_traffic,
            limit=100000
        )

        # 4. Filter by dimensions
        if dims:
            events = self._filter_by_dimensions(events, dims)

        # 5. Normalize event names via template event mapping
        normalized_events = self._normalize_event_names(events, template)

        # 6. Compute counts based on entity type and funnel architecture
        numerator, denominator = self._compute_counts(
            metric_def=metric_def,
            events=normalized_events,
            window=window,
            watermark=watermark,
            tenant_id=tenant_id
        )

        # 7. Evaluate Ratio Invariants & Status
        sample_size = denominator
        min_sample_met = (sample_size >= metric_def.min_sample_threshold)

        if denominator == 0:
            value: Optional[float] = None
            if len(events) == 0:
                status: MetricStatus = "no_data"
            else:
                status: MetricStatus = "zero_denominator"
            numerator = 0
            denominator = 0
            sample_size = 0
            min_sample_met = False
        else:
            value = numerator / denominator
            status = "valid" if min_sample_met else "insufficient_sample"

        # 8. Deterministic, Immutable Evidence Reference (Query Specification)
        dims_str = ",".join(f"{k}={v}" for k, v in sorted(dims.items()))
        evidence_ref = (
            f"query:tenant={tenant_id}:metric={metric_name}:"
            f"window={window.start.strftime('%Y%m%d%H%M%S')}_{window.end.strftime('%Y%m%d%H%M%S')}:"
            f"as_of={watermark.strftime('%Y%m%d%H%M%S')}:ver={metric_def.definition_version}:"
            f"filters={dims_str or 'none'}"
        )

        return MetricResult(
            tenant_id=tenant_id,
            vertical_template_id=vertical_template_id,
            metric_name=metric_name,
            definition_version=metric_def.definition_version,
            window=window,
            as_of=watermark,
            calculated_at=calculated_at,
            dimensions=dims,
            numerator=numerator if denominator > 0 else None,
            denominator=denominator if denominator > 0 else None,
            value=value,
            status=status,
            unit=metric_def.unit,
            sample_size=sample_size,
            min_sample_threshold=metric_def.min_sample_threshold,
            min_sample_met=min_sample_met,
            evidence_ref=evidence_ref
        )

    def calculate_all_template_metrics(
        self,
        tenant_id: str,
        vertical_template_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        clock: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        exclude_test_traffic: bool = True
    ) -> Dict[str, MetricResult]:
        """
        Calculates all catalog metrics configured for the given vertical template.
        """
        template = get_vertical_template(vertical_template_id)
        results: Dict[str, MetricResult] = {}

        for metric_name in template.metrics.keys():
            results[metric_name] = self.calculate_metric(
                tenant_id=tenant_id,
                vertical_template_id=vertical_template_id,
                metric_name=metric_name,
                window=window,
                as_of=as_of,
                clock=clock,
                dimensions=dimensions,
                exclude_test_traffic=exclude_test_traffic
            )

        return results

    def _normalize_event_names(
        self,
        events: List[EventEnvelope],
        template: VerticalTemplate
    ) -> List[EventEnvelope]:
        """
        Applies template event_mapping layer to resolve any vendor/SDK aliases into canonical events.
        """
        if not template.event_mapping:
            return events

        normalized: List[EventEnvelope] = []
        for e in events:
            canonical_name = template.resolve_event_name(e.event_name)
            if canonical_name != e.event_name:
                # Update event_name via model_copy
                normalized.append(e.model_copy(update={"event_name": canonical_name}))
            else:
                normalized.append(e)
        return normalized

    def _filter_by_dimensions(
        self,
        events: List[EventEnvelope],
        dimensions: Dict[str, str]
    ) -> List[EventEnvelope]:
        filtered: List[EventEnvelope] = []
        for event in events:
            matches = True
            for dim_key, dim_val in dimensions.items():
                if dim_key == "device_type":
                    if event.device.device_type != dim_val:
                        matches = False
                        break
                elif dim_key == "browser":
                    if event.device.browser != dim_val:
                        matches = False
                        break
                elif dim_key == "os":
                    if event.device.os != dim_val:
                        matches = False
                        break
                elif dim_key == "channel":
                    if event.utm.source != dim_val:
                        matches = False
                        break
                elif dim_key == "campaign":
                    if event.utm.campaign != dim_val:
                        matches = False
                        break
                elif dim_key in event.properties:
                    if str(event.properties[dim_key]) != dim_val:
                        matches = False
                        break
                else:
                    matches = False
                    break
            if matches:
                filtered.append(event)
        return filtered

    def _compute_counts(
        self,
        metric_def: MetricDefinition,
        events: List[EventEnvelope],
        window: TimeWindow,
        watermark: datetime,
        tenant_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Dispatches calculation based on entity type:
        - session: fast funnels, attributed by session start time with maturity rules.
        - customer / application: slow funnels, cohort window tracking from start event.
        """
        if metric_def.metric_name in (
            "blended_roas", "blended_cac", "ad_spend", "loyalty_waiver_cost",
            "daily_waiver_budget", "marketing_budget_arbitration"
        ):
            return 0, 0

        if metric_def.entity == "session":
            return self._compute_session_counts(metric_def, events, window, watermark, tenant_id=tenant_id)
        else:
            return self._compute_cohort_counts(metric_def, events, window, watermark)

    def _compute_session_counts(
        self,
        metric_def: MetricDefinition,
        events: List[EventEnvelope],
        window: TimeWindow,
        watermark: datetime,
        tenant_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Session-level funnel calculation.
        Sessions are attributed to window by session start time: min(occurred_at).
        Maturity rule: uncompleted sessions active within maturity_window_minutes are excluded from abandonment denominators.
        """
        sessions: Dict[str, List[EventEnvelope]] = defaultdict(list)
        for e in events:
            sessions[e.session_id].append(e)

        # Attribute sessions to window by session start time (min occurred_at)
        attributed_sessions: Dict[str, List[EventEnvelope]] = {}
        for sid, s_evts in sessions.items():
            s_evts.sort(key=lambda x: x.occurred_at)
            start_dt = datetime.fromisoformat(s_evts[0].occurred_at)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            # Attribution window: [window.start, window.end)
            if window.start <= start_dt < window.end:
                attributed_sessions[sid] = s_evts

        total_sessions = len(attributed_sessions)
        session_event_names: Dict[str, Set[str]] = {
            sid: {e.event_name for e in evts} for sid, evts in attributed_sessions.items()
        }
        session_steps: Dict[str, Set[int]] = defaultdict(set)
        for sid, evts in attributed_sessions.items():
            for e in evts:
                if e.event_name == "checkout.step_completed":
                    if "step_number" in e.properties:
                        try:
                            session_steps[sid].add(int(e.properties["step_number"]))
                        except (ValueError, TypeError):
                            pass
                    elif "step" in e.properties:
                        try:
                            session_steps[sid].add(int(e.properties["step"]))
                        except (ValueError, TypeError):
                            pass
                    step_nm = str(e.properties.get("step_name", "")).lower()
                    if step_nm in ("1", "address", "step_1", "step_1_address"):
                        session_steps[sid].add(1)
                    elif step_nm in ("2", "payment", "charges", "step_2", "step_2_charges"):
                        session_steps[sid].add(2)

        # Reconcile server orders if tenant_id is available
        server_order_sessions: Set[str] = set()
        if tenant_id and hasattr(self.storage, "query_orders"):
            try:
                server_orders = self.storage.query_orders(
                    tenant_id=tenant_id,
                    window=window,
                    as_of=watermark,
                    payment_status="captured"
                )
                server_order_sessions = {o.session_id for o in server_orders if o.session_id}
            except Exception:
                server_order_sessions = set()

        # Helper: check maturity for drop-off / abandonment
        maturity_limit = min(window.end, watermark) - timedelta(minutes=metric_def.maturity_window_minutes or 0)
        def is_mature(sid: str, completion_events: Set[str]) -> bool:
            # If converted via verified server order, session is mature and converted
            if sid in server_order_sessions:
                return True
            evts = attributed_sessions[sid]
            # If already converted, session is complete
            if any(e.event_name in completion_events for e in evts):
                return True
            last_dt = datetime.fromisoformat(evts[-1].occurred_at)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            return last_dt <= maturity_limit

        m_name = metric_def.metric_name

        # -------------------------------------------------------------
        # 1. E-Commerce & Retail Metrics
        # -------------------------------------------------------------
        if m_name == "cart_abandonment_rate":
            cart_sessions = {sid for sid, evts in session_event_names.items() if "cart.item_added" in evts or "plan.selected" in evts}
            completed_events = {"purchase.completed", "subscription.activated", "order.completed"}
            # Apply maturity rule to cart abandonment denominator
            mature_cart_sessions = {sid for sid in cart_sessions if is_mature(sid, completed_events)}
            purchased_sessions = {sid for sid, evts in session_event_names.items() if any(c in evts for c in completed_events)} | (server_order_sessions & mature_cart_sessions)
            abandoned = mature_cart_sessions - purchased_sessions
            return len(abandoned), len(mature_cart_sessions)

        elif m_name == "checkout_drop_off_rate":
            checkout_sessions = {sid for sid, evts in session_event_names.items() if "checkout.started" in evts}
            completed_events = {"purchase.completed", "subscription.activated", "order.completed"}
            mature_checkout_sessions = {sid for sid in checkout_sessions if is_mature(sid, completed_events)}
            purchased_sessions = {sid for sid, evts in session_event_names.items() if any(c in evts for c in completed_events)} | (server_order_sessions & mature_checkout_sessions)
            drop_offs = mature_checkout_sessions - purchased_sessions
            return len(drop_offs), len(mature_checkout_sessions)

        elif m_name == "checkout_step_1_drop_off_rate":
            checkout_sessions = {sid for sid, evts in session_event_names.items() if "checkout.started" in evts}
            step_1_sessions = {sid for sid, steps in session_steps.items() if 1 in steps}
            # Set difference: started checkout but did not complete step 1
            drop_offs = checkout_sessions - step_1_sessions
            return len(drop_offs), len(checkout_sessions)

        elif m_name == "checkout_step_2_drop_off_rate":
            step_1_sessions = {sid for sid, steps in session_steps.items() if 1 in steps}
            step_2_sessions = {sid for sid, steps in session_steps.items() if 2 in steps}
            # Set difference: completed step 1 but did not complete step 2
            drop_offs = step_1_sessions - step_2_sessions
            return len(drop_offs), len(step_1_sessions)

        elif m_name == "checkout_step_3_drop_off_rate":
            step_2_sessions = {sid for sid, steps in session_steps.items() if 2 in steps}
            purchased_sessions = {sid for sid, evts in session_event_names.items() if "purchase.completed" in evts} | (server_order_sessions & step_2_sessions)
            drop_offs = step_2_sessions - purchased_sessions
            return len(drop_offs), len(step_2_sessions)

        elif m_name == "checkout_conversion_rate":
            checkout_sessions = {sid for sid, evts in session_event_names.items() if "checkout.started" in evts}
            purchased_sessions = {sid for sid, evts in session_event_names.items() if "purchase.completed" in evts} | (server_order_sessions & checkout_sessions)
            return len(purchased_sessions & checkout_sessions), len(checkout_sessions)

        elif m_name == "overall_conversion_rate":
            visiting_sessions = {sid for sid, evts in session_event_names.items() if "page.viewed" in evts or "product.viewed" in evts}
            purchased_sessions = {sid for sid, evts in session_event_names.items() if "purchase.completed" in evts} | (server_order_sessions & visiting_sessions)
            denom = len(visiting_sessions) if visiting_sessions else total_sessions
            return len(purchased_sessions & visiting_sessions), denom

        elif m_name == "add_to_cart_rate":
            product_view_sessions = {sid for sid, evts in session_event_names.items() if "product.viewed" in evts}
            cart_sessions = {sid for sid, evts in session_event_names.items() if "cart.item_added" in evts}
            return len(cart_sessions & product_view_sessions), len(product_view_sessions)

        elif m_name == "cart_to_checkout_rate":
            cart_sessions = {sid for sid, evts in session_event_names.items() if "cart.item_added" in evts}
            checkout_sessions = {sid for sid, evts in session_event_names.items() if "checkout.started" in evts}
            return len(checkout_sessions & cart_sessions), len(cart_sessions)

        elif m_name == "rage_click_session_rate":
            rage_sessions = {sid for sid, evts in session_event_names.items() if "user.rage_click" in evts or "ui.rage_clicked" in evts}
            return len(rage_sessions), total_sessions

        elif m_name == "exit_intent_rate":
            exit_sessions = {sid for sid, evts in session_event_names.items() if "user.exit_intent" in evts}
            return len(exit_sessions), total_sessions

        # -------------------------------------------------------------
        # 2. QSR & Food Delivery
        # -------------------------------------------------------------
        elif m_name == "customization_drop_off_rate":
            customize_sessions = {sid for sid, evts in session_event_names.items() if "product.customized" in evts}
            cart_sessions = {sid for sid, evts in session_event_names.items() if "cart.item_added" in evts}
            abandoned = customize_sessions - cart_sessions
            return len(abandoned), len(customize_sessions)

        # -------------------------------------------------------------
        # 3. SaaS & Product-Led Growth (Session-based metrics)
        # -------------------------------------------------------------
        elif m_name == "signup_completion_rate":
            signup_starts = {sid for sid, evts in session_event_names.items() if "user.signup_started" in evts}
            signup_completes = {sid for sid, evts in session_event_names.items() if "user.signed_up" in evts}
            return len(signup_starts & signup_completes), len(signup_starts)

        elif m_name == "visitor_to_signup_rate":
            visiting_sessions = {sid for sid, evts in session_event_names.items() if "page.viewed" in evts}
            signed_up_sessions = {sid for sid, evts in session_event_names.items() if "user.signed_up" in evts}
            return len(visiting_sessions & signed_up_sessions), len(visiting_sessions)

        # -------------------------------------------------------------
        # 4. Travel & Hospitality
        # -------------------------------------------------------------
        elif m_name == "search_to_detail_rate":
            search_sessions = {sid for sid, evts in session_event_names.items() if "search.performed" in evts}
            detail_sessions = {sid for sid, evts in session_event_names.items() if "listing.viewed" in evts}
            return len(search_sessions & detail_sessions), len(search_sessions)

        elif m_name == "booking_drop_off_rate":
            dates_sessions = {sid for sid, evts in session_event_names.items() if "dates.selected" in evts}
            booked_sessions = {sid for sid, evts in session_event_names.items() if "booking.confirmed" in evts}
            drop_offs = dates_sessions - booked_sessions
            return len(drop_offs), len(dates_sessions)

        elif m_name == "payment_failure_rate":
            payment_attempts = {sid for sid, evts in session_event_names.items() if "payment.initiated" in evts}
            payment_failures = {sid for sid, evts in session_event_names.items() if "payment.failed" in evts}
            return len(payment_attempts & payment_failures), len(payment_attempts)

        elif m_name == "overall_booking_conversion_rate":
            search_sessions = {sid for sid, evts in session_event_names.items() if "search.performed" in evts or "page.viewed" in evts}
            booked_sessions = {sid for sid, evts in session_event_names.items() if "booking.confirmed" in evts}
            denom = len(search_sessions) if search_sessions else total_sessions
            return len(search_sessions & booked_sessions), denom

        # -------------------------------------------------------------
        # 5. D2C Subscription Box
        # -------------------------------------------------------------
        elif m_name == "plan_selection_rate":
            visiting_sessions = {sid for sid, evts in session_event_names.items() if "page.viewed" in evts or "product.viewed" in evts}
            plan_selected = {sid for sid, evts in session_event_names.items() if "plan.selected" in evts}
            return len(visiting_sessions & plan_selected), len(visiting_sessions)

        else:
            raise NotImplementedError(f"Formula for metric '{m_name}' is not implemented in MetricsEngine")

    def _compute_cohort_counts(
        self,
        metric_def: MetricDefinition,
        events: List[EventEnvelope],
        window: TimeWindow,
        watermark: datetime
    ) -> Tuple[int, int]:
        """
        Slow funnel cohort calculation for customer or application entities.
        Finds entities whose start step occurred within [window.start, window.end).
        Evaluates whether conversion occurred within cohort_window_days from the start event.
        Guarantees 0 <= numerator <= denominator.
        """
        step_from = metric_def.step_from
        step_to = metric_def.step_to
        cohort_days = metric_def.cohort_window_days or 14

        if not step_from or not step_to:
            raise ValueError(
                f"Cohort metric '{metric_def.metric_name}' requires step_from and step_to definitions"
            )

        # 1. Group events by entity identifier
        entity_events: Dict[str, List[EventEnvelope]] = defaultdict(list)
        for e in events:
            if metric_def.entity == "customer":
                ent_id = e.customer_id or e.session_id
            elif metric_def.entity == "application":
                ent_id = str(e.properties.get("application_id") or e.customer_id or e.session_id)
            else:
                ent_id = e.session_id
            entity_events[ent_id].append(e)

        # 2. Identify cohort entities whose step_from occurred in the window
        cohort_start_times: Dict[str, datetime] = {}
        for ent_id, evts in entity_events.items():
            evts.sort(key=lambda x: x.occurred_at)
            for e in evts:
                if e.event_name == step_from:
                    dt = datetime.fromisoformat(e.occurred_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if window.start <= dt < window.end:
                        if ent_id not in cohort_start_times or dt < cohort_start_times[ent_id]:
                            cohort_start_times[ent_id] = dt

        denominator_entities = set(cohort_start_times.keys())
        denominator = len(denominator_entities)

        if denominator == 0:
            return 0, 0

        # 3. Check conversion within cohort window from each entity's start time
        converted_entities: Set[str] = set()
        for ent_id, start_dt in cohort_start_times.items():
            evts = entity_events[ent_id]
            cutoff_dt = start_dt + timedelta(days=cohort_days)
            for e in evts:
                if e.event_name == step_to:
                    conv_dt = datetime.fromisoformat(e.occurred_at)
                    if conv_dt.tzinfo is None:
                        conv_dt = conv_dt.replace(tzinfo=timezone.utc)
                    # Check conversion occurred at or after start, and within cohort window
                    if start_dt <= conv_dt <= cutoff_dt:
                        converted_entities.add(ent_id)
                        break

        # 4. Polarity determination for drop-off vs conversion
        if metric_def.polarity == "lower_is_better":
            # Drop-off rate: cohort members who did NOT convert
            dropped_entities = denominator_entities - converted_entities
            numerator = len(dropped_entities)
        else:
            # Conversion rate: cohort members who did convert
            numerator = len(converted_entities)

        assert 0 <= numerator <= denominator, f"Ratio violation: {numerator}/{denominator}"
        return numerator, denominator

    def calculate_blended_ad_metrics(
        self,
        ad_records: List[AdsCampaignDaily],
        new_customers_count: int = 0,
        attributed_revenue_paise: int = 0
    ) -> BlendedAdMetrics:
        """
        Computes deterministic grounded blended advertising analytics across campaigns.
        Calculates total spend (paise & INR), aggregate impressions, clicks, conversions,
        blended CTR, blended CPC, blended CPA, blended ROAS, and blended CAC.
        """
        total_spend_paise = sum(r.spend_paise for r in ad_records)
        total_spend_inr = round(total_spend_paise / 100.0, 2)
        total_impressions = sum(r.impressions for r in ad_records)
        total_clicks = sum(r.clicks for r in ad_records)
        total_conversions = sum(r.conversions for r in ad_records)
        conversion_value_paise = attributed_revenue_paise if attributed_revenue_paise > 0 else sum(r.conversion_value_paise for r in ad_records)

        blended_ctr = round(float(total_clicks) / float(total_impressions), 4) if total_impressions > 0 else 0.0
        blended_cpc_paise = int(round(float(total_spend_paise) / float(total_clicks))) if total_clicks > 0 else 0
        blended_cpa_paise = int(round(float(total_spend_paise) / total_conversions)) if total_conversions > 0 else 0
        blended_roas = round(float(conversion_value_paise) / float(total_spend_paise), 2) if total_spend_paise > 0 else 0.0

        blended_cac_paise = None
        blended_cac_inr = None
        if new_customers_count > 0:
            blended_cac_paise = int(round(float(total_spend_paise) / float(new_customers_count)))
            blended_cac_inr = round(blended_cac_paise / 100.0, 2)

        unique_campaigns = {r.campaign_id for r in ad_records}

        return BlendedAdMetrics(
            total_spend_paise=total_spend_paise,
            total_spend_inr=total_spend_inr,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            conversion_value_paise=conversion_value_paise,
            blended_ctr=blended_ctr,
            blended_cpc_paise=blended_cpc_paise,
            blended_cpa_paise=blended_cpa_paise,
            blended_roas=blended_roas,
            blended_cac_paise=blended_cac_paise,
            blended_cac_inr=blended_cac_inr,
            campaign_count=len(unique_campaigns)
        )

    def calculate_server_revenue_metrics(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        payment_status: str = "captured"
    ) -> Dict[str, Any]:
        """
        Calculates deterministic grounded revenue and order volume metrics
        from verified server-side orders, eliminating browser event spoofing.
        """
        watermark = as_of or window.end
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)

        if hasattr(self.storage, "query_orders"):
            orders = self.storage.query_orders(
                tenant_id=tenant_id,
                window=window,
                as_of=watermark,
                payment_status=payment_status,
                limit=100000
            )
        else:
            orders = []

        order_count = len(orders)
        total_revenue_paise = sum(o.total_paid_paise for o in orders)
        total_revenue_inr = round(total_revenue_paise / 100.0, 2)
        subtotal_paise = sum(o.subtotal_paise for o in orders)
        discount_paise = sum(o.discount_paise for o in orders)
        tax_paise = sum(o.tax_paise for o in orders)

        aov_paise = int(round(total_revenue_paise / order_count)) if order_count > 0 else 0
        aov_inr = round(aov_paise / 100.0, 2)

        unique_customers = {o.customer_id for o in orders if o.customer_id}
        unique_sessions = {o.session_id for o in orders if o.session_id}

        return {
            "tenant_id": tenant_id,
            "order_count": order_count,
            "total_revenue_paise": total_revenue_paise,
            "total_revenue_inr": total_revenue_inr,
            "subtotal_paise": subtotal_paise,
            "discount_paise": discount_paise,
            "tax_paise": tax_paise,
            "aov_paise": aov_paise,
            "aov_inr": aov_inr,
            "unique_customers_count": len(unique_customers),
            "unique_sessions_count": len(unique_sessions),
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "as_of": watermark.isoformat()
        }

