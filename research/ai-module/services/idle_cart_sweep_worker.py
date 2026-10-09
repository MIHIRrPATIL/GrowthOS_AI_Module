"""
Idle Cart Sweep Worker Service (Background Scheduler)
GrowthOS Module 4: AI Growth Brain

Periodically sweeps active sessions to identify abandoned shopping carts:
1. Filters unpurchased carts idle >= 15 minutes.
2. Resolves canonical customer identity (enforces Invariant 14: no outreach to unauthenticated guests).
3. Computes heuristic purchase propensity:
   - Suppresses organic high-intent buyers (>= 0.85) to prevent margin cannibalization.
   - Suppresses low-intent window shoppers (<= 0.15) to preserve notification budget.
4. For eligible sessions (0.15 < propensity < 0.85):
   - Constructs ActionPlan (WAIVE_DELIVERY_FEE or SEND_RECOVERY_WHATSAPP).
   - Routes through ActionOrchestrator to enforce:
     * PolicyEngine boundaries
     * ConsentPort DPDP compliance
     * 10% randomized holdout control allocation
     * Outbound claim idempotency
     * Write-ahead immutable audit ledger logging

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, ConfigDict
import uuid

from ports.storage import EventStoragePort
from ports.identity import IdentityResolutionPort
from services.action_orchestrator import ActionOrchestrator
from domain.actions import ActionPlan, ActionType, ExecutionMode
from engines.heuristic_scoring import (
    score_purchase_propensity,
    score_customer_cltv,
    HeuristicWeightsConfig,
    DEFAULT_HEURISTIC_CONFIG
)


class SweepReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    sweep_timestamp: str
    scanned_sessions_count: int
    eligible_sessions_count: int
    suppressed_anonymous_count: int
    suppressed_organic_count: int
    suppressed_low_intent_count: int
    dispatched_plans_count: int
    holdout_plans_count: int
    rejected_plans_count: int
    pending_approval_count: int
    processed_plan_ids: List[str] = Field(default_factory=list)


class IdleCartSweepWorker:
    """
    Background worker for sweeping idle abandoned carts and executing governance-gated interventions.
    """

    def __init__(
        self,
        event_storage: EventStoragePort,
        identity_resolver: IdentityResolutionPort,
        orchestrator: ActionOrchestrator,
        heuristic_config: Optional[HeuristicWeightsConfig] = None
    ):
        self.event_storage = event_storage
        self.identity_resolver = identity_resolver
        self.orchestrator = orchestrator
        self.config = heuristic_config or DEFAULT_HEURISTIC_CONFIG

    def sweep_tenant(
        self,
        tenant_id: str,
        as_of: Optional[datetime] = None,
        idle_threshold_minutes: float = 15.0,
        default_aov_paise: int = 50000,
        high_value_threshold_paise: int = 50000
    ) -> SweepReport:
        """
        Executes a single sweep over all idle sessions for a tenant.
        """
        now = as_of or datetime.now(timezone.utc)
        idle_sessions = self.event_storage.query_idle_sessions(
            tenant_id=tenant_id,
            as_of=now,
            idle_threshold_minutes=idle_threshold_minutes
        )

        scanned_count = len(idle_sessions)
        eligible_count = 0
        suppressed_anon = 0
        suppressed_organic = 0
        suppressed_low = 0
        dispatched_count = 0
        holdout_count = 0
        rejected_count = 0
        pending_approval = 0
        processed_ids: List[str] = []

        for s in idle_sessions:
            session_id = s["session_id"]
            cust_id = s.get("customer_id")
            anon_id = s.get("anonymous_id")

            # 1. Identity Resolution & Invariant 14 Check
            canonical_cust = None
            if cust_id:
                canonical_cust = self.identity_resolver.get_canonical_customer_id(tenant_id, cust_id) or cust_id
            elif anon_id:
                canonical_cust = self.identity_resolver.get_canonical_customer_id(tenant_id, anon_id)

            if not canonical_cust:
                suppressed_anon += 1
                continue

            # Calculate idle minutes
            last_event_at = s["last_event_at"]
            if last_event_at.tzinfo is None:
                last_event_at = last_event_at.replace(tzinfo=timezone.utc)
            idle_mins = max(0.0, (now - last_event_at).total_seconds() / 60.0)

            cart_paise = s.get("cart_subtotal_paise", 0)
            views = s.get("product_views_count", 0)
            adds = s.get("cart_adds_count", 0)
            stage = s.get("funnel_stage", "cart")

            # 2. Heuristic Purchase Propensity Scoring
            prop_res = score_purchase_propensity(
                cart_subtotal_paise=cart_paise,
                tenant_aov_paise=default_aov_paise,
                product_views_count=views,
                cart_adds_count=adds,
                funnel_stage=stage,
                idle_minutes=idle_mins,
                config=self.config
            )

            if prop_res.eligibility == "SUPPRESS_ORGANIC_BUYER":
                suppressed_organic += 1
                continue
            elif prop_res.eligibility == "SUPPRESS_LOW_INTENT":
                suppressed_low += 1
                continue

            # 3. Eligible for Incentive Intervention
            eligible_count += 1

            # Decide Action Type & Target Module
            if cart_paise >= high_value_threshold_paise:
                action_type = ActionType.WAIVE_DELIVERY_FEE
                target_module = "module_1_loyalty"
                params = {
                    "fee_amount_paise": 5000,
                    "fee_amount": 50.0,
                    "points_deducted": 0,
                    "customer_id": canonical_cust
                }
                reason = (
                    f"Idle cart of INR {cart_paise / 100:.2f} for {idle_mins:.1f}m. "
                    f"Propensity: {prop_res.score:.2f} in eligible band. Proposing delivery fee waiver."
                )
            else:
                action_type = ActionType.SEND_RECOVERY_WHATSAPP
                target_module = "notification"
                params = {
                    "customer_id": canonical_cust,
                    "cart_url": f"https://store.growthos.io/checkout?session={session_id}",
                    "discount_pct": 0.0
                }
                reason = (
                    f"Idle cart of INR {cart_paise / 100:.2f} for {idle_mins:.1f}m. "
                    f"Propensity: {prop_res.score:.2f}. Proposing cart recovery reminder."
                )

            dedupe_key = f"sweep:{tenant_id}:{session_id}:{action_type.value}"

            plan = ActionPlan(
                plan_id=f"plan_{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                action_type=action_type,
                target_module=target_module,
                customer_id=canonical_cust,
                anonymous_id=anon_id,
                parameters=params,
                reasoning_summary=reason,
                evidence_citations=[
                    f"cart_paise={cart_paise}",
                    f"idle_mins={idle_mins:.1f}",
                    f"propensity_score={prop_res.score}"
                ],
                priority_score=prop_res.score,
                calibrated_probability=prop_res.score,
                signal_dedupe_key=dedupe_key,
                execution_mode=ExecutionMode.AUTONOMOUS
            )

            # 4. Route through Governance & Orchestration Layer
            routed_plan = self.orchestrator.evaluate_and_route_plan(plan)
            processed_ids.append(routed_plan.plan_id)

            if routed_plan.status == "dispatched":
                dispatched_count += 1
            elif routed_plan.status == "holdout":
                holdout_count += 1
            elif routed_plan.status == "pending_approval":
                pending_approval += 1
            elif routed_plan.status == "rejected":
                rejected_count += 1

        return SweepReport(
            tenant_id=tenant_id,
            sweep_timestamp=now.isoformat(),
            scanned_sessions_count=scanned_count,
            eligible_sessions_count=eligible_count,
            suppressed_anonymous_count=suppressed_anon,
            suppressed_organic_count=suppressed_organic,
            suppressed_low_intent_count=suppressed_low,
            dispatched_plans_count=dispatched_count,
            holdout_plans_count=holdout_count,
            rejected_plans_count=rejected_count,
            pending_approval_count=pending_approval,
            processed_plan_ids=processed_ids
        )
