"""
Campaign Deployment Service and State Machine Orchestrator
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from domain.plans import CampaignPlan, PlanStatus
from engines.validation_engine import CampaignValidationEngine, ValidationResult
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.base import AdsConnectorBase
from events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class CampaignDeploymentService:
    """
    Manages the lifecycle state machine for Google Ads campaigns:
    DRAFT -> VALIDATING -> AWAITING_APPROVAL -> APPROVED -> DEPLOYING -> ACTIVE

    Enforces that unvalidated or unapproved campaigns cannot be executed.
    Supports dry-run validation (validate_only=True) before real commit.
    """

    def __init__(
        self,
        storage: SqlAdsStorageAdapter,
        connector: AdsConnectorBase,
        validation_engine: Optional[CampaignValidationEngine] = None,
        publisher: Optional[EventPublisher] = None
    ):
        self.storage = storage
        self.connector = connector
        self.validation_engine = validation_engine or CampaignValidationEngine()
        self.publisher = publisher or EventPublisher()

    def validate_plan(self, plan_id: str) -> CampaignPlan:
        """
        Validates campaign against editorial, financial, and structural constraints.
        Transitions DRAFT -> VALIDATING -> AWAITING_APPROVAL (or VALIDATION_FAILED).
        """
        plan = self.storage.get_campaign_plan(plan_id)
        if not plan:
            raise ValueError(f"Campaign plan '{plan_id}' not found.")

        if plan.status not in (PlanStatus.DRAFT, PlanStatus.VALIDATION_FAILED):
            logger.info(f"Re-validating plan {plan_id} currently in status {plan.status.value}")

        self.storage.update_plan_status(plan_id, PlanStatus.VALIDATING)

        val_result: ValidationResult = self.validation_engine.validate(plan)

        if val_result.is_valid:
            updated_plan = self.storage.update_plan_status(
                plan_id=plan_id,
                status=PlanStatus.AWAITING_APPROVAL,
                validation_errors=[],
                validation_warnings=val_result.warnings
            )
            logger.info(f"Plan {plan_id} passed validation; moved to AWAITING_APPROVAL.")
        else:
            updated_plan = self.storage.update_plan_status(
                plan_id=plan_id,
                status=PlanStatus.VALIDATION_FAILED,
                validation_errors=val_result.errors,
                validation_warnings=val_result.warnings
            )
            logger.warning(f"Plan {plan_id} failed validation with {len(val_result.errors)} errors.")

        return updated_plan

    def approve_plan(
        self,
        plan_id: str,
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> CampaignPlan:
        """
        Transitions AWAITING_APPROVAL -> APPROVED.
        Requires that the campaign is strictly in AWAITING_APPROVAL status.
        """
        plan = self.storage.get_campaign_plan(plan_id)
        if not plan:
            raise ValueError(f"Campaign plan '{plan_id}' not found.")

        if plan.status != PlanStatus.AWAITING_APPROVAL:
            raise ValueError(
                f"Cannot approve plan in status '{plan.status.value}'. "
                f"Plan must be in 'AWAITING_APPROVAL' state."
            )

        updated_plan = self.storage.update_plan_status(
            plan_id=plan_id,
            status=PlanStatus.APPROVED,
            approved_by=approved_by,
            approval_notes=approval_notes
        )
        logger.info(f"Plan {plan_id} approved by '{approved_by}'; ready for deployment.")
        return updated_plan

    def deploy_plan(
        self,
        plan_id: str,
        validate_only: bool = False
    ) -> CampaignPlan:
        """
        Deploys an approved campaign to Google Ads API.
        If validate_only=True, runs a non-committing dry-run check.
        Transitions APPROVED -> DEPLOYING -> ACTIVE (or DEPLOYMENT_FAILED).
        """
        plan = self.storage.get_campaign_plan(plan_id)
        if not plan:
            raise ValueError(f"Campaign plan '{plan_id}' not found.")

        if plan.status != PlanStatus.APPROVED:
            raise ValueError(
                f"Cannot deploy plan in status '{plan.status.value}'. "
                f"Plan must be approved prior to deployment."
            )

        if validate_only:
            logger.info(f"Executing dry-run validation for plan {plan_id}...")
            deploy_result = self.connector.deploy_campaign(
                account_id=plan.account_id,
                plan=plan,
                validate_only=True
            )
            if not deploy_result.get("success", False):
                raise RuntimeError(f"Dry-run deployment failed: {deploy_result.get('message')}")
            return plan

        # Full deployment
        self.storage.update_plan_status(plan_id, PlanStatus.DEPLOYING)
        logger.info(f"Deploying campaign {plan_id} to account {plan.account_id}...")

        try:
            deploy_result = self.connector.deploy_campaign(
                account_id=plan.account_id,
                plan=plan,
                validate_only=False
            )

            if deploy_result.get("success", False):
                deployed_id = deploy_result.get("deployed_campaign_id", f"camp_{plan_id[-6:]}")
                updated_plan = self.storage.update_plan_status(
                    plan_id=plan_id,
                    status=PlanStatus.ACTIVE,
                    deployed_campaign_id=deployed_id
                )
                logger.info(f"Plan {plan_id} successfully deployed as campaign {deployed_id}.")

                # Emit event
                self.publisher.publish(
                    event_type="ads.campaign.deployed",
                    payload={
                        "workspace_id": plan.workspace_id,
                        "account_id": plan.account_id,
                        "plan_id": plan_id,
                        "deployed_campaign_id": deployed_id,
                        "daily_budget_paise": plan.daily_budget_paise,
                        "deployed_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                return updated_plan
            else:
                err_msg = deploy_result.get("message", "Unknown deployment error")
                updated_plan = self.storage.update_plan_status(
                    plan_id=plan_id,
                    status=PlanStatus.DEPLOYMENT_FAILED,
                    validation_errors=[err_msg]
                )
                return updated_plan

        except Exception as e:
            logger.error(f"Failed to deploy campaign plan {plan_id}: {e}")
            updated_plan = self.storage.update_plan_status(
                plan_id=plan_id,
                status=PlanStatus.DEPLOYMENT_FAILED,
                validation_errors=[str(e)]
            )
            return updated_plan

    def pause_plan(self, plan_id: str) -> CampaignPlan:
        plan = self.storage.get_campaign_plan(plan_id)
        if not plan:
            raise ValueError(f"Campaign plan '{plan_id}' not found.")
        return self.storage.update_plan_status(plan_id, PlanStatus.PAUSED)

    def archive_plan(self, plan_id: str) -> CampaignPlan:
        plan = self.storage.get_campaign_plan(plan_id)
        if not plan:
            raise ValueError(f"Campaign plan '{plan_id}' not found.")
        return self.storage.update_plan_status(plan_id, PlanStatus.ARCHIVED)
