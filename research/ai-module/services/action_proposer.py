"""
Action Proposer Service
Translates digest flags and anomaly signals into structured, versioned ActionPlan proposals.
Ensures deterministic plan generation, holdout cohort suppression, and write-ahead audit tracking.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone, timedelta

from domain.actions import ActionPlan, AuditRecord
from domain.metrics import DigestReport, DigestFlag
from ports.decision import DecisionPort, DecisionContext, DecisionCandidate
from ports.action_storage import ActionStoragePort
from ports.outbound import AuditLedgerPort


class ActionProposer:
    """
    Action proposal coordinator.
    Ingests signals from DigestReport or Anomaly detection, generates action candidates
    via DecisionPort, deduplicates against active plans, and persists drafted plans.
    """

    def __init__(
        self,
        decision_provider: DecisionPort,
        action_storage: ActionStoragePort,
        audit_ledger: AuditLedgerPort,
        clock: Optional[Callable[[], datetime]] = None
    ):
        self.decision_provider = decision_provider
        self.action_storage = action_storage
        self.audit_ledger = audit_ledger
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def propose_actions_from_digest(
        self,
        digest_report: DigestReport,
        tenant_config: Optional[Dict[str, Any]] = None
    ) -> List[ActionPlan]:
        """
        Processes all flags and anomalies in a DigestReport and generates drafted ActionPlans.
        """
        tenant_id = digest_report.tenant_id
        config = tenant_config or {}
        now = self.clock()
        created_plans: List[ActionPlan] = []

        # 1. Process Digest Flags
        for flag in digest_report.flags:
            context = DecisionContext(
                tenant_id=tenant_id,
                signal_type="digest_flag",
                signal_payload=flag.model_dump(),
                signal_dedupe_key=flag.dedupe_key,
                as_of=now,
                tenant_config=config
            )
            candidates = self.decision_provider.propose_candidates(context)
            plans = self._materialize_candidates(candidates, context, now)
            created_plans.extend(plans)

        # 2. Process Idle Cart Anomalies
        for anomaly in digest_report.anomalies:
            dedupe_key = getattr(anomaly, "dedupe_key", None)
            if not dedupe_key:
                sess_id = getattr(anomaly, "session_id", "unknown")
                cust_id = getattr(anomaly, "customer_id", "unknown")
                dedupe_key = f"idle_cart_{sess_id}_{cust_id}"

            payload = anomaly.model_dump() if hasattr(anomaly, "model_dump") else dict(anomaly)
            context = DecisionContext(
                tenant_id=tenant_id,
                signal_type="idle_cart",
                signal_payload=payload,
                signal_dedupe_key=dedupe_key,
                as_of=now,
                tenant_config=config
            )
            candidates = self.decision_provider.propose_candidates(context)
            plans = self._materialize_candidates(candidates, context, now)
            created_plans.extend(plans)

        return created_plans

    def propose_action_from_signal(
        self,
        tenant_id: str,
        signal_type: str,
        signal_payload: Dict[str, Any],
        signal_dedupe_key: str,
        tenant_config: Optional[Dict[str, Any]] = None
    ) -> List[ActionPlan]:
        """
        Proposes actions for a standalone signal.
        """
        now = self.clock()
        config = tenant_config or {}
        context = DecisionContext(
            tenant_id=tenant_id,
            signal_type=signal_type,  # type: ignore
            signal_payload=signal_payload,
            signal_dedupe_key=signal_dedupe_key,
            as_of=now,
            tenant_config=config
        )
        candidates = self.decision_provider.propose_candidates(context)
        return self._materialize_candidates(candidates, context, now)

    def _materialize_candidates(
        self,
        candidates: List[DecisionCandidate],
        context: DecisionContext,
        now: datetime
    ) -> List[ActionPlan]:
        plans: List[ActionPlan] = []

        for c in candidates:
            # 1. Check holdout cohort suppression
            if c.is_holdout:
                self.audit_ledger.record_audit(
                    AuditRecord(
                        tenant_id=context.tenant_id,
                        plan_id="HOLD_OUT_CONTROL",
                        actor="ai_growth_brain",
                        event_type="candidate_holdout_suppressed",
                        details={
                            "action_type": c.action_type.value,
                            "target_id": c.target_id,
                            "reason": "customer_allocated_to_causal_control_holdout"
                        }
                    )
                )
                continue

            # 2. Derive deterministic plan ID to prevent rerun duplicates
            plan_id = ActionPlan.generate_plan_id(
                tenant_id=context.tenant_id,
                signal_dedupe_key=context.signal_dedupe_key,
                action_type=c.action_type.value,
                target_id=c.target_id
            )

            # 3. Check for existing active plan
            existing = self.action_storage.get_plan(context.tenant_id, plan_id)
            if existing and existing.status in ("drafted", "pending_approval", "approved", "dispatching", "dispatched"):
                # Active plan already exists; skip recreation
                continue

            # 4. Construct ActionPlan
            plan = ActionPlan(
                plan_id=plan_id,
                tenant_id=context.tenant_id,
                signal_dedupe_key=context.signal_dedupe_key,
                customer_id=c.customer_id,
                anonymous_id=c.anonymous_id,
                action_type=c.action_type,
                target_module=c.target_module,
                parameters=c.parameters.model_dump(),
                reasoning_summary=c.reasoning_summary,
                evidence_citations=c.evidence_citations,
                priority_score=c.priority_score,
                calibrated_probability=c.calibrated_probability,
                confidence_score=c.priority_score,
                status="drafted",
                version=1,
                is_holdout=False,
                created_at=now.isoformat(),
                expires_at=(now + timedelta(hours=24)).isoformat()
            )

            # 5. Persist plan
            self.action_storage.save_plan(plan)

            # 6. Record write-ahead audit entry
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=context.tenant_id,
                    plan_id=plan.plan_id,
                    actor="ai_growth_brain",
                    event_type="plan_drafted",
                    details={
                        "action_type": plan.action_type.value,
                        "target_module": plan.target_module,
                        "target_id": c.target_id,
                        "priority_score": plan.priority_score,
                        "expires_at": plan.expires_at
                    }
                )
            )

            plans.append(plan)

        return plans
