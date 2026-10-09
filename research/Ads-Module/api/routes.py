"""
FastAPI Routes for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel, Field

from domain.models import AccountConnection, AccountStatus, AdsCampaignDaily
from domain.plans import CampaignPlan, PlanGenerationRequest, PlanStatus
from domain.attribution import (
    ClickRecord,
    ConversionRecord,
    IngestClickRequest,
    IngestConversionRequest,
    AttributionSummary
)
from services.sync_service import AdsSyncService, SyncResult
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.base import AdsConnectorBase
from engines.planning_engine import CampaignPlanningEngine
from engines.validation_engine import CampaignValidationEngine
from services.deployment_service import CampaignDeploymentService
from attribution.click_tracker import ClickTracker
from attribution.conversion_matcher import ConversionMatcher
from connectors.offline_conversion_uploader import OfflineConversionUploader

router = APIRouter(prefix="/api/v1/ads", tags=["Ads Module"])


# Request / Response Schemas
class ConnectAccountRequest(BaseModel):
    workspace_id: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=10, max_length=12, description="10-digit Google Ads customer ID")
    account_name: str = Field(default="Main Ad Account")
    currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Kolkata")
    login_customer_id: Optional[str] = Field(default=None)


class SyncAccountRequest(BaseModel):
    workspace_id: str = Field(..., min_length=1)
    start_date: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD")
    lookback_days: int = Field(default=3, ge=1, le=90)


class ApprovePlanRequest(BaseModel):
    approved_by: str = Field(..., min_length=1, description="Merchant user or automated brain ID")
    approval_notes: Optional[str] = Field(default=None)


# Dependency injection container holder
class AdsModuleContainer:
    storage: SqlAdsStorageAdapter
    connector: AdsConnectorBase
    sync_service: AdsSyncService
    planning_engine: CampaignPlanningEngine
    validation_engine: CampaignValidationEngine
    deployment_service: CampaignDeploymentService
    click_tracker: ClickTracker
    conversion_matcher: ConversionMatcher
    conversion_uploader: OfflineConversionUploader


_container: Optional[AdsModuleContainer] = None


def set_container(container: AdsModuleContainer) -> None:
    global _container
    _container = container


def get_container() -> AdsModuleContainer:
    if _container is None:
        raise RuntimeError("AdsModuleContainer not initialized")
    return _container


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health")
def health_check(container: AdsModuleContainer = Depends(get_container)) -> Dict[str, Any]:
    connector_health = container.connector.health_check()
    return {
        "status": "healthy",
        "service": "growthos-ads-module",
        "connector": connector_health
    }


@router.post("/accounts/connect", response_model=AccountConnection)
def connect_account(
    req: ConnectAccountRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> AccountConnection:
    connection = AccountConnection(
        workspace_id=req.workspace_id,
        account_id=req.account_id,
        account_name=req.account_name,
        currency=req.currency,
        timezone=req.timezone,
        login_customer_id=req.login_customer_id,
        status=AccountStatus.ACTIVE
    )
    container.storage.save_account_connection(connection)
    return connection


@router.get("/accounts", response_model=List[AccountConnection])
def list_accounts(
    workspace_id: str = Query(..., min_length=1),
    container: AdsModuleContainer = Depends(get_container)
) -> List[AccountConnection]:
    return container.storage.list_account_connections(workspace_id=workspace_id)


@router.post("/accounts/{account_id}/sync", response_model=SyncResult)
def trigger_sync(
    account_id: str,
    req: SyncAccountRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> SyncResult:
    res = container.sync_service.sync_account(
        workspace_id=req.workspace_id,
        account_id=account_id,
        start_date=req.start_date,
        end_date=req.end_date,
        lookback_days=req.lookback_days
    )
    if not res.success:
        raise HTTPException(status_code=502, detail=f"Sync failed: {res.error_message}")
    return res


@router.get("/campaigns/{campaign_id}/metrics", response_model=List[AdsCampaignDaily])
def get_campaign_metrics(
    campaign_id: str,
    start_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD"),
    container: AdsModuleContainer = Depends(get_container)
) -> List[AdsCampaignDaily]:
    today = date.today()
    if not end_date:
        end_date = today.isoformat()
    if not start_date:
        start_date = (today - timedelta(days=30)).isoformat()

    return container.storage.get_campaign_daily_metrics(
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/campaigns/metrics/bulk", response_model=List[AdsCampaignDaily])
def get_bulk_metrics(
    workspace_id: str = Query(..., min_length=1),
    start_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO YYYY-MM-DD"),
    container: AdsModuleContainer = Depends(get_container)
) -> List[AdsCampaignDaily]:
    today = date.today()
    if not end_date:
        end_date = today.isoformat()
    if not start_date:
        start_date = (today - timedelta(days=30)).isoformat()

    return container.storage.get_bulk_metrics(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date
    )


# =============================================================================
# Campaign Planning & Lifecycle State Machine Endpoints (Phase 3)
# =============================================================================

@router.post("/campaigns/plan", response_model=CampaignPlan)
def generate_campaign_plan(
    req: PlanGenerationRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> CampaignPlan:
    """
    Synthesizes a structured CampaignPlan from natural language prompt / merchant goals.
    Initial state: DRAFT.
    """
    plan = container.planning_engine.generate_plan(req)
    container.storage.save_campaign_plan(plan)
    return plan


@router.get("/campaigns/plans", response_model=List[CampaignPlan])
def list_campaign_plans(
    workspace_id: str = Query(..., min_length=1),
    status: Optional[PlanStatus] = Query(None),
    container: AdsModuleContainer = Depends(get_container)
) -> List[CampaignPlan]:
    return container.storage.list_campaign_plans(workspace_id=workspace_id, status=status)


@router.get("/campaigns/plans/{plan_id}", response_model=CampaignPlan)
def get_campaign_plan(
    plan_id: str,
    container: AdsModuleContainer = Depends(get_container)
) -> CampaignPlan:
    plan = container.storage.get_campaign_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Campaign plan '{plan_id}' not found")
    return plan


@router.post("/campaigns/plans/{plan_id}/validate", response_model=CampaignPlan)
def validate_campaign_plan(
    plan_id: str,
    container: AdsModuleContainer = Depends(get_container)
) -> CampaignPlan:
    """
    Executes validation checks against financial, editorial, and platform constraints.
    Transitions: DRAFT -> VALIDATING -> AWAITING_APPROVAL (or VALIDATION_FAILED).
    """
    try:
        return container.deployment_service.validate_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/campaigns/plans/{plan_id}/approve", response_model=CampaignPlan)
def approve_campaign_plan(
    plan_id: str,
    req: ApprovePlanRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> CampaignPlan:
    """
    Approves validated plan for deployment.
    Transitions: AWAITING_APPROVAL -> APPROVED.
    """
    try:
        return container.deployment_service.approve_plan(
            plan_id=plan_id,
            approved_by=req.approved_by,
            approval_notes=req.approval_notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/plans/{plan_id}/deploy", response_model=CampaignPlan)
def deploy_campaign_plan(
    plan_id: str,
    validate_only: bool = Query(default=False, description="Dry-run validation with Google Ads API without committing spend"),
    container: AdsModuleContainer = Depends(get_container)
) -> CampaignPlan:
    """
    Deploys approved campaign to Google Ads API.
    Transitions: APPROVED -> DEPLOYING -> ACTIVE (or DEPLOYMENT_FAILED).
    """
    try:
        return container.deployment_service.deploy_plan(
            plan_id=plan_id,
            validate_only=validate_only
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


# =============================================================================
# Closed-Loop Attribution Endpoints (Phase 4)
# =============================================================================

@router.post("/attribution/clicks", response_model=ClickRecord)
def ingest_ad_click(
    req: IngestClickRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> ClickRecord:
    """
    Ingests ad click and session tracking data (gclid, UTM parameters).
    """
    return container.click_tracker.record_click(req)


@router.post("/attribution/conversions", response_model=ConversionRecord)
def ingest_order_conversion(
    req: IngestConversionRequest,
    container: AdsModuleContainer = Depends(get_container)
) -> ConversionRecord:
    """
    Matches order completed events back to initial ad clicks within lookback window.
    """
    return container.conversion_matcher.match_and_record_conversion(req)


@router.post("/attribution/conversions/upload")
def upload_offline_conversions(
    workspace_id: str = Query(..., min_length=1),
    container: AdsModuleContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Uploads pending attributed conversions (with gclids) to Google Ads ConversionUploadService.
    """
    return container.conversion_uploader.upload_pending_conversions(workspace_id=workspace_id)


@router.get("/attribution/summary", response_model=AttributionSummary)
def get_attribution_summary(
    workspace_id: str = Query(..., min_length=1),
    container: AdsModuleContainer = Depends(get_container)
) -> AttributionSummary:
    """
    Returns closed-loop attribution metrics (GCLID vs UTM vs Organic, attributed revenue).
    """
    data = container.storage.get_attribution_summary(workspace_id)
    return AttributionSummary(**data)


@router.get("/attribution/conversions", response_model=List[ConversionRecord])
def list_conversions(
    workspace_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=500),
    container: AdsModuleContainer = Depends(get_container)
) -> List[ConversionRecord]:
    return container.storage.list_conversions(workspace_id=workspace_id, limit=limit)
