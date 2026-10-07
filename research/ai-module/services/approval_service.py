"""
Human Approval Service
Provides endpoints for human merchant operators to review, approve, or reject pending action plans.
Enforces optimistic concurrency locking, role authorization, and audit trail completion.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from domain.actions import ActionPlan, AuditRecord
from ports.action_storage import ActionStoragePort
from ports.outbound import AuditLedgerPort
from services.action_orchestrator import ActionOrchestrator


class ApprovalService:
    """
    Manages human review and approval workflows for ActionPlans in APPROVAL mode.
    """

    ALLOWED_ROLES = {"merchant_admin", "merchant_owner", "operator", "growth_lead"}

    def __init__(
        self,
        action_storage: ActionStoragePort,
        audit_ledger: AuditLedgerPort,
        orchestrator: ActionOrchestrator
    ):
        self.action_storage = action_storage
        self.audit_ledger = audit_ledger
        self.orchestrator = orchestrator

    def approve_plan(
        self,
        tenant_id: str,
        plan_id: str,
        approver_id: str,
        approver_role: str = "merchant_admin",
        expected_version: int = 1
    ) -> ActionPlan:
        """
        Approves a pending action plan and triggers its atomic execution dispatch.
        """
        # 1. Authorize Approver Role
        if approver_role not in self.ALLOWED_ROLES:
            raise PermissionError(f"Approver {approver_id} with role '{approver_role}' is not authorized to approve plans.")

        # 2. Retrieve Plan
        plan = self.action_storage.get_plan(tenant_id, plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found for tenant '{tenant_id}'.")

        if plan.status != "pending_approval" or plan.version != expected_version:
            raise RuntimeError(f"Concurrent modification on plan '{plan_id}'. Status is '{plan.status}', version is {plan.version} (expected {expected_version}).")

        now = datetime.now(timezone.utc)

        # 3. Atomic State Transition to 'approved'
        transitioned = self.action_storage.update_plan_status_atomic(
            tenant_id=tenant_id,
            plan_id=plan_id,
            expected_status="pending_approval",
            new_status="approved",
            expected_version=expected_version,
            approved_by=approver_id
        )
        if not transitioned:
            raise RuntimeError(f"Concurrent modification on plan '{plan_id}'. Status or version mismatch.")

        plan.status = "approved"
        plan.approved_by = approver_id
        plan.approved_at = now.isoformat()
        plan.version = expected_version + 1

        # 4. Record Audit Event
        self.audit_ledger.record_audit(
            AuditRecord(
                tenant_id=tenant_id,
                plan_id=plan_id,
                actor=f"human:{approver_id}",
                event_type="plan_approved",
                details={
                    "approver_id": approver_id,
                    "approver_role": approver_role,
                    "approved_at": plan.approved_at
                }
            )
        )

        # 5. Trigger Execution Dispatch via Orchestrator
        dispatched_plan = self.orchestrator.execute_dispatch(plan, actor=f"human:{approver_id}")
        return dispatched_plan

    def reject_plan(
        self,
        tenant_id: str,
        plan_id: str,
        rejector_id: str,
        reason: str,
        rejector_role: str = "merchant_admin",
        expected_version: int = 1
    ) -> ActionPlan:
        """
        Rejects a pending action plan and closes its lifecycle.
        """
        if rejector_role not in self.ALLOWED_ROLES:
            raise PermissionError(f"Rejector {rejector_id} with role '{rejector_role}' is not authorized.")

        plan = self.action_storage.get_plan(tenant_id, plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found for tenant '{tenant_id}'.")

        if plan.status != "pending_approval" or plan.version != expected_version:
            raise RuntimeError(f"Concurrent modification on plan '{plan_id}'. Status is '{plan.status}', version is {plan.version} (expected {expected_version}).")

        transitioned = self.action_storage.update_plan_status_atomic(
            tenant_id=tenant_id,
            plan_id=plan_id,
            expected_status="pending_approval",
            new_status="rejected",
            expected_version=expected_version,
            approved_by=rejector_id
        )
        if not transitioned:
            raise RuntimeError(f"Concurrent modification on plan '{plan_id}'. Status or version mismatch.")

        plan.status = "rejected"
        plan.version = expected_version + 1
        self.action_storage.save_plan(plan)

        self.audit_ledger.record_audit(
            AuditRecord(
                tenant_id=tenant_id,
                plan_id=plan_id,
                actor=f"human:{rejector_id}",
                event_type="plan_rejected",
                details={
                    "rejector_id": rejector_id,
                    "rejection_reason": reason
                }
            )
        )
        return plan
