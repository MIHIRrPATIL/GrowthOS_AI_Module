"""
Action Orchestrator Service
Enforces execution mode gating (MANUAL, APPROVAL, AUTONOMOUS), pre-dispatch policy re-verification,
freshness checks, write-ahead audit logging, and idempotency claims prior to dispatching actions.
"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
import json

from domain.actions import (
    ActionPlan,
    ActionType,
    ExecutionMode,
    PolicyRule,
    AuditRecord
)
from engines.policy_engine import PolicyEngine
from ports.action_storage import ActionStoragePort
from ports.consent import ConsentPort
from ports.outbound import (
    AuditLedgerPort,
    LoyaltyPort,
    BehaviorPort,
    AdsPort,
    NotificationPort
)


class ActionOrchestrator:
    """
    Central orchestration service for evaluating policies, routing plans by execution mode,
    and reliably executing dispatches with idempotency barriers and write-ahead audit records.
    """

    def __init__(
        self,
        action_storage: ActionStoragePort,
        policy_engine: PolicyEngine,
        consent_port: ConsentPort,
        audit_ledger: AuditLedgerPort,
        loyalty_adapter: LoyaltyPort,
        behavior_adapter: BehaviorPort,
        ads_adapter: AdsPort,
        notification_adapter: NotificationPort,
        freshness_verifier: Optional[Callable[[ActionPlan], bool]] = None,
        clock: Optional[Callable[[], datetime]] = None
    ):
        self.action_storage = action_storage
        self.policy_engine = policy_engine
        self.consent_port = consent_port
        self.audit_ledger = audit_ledger
        self.loyalty_adapter = loyalty_adapter
        self.behavior_adapter = behavior_adapter
        self.ads_adapter = ads_adapter
        self.notification_adapter = notification_adapter
        self.freshness_verifier = freshness_verifier or (lambda plan: True)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate_and_route_plan(
        self,
        plan: ActionPlan,
        target_mode: Optional[ExecutionMode] = None
    ) -> ActionPlan:
        """
        Evaluates an ActionPlan against current tenant policy rules and routes it
        according to the execution mode (Manual, Approval, Autonomous).
        """
        now = self.clock()

        # 1. Fetch active tenant policy rule (Do not trust caller's rule)
        rule = self.action_storage.get_policy_rule(plan.tenant_id)
        if not rule:
            rule = PolicyRule(tenant_id=plan.tenant_id)
            self.action_storage.save_policy_rule(rule)

        # 2. Evaluate hard boundaries via PolicyEngine (Confidence is decoupled)
        eval_result = self.policy_engine.evaluate(plan, rule, as_of=now)
        plan.policy_check_passed = eval_result.passed
        plan.policy_violations = eval_result.violations
        plan.rule_version = eval_result.rule_version

        # Record policy evaluation audit entry
        self.audit_ledger.record_audit(
            AuditRecord(
                tenant_id=plan.tenant_id,
                plan_id=plan.plan_id,
                actor="policy_engine",
                event_type="policy_evaluated",
                details={
                    "passed": eval_result.passed,
                    "violations": eval_result.violations,
                    "rule_version": eval_result.rule_version,
                    "evaluated_limits": eval_result.evaluated_limits
                }
            )
        )

        # If policy check failed, reject immediately
        if not eval_result.passed:
            plan.status = "rejected"
            self.action_storage.save_plan(plan)
            # Record explicit plan_rejected event to complete lifecycle
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor="policy_gate",
                    event_type="plan_rejected",
                    details={
                        "reason": "policy_violations",
                        "violations": eval_result.violations
                    }
                )
            )
            return plan

        # 3. Mode Gate Evaluation
        mode = target_mode or plan.execution_mode

        if mode == ExecutionMode.MANUAL:
            plan.execution_mode = ExecutionMode.MANUAL
            plan.status = "drafted"
            self.action_storage.save_plan(plan)
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor="mode_gate",
                    event_type="manual_recommendation_ready",
                    details={"action_type": plan.action_type.value}
                )
            )
            return plan

        elif mode == ExecutionMode.AUTONOMOUS:
            # Check Autonomy Guardrails (Review points 1 & 8)
            demotion_reason = None

            if rule.emergency_kill_switch_active:
                demotion_reason = "emergency_kill_switch_active"
            elif plan.action_type.value not in rule.autonomous_action_allowlist:
                demotion_reason = "action_type_not_on_autonomous_allowlist"
            elif plan.calibrated_probability is None or plan.calibrated_probability < rule.autonomous_confidence_threshold:
                demotion_reason = "calibrated_probability_below_threshold"

            if demotion_reason:
                # Downgrade to APPROVAL mode
                plan.execution_mode = ExecutionMode.APPROVAL
                plan.status = "pending_approval"
                self.action_storage.save_plan(plan)
                self.audit_ledger.record_audit(
                    AuditRecord(
                        tenant_id=plan.tenant_id,
                        plan_id=plan.plan_id,
                        actor="mode_gate",
                        event_type="autonomy_demoted_to_approval",
                        details={
                            "demotion_reason": demotion_reason,
                            "calibrated_probability": plan.calibrated_probability,
                            "threshold": rule.autonomous_confidence_threshold,
                            "allowlist": rule.autonomous_action_allowlist
                        }
                    )
                )
                return plan
            else:
                # All autonomy checks passed: proceed to autonomous execution
                plan.execution_mode = ExecutionMode.AUTONOMOUS
                plan.status = "approved"
                plan.approved_by = "autonomous_growth_engine"
                plan.approved_at = now.isoformat()
                self.action_storage.save_plan(plan)
                return self.execute_dispatch(plan, actor="autonomous_growth_engine")

        else:
            # Default: APPROVAL mode
            plan.execution_mode = ExecutionMode.APPROVAL
            plan.status = "pending_approval"
            self.action_storage.save_plan(plan)
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor="mode_gate",
                    event_type="awaiting_human_approval",
                    details={"action_type": plan.action_type.value, "priority_score": plan.priority_score}
                )
            )
            return plan

    def execute_dispatch(self, plan: ActionPlan, actor: str) -> ActionPlan:
        """
        Executes outbound dispatch with write-ahead audit, pre-dispatch freshness,
        local claim reservation, and adapter invocation.
        """
        now = self.clock()

        # 1. Re-check Plan Expiration (Review point 9)
        expires_at = datetime.fromisoformat(plan.expires_at)
        if expires_at <= now:
            plan.status = "expired"
            self.action_storage.save_plan(plan)
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor="orchestrator",
                    event_type="plan_expired",
                    details={"expired_at": plan.expires_at, "attempted_at": now.isoformat()}
                )
            )
            return plan

        # 2. Freshness Check (e.g. customer placed order in interim, cart removed)
        if not self.freshness_verifier(plan):
            plan.status = "expired"
            self.action_storage.save_plan(plan)
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor="orchestrator",
                    event_type="plan_invalidated_freshness_failed",
                    details={"reason": "customer_state_changed_or_cart_empty"}
                )
            )
            return plan

        # 3. Pre-dispatch Consent Verification (Review point 5)
        if plan.customer_id and plan.action_type in (ActionType.SEND_RECOVERY_WHATSAPP, ActionType.SEND_RECOVERY_EMAIL):
            purpose = "whatsapp_marketing" if plan.action_type == ActionType.SEND_RECOVERY_WHATSAPP else "email_marketing"
            if not self.consent_port.has_consent(plan.tenant_id, plan.customer_id, purpose):
                plan.status = "rejected"
                self.action_storage.save_plan(plan)
                self.audit_ledger.record_audit(
                    AuditRecord(
                        tenant_id=plan.tenant_id,
                        plan_id=plan.plan_id,
                        actor="orchestrator",
                        event_type="dispatch_aborted_consent_withdrawn",
                        details={"customer_id": plan.customer_id, "purpose": purpose}
                    )
                )
                return plan

        # 4. Idempotency Claim Barrier (Review point 4)
        target = plan.customer_id or plan.parameters.get("component_selector") or plan.parameters.get("segment_name") or "global"
        idempotency_key = f"{plan.tenant_id}:{plan.plan_id}:{plan.action_type.value}:{target}"

        existing_claim = self.action_storage.get_outbound_claim(plan.tenant_id, idempotency_key)
        if existing_claim:
            if existing_claim["status"] == "succeeded":
                # Return cached receipt without invoking outbound adapter
                raw_rcpt = existing_claim.get("receipt")
                if isinstance(raw_rcpt, str):
                    receipt = json.loads(raw_rcpt)
                elif isinstance(raw_rcpt, dict):
                    receipt = raw_rcpt
                else:
                    receipt = {}
                plan.status = "dispatched"
                plan.dispatched_at = existing_claim.get("completed_at") or now.isoformat()
                plan.execution_receipt = receipt
                self.action_storage.save_plan(plan)
                return plan
            elif existing_claim["status"] == "reserved":
                raise RuntimeError(f"Concurrent dispatch in-flight for claim {idempotency_key}")

        # Reserve claim
        reserved = self.action_storage.reserve_outbound_claim(
            tenant_id=plan.tenant_id,
            idempotency_key=idempotency_key,
            plan_id=plan.plan_id,
            action_type=plan.action_type.value,
            reserved_at=now
        )
        if not reserved:
            raise RuntimeError(f"Could not reserve outbound claim {idempotency_key}")

        # 5. Atomic State Transition to 'dispatching'
        current_status = plan.status
        transitioned = self.action_storage.update_plan_status_atomic(
            tenant_id=plan.tenant_id,
            plan_id=plan.plan_id,
            expected_status=current_status,
            new_status="dispatching",
            expected_version=plan.version
        )
        if not transitioned:
            raise RuntimeError(f"Concurrent state modification on plan {plan.plan_id}")
        plan.status = "dispatching"
        plan.version += 1

        # 6. Write-Ahead Audit: dispatch_attempted (Fail closed if write fails)
        try:
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor=actor,
                    event_type="dispatch_attempted",
                    details={
                        "action_type": plan.action_type.value,
                        "idempotency_key": idempotency_key,
                        "target": target
                    }
                )
            )
        except Exception as e:
            # Audit ledger write failed: abort dispatch immediately
            self.action_storage.update_outbound_claim(plan.tenant_id, idempotency_key, status="failed")
            self.action_storage.update_plan_status_atomic(
                tenant_id=plan.tenant_id,
                plan_id=plan.plan_id,
                expected_status="dispatching",
                new_status="failed",
                expected_version=plan.version
            )
            plan.status = "failed"
            plan.version += 1
            raise RuntimeError(f"Fail closed: Audit ledger write failed prior to dispatch: {e}") from e

        # 7. Invoke Outbound Adapter
        receipt: Optional[Dict[str, Any]] = None
        try:
            receipt = self._call_adapter(plan, idempotency_key)
        except TimeoutError as te:
            # Review point 4: Timeout is reconciliation_needed, not failed
            self.action_storage.update_outbound_claim(plan.tenant_id, idempotency_key, status="reconciliation_needed")
            self.action_storage.update_plan_status_atomic(
                tenant_id=plan.tenant_id,
                plan_id=plan.plan_id,
                expected_status="dispatching",
                new_status="reconciliation_needed",
                expected_version=plan.version
            )
            plan.status = "reconciliation_needed"
            plan.version += 1
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor=actor,
                    event_type="dispatch_reconciliation_needed",
                    details={"error": str(te), "idempotency_key": idempotency_key}
                )
            )
            return plan
        except Exception as ex:
            # Outbound dispatch failure
            self.action_storage.update_outbound_claim(plan.tenant_id, idempotency_key, status="failed")
            self.action_storage.update_plan_status_atomic(
                tenant_id=plan.tenant_id,
                plan_id=plan.plan_id,
                expected_status="dispatching",
                new_status="failed",
                expected_version=plan.version
            )
            plan.status = "failed"
            plan.version += 1
            self.audit_ledger.record_audit(
                AuditRecord(
                    tenant_id=plan.tenant_id,
                    plan_id=plan.plan_id,
                    actor=actor,
                    event_type="dispatch_failed",
                    details={"error": str(ex), "idempotency_key": idempotency_key}
                )
            )
            return plan

        # 8. Post-Dispatch Tracking & Atomic Success
        self.action_storage.update_outbound_claim(
            tenant_id=plan.tenant_id,
            idempotency_key=idempotency_key,
            status="succeeded",
            receipt=receipt,
            completed_at=now
        )

        # Outreach log tracking
        if plan.action_type in (ActionType.SEND_RECOVERY_WHATSAPP, ActionType.SEND_RECOVERY_EMAIL) and plan.customer_id:
            channel = "whatsapp" if plan.action_type == ActionType.SEND_RECOVERY_WHATSAPP else "email"
            self.action_storage.record_outreach(
                tenant_id=plan.tenant_id,
                log_id=f"log_{plan.plan_id}",
                recipient_type="customer",
                recipient_id=plan.customer_id,
                channel=channel,
                template_name=plan.parameters.get("template_name", "generic"),
                sent_at=now,
                status="sent"
            )

        # Daily cumulative budget & discount tracking
        date_key = now.strftime("%Y-%m-%d")
        if "fee_amount_paise" in plan.parameters:
            self.action_storage.record_daily_spend(
                plan.tenant_id, date_key, discount_paise=plan.parameters["fee_amount_paise"], budget_shifted_paise=0, timestamp=now
            )
        elif "discount_amount_paise" in plan.parameters:
            self.action_storage.record_daily_spend(
                plan.tenant_id, date_key, discount_paise=plan.parameters["discount_amount_paise"], budget_shifted_paise=0, timestamp=now
            )
        elif "delta_amount_paise" in plan.parameters:
            self.action_storage.record_daily_spend(
                plan.tenant_id, date_key, discount_paise=0, budget_shifted_paise=plan.parameters["delta_amount_paise"], timestamp=now
            )

        # Atomic transition to 'dispatched'
        self.action_storage.update_plan_status_atomic(
            tenant_id=plan.tenant_id,
            plan_id=plan.plan_id,
            expected_status="dispatching",
            new_status="dispatched",
            expected_version=plan.version,
            dispatched_at=now.isoformat(),
            execution_receipt=receipt
        )
        plan.status = "dispatched"
        plan.dispatched_at = now.isoformat()
        plan.execution_receipt = receipt
        plan.version += 1

        self.audit_ledger.record_audit(
            AuditRecord(
                tenant_id=plan.tenant_id,
                plan_id=plan.plan_id,
                actor=actor,
                event_type="dispatch_succeeded",
                details={"receipt": receipt, "idempotency_key": idempotency_key}
            )
        )

        return plan

    def _call_adapter(self, plan: ActionPlan, idempotency_key: str) -> Dict[str, Any]:
        """Dispatches call to the correct typed port adapter."""
        atype = plan.action_type
        params = plan.parameters

        if atype == ActionType.WAIVE_DELIVERY_FEE:
            fee_inr = params["fee_amount_paise"] / 100.0
            return self.loyalty_adapter.waive_delivery_fee(
                customer_id=params["customer_id"],
                fee_amount=fee_inr,
                points_deducted=params.get("points_deducted", 0),
                idempotency_key=idempotency_key
            )

        elif atype == ActionType.GRANT_BONUS_POINTS:
            return self.loyalty_adapter.grant_bonus_points(
                customer_id=params["customer_id"],
                points=params["points"],
                reason=params["reason"],
                idempotency_key=idempotency_key
            )

        elif atype == ActionType.ISSUE_DISCOUNT_COUPON:
            disc_inr = params["discount_amount_paise"] / 100.0
            return self.loyalty_adapter.issue_discount_coupon(
                customer_id=params["customer_id"],
                coupon_code=params["coupon_code"],
                discount_amount=disc_inr,
                idempotency_key=idempotency_key
            )

        elif atype == ActionType.REQUEST_DENSE_TELEMETRY:
            return self.behavior_adapter.request_dense_telemetry(
                component_selector=params["component_selector"],
                duration_minutes=params["duration_minutes"],
                sample_rate=params.get("sample_rate", 1.0)
            )

        elif atype == ActionType.FLAG_UI_FRICTION_BUG:
            return self.behavior_adapter.register_ui_friction_bug(
                component_selector=params["component_selector"],
                friction_type=params["friction_type"],
                session_count=params["session_count"],
                evidence=params.get("evidence", {})
            )

        elif atype == ActionType.SYNC_AUDIENCE_SEGMENT:
            return self.ads_adapter.sync_audience_segment(
                segment_name=params["segment_name"],
                customer_identifiers=params["customer_identifiers"],
                target_platform=params.get("target_platform", "all")
            )

        elif atype == ActionType.SHIFT_CAMPAIGN_BUDGET:
            shift_inr = params["delta_amount_paise"] / 100.0
            return self.ads_adapter.shift_campaign_budget(
                from_campaign_id=params["from_campaign_id"],
                to_campaign_id=params["to_campaign_id"],
                delta_amount_inr=shift_inr,
                idempotency_key=idempotency_key
            )

        elif atype in (ActionType.SEND_RECOVERY_WHATSAPP, ActionType.SEND_RECOVERY_EMAIL):
            return self.notification_adapter.send_recovery_message(
                recipient=params["recipient"],
                channel=params["channel"],
                template_name=params["template_name"],
                parameters=params.get("parameters", {}),
                idempotency_key=idempotency_key
            )

        else:
            raise ValueError(f"Unsupported action type for dispatch: {atype}")
