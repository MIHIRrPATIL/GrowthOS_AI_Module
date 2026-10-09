"""
24-Hour Attribution Closing Worker Service
GrowthOS Module 4: AI Growth Brain

Closes out the 24-hour attribution window for executed interventions and holdouts:
1. Queries ActionPlans in 'dispatched' or 'holdout' state with elapsed attribution windows.
2. Cross-references event storage for subsequent 'order_completed' / 'purchase' events within 24h.
3. Classifies outcome:
   - CONVERTED: Intervened customer completed order within 24h.
   - HOLDOUT_CONVERTED: Un-messaged holdout control customer completed order within 24h (organic conversion baseline).
   - EXPIRED: No order completed within 24h.
4. Computes true incremental conversion lift:
   Lift = (Treated Conversion Rate) - (Holdout Control Conversion Rate)
5. Appends immutable audit records for closing decisions.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, ConfigDict

from ports.action_storage import ActionStoragePort
from ports.storage import EventStoragePort
from ports.outbound import AuditLedgerPort
from domain.actions import ActionPlan, AuditRecord
from domain.metrics import TimeWindow


class AttributionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    closing_timestamp: str
    evaluated_plans_count: int
    treated_converted_count: int
    treated_expired_count: int
    holdout_converted_count: int
    holdout_expired_count: int
    treated_conversion_rate: float
    holdout_conversion_rate: float
    incremental_lift_pct: float
    closed_plan_ids: List[str] = Field(default_factory=list)


class AttributionClosingWorker:
    """
    Background worker for closing 24h attribution windows and measuring incremental lift against holdout groups.
    """

    def __init__(
        self,
        action_storage: ActionStoragePort,
        event_storage: EventStoragePort,
        audit_ledger: AuditLedgerPort,
        attribution_window_hours: float = 24.0
    ):
        self.action_storage = action_storage
        self.event_storage = event_storage
        self.audit_ledger = audit_ledger
        self.window_hours = attribution_window_hours

    def close_attribution(
        self,
        tenant_id: str,
        as_of: Optional[datetime] = None
    ) -> AttributionReport:
        """
        Closes attribution windows for all eligible dispatched and holdout plans for the tenant.
        """
        now = as_of or datetime.now(timezone.utc)
        cutoff_dt = now - timedelta(hours=self.window_hours)

        # Retrieve candidate plans
        all_dispatched = self.action_storage.list_plans(tenant_id=tenant_id, status="dispatched", limit=500)
        all_holdouts = self.action_storage.list_plans(tenant_id=tenant_id, status="holdout", limit=500)

        treated_conv = 0
        treated_exp = 0
        holdout_conv = 0
        holdout_exp = 0
        closed_ids: List[str] = []

        # Process Dispatched (Treated) Plans
        for plan in all_dispatched:
            dispatch_time_str = plan.dispatched_at or plan.created_at
            dispatch_time = datetime.fromisoformat(dispatch_time_str)
            if dispatch_time.tzinfo is None:
                dispatch_time = dispatch_time.replace(tzinfo=timezone.utc)

            # Check if 24 hours have elapsed since dispatch
            if dispatch_time > cutoff_dt:
                continue  # Attribution window still active

            window_end = dispatch_time + timedelta(hours=self.window_hours)
            converted = self._check_customer_order(tenant_id, plan.customer_id, dispatch_time, window_end)

            new_status = "converted" if converted else "expired"
            plan.status = new_status
            self.action_storage.save_plan(plan)
            closed_ids.append(plan.plan_id)

            if converted:
                treated_conv += 1
            else:
                treated_exp += 1

            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=tenant_id,
                    plan_id=plan.plan_id,
                    actor="attribution_worker",
                    event_type="attribution_closed",
                    details={
                        "outcome": new_status,
                        "dispatched_at": dispatch_time.isoformat(),
                        "window_end": window_end.isoformat(),
                        "is_holdout": False
                    }
                )
            )

        # Process Holdout (Control) Plans
        for plan in all_holdouts:
            created_time = datetime.fromisoformat(plan.created_at)
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=timezone.utc)

            if created_time > cutoff_dt:
                continue

            window_end = created_time + timedelta(hours=self.window_hours)
            converted = self._check_customer_order(tenant_id, plan.customer_id, created_time, window_end)

            new_status = "holdout_converted" if converted else "holdout_expired"
            plan.status = new_status
            self.action_storage.save_plan(plan)
            closed_ids.append(plan.plan_id)

            if converted:
                holdout_conv += 1
            else:
                holdout_exp += 1

            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=tenant_id,
                    plan_id=plan.plan_id,
                    actor="attribution_worker",
                    event_type="attribution_closed",
                    details={
                        "outcome": new_status,
                        "created_at": created_time.isoformat(),
                        "window_end": window_end.isoformat(),
                        "is_holdout": True
                    }
                )
            )

        # Compute Lift Metrics
        total_treated = treated_conv + treated_exp
        total_holdout = holdout_conv + holdout_exp

        treated_rate = (treated_conv / total_treated) if total_treated > 0 else 0.0
        holdout_rate = (holdout_conv / total_holdout) if total_holdout > 0 else 0.0
        incremental_lift = (treated_rate - holdout_rate) * 100.0

        return AttributionReport(
            tenant_id=tenant_id,
            closing_timestamp=now.isoformat(),
            evaluated_plans_count=len(closed_ids),
            treated_converted_count=treated_conv,
            treated_expired_count=treated_exp,
            holdout_converted_count=holdout_conv,
            holdout_expired_count=holdout_exp,
            treated_conversion_rate=round(treated_rate, 4),
            holdout_conversion_rate=round(holdout_rate, 4),
            incremental_lift_pct=round(incremental_lift, 2),
            closed_plan_ids=closed_ids
        )

    def _check_customer_order(
        self,
        tenant_id: str,
        customer_id: Optional[str],
        window_start: datetime,
        window_end: datetime
    ) -> bool:
        if not customer_id:
            return False

        order_events = self.event_storage.query_events(
            tenant_id=tenant_id,
            window=TimeWindow(start=window_start, end=window_end),
            event_names=["order_completed", "purchase"],
            customer_id=customer_id
        )
        return len(order_events) > 0
