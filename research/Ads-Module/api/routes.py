"""
FastAPI Routes for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel, Field

from domain.models import AccountConnection, AccountStatus, AdsCampaignDaily
from services.sync_service import AdsSyncService, SyncResult
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.base import AdsConnectorBase

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


# Dependency injection container holder
class AdsModuleContainer:
    storage: SqlAdsStorageAdapter
    connector: AdsConnectorBase
    sync_service: AdsSyncService


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
