"""
Domain Models and Canonical Schemas for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PAUSED = "PAUSED"


class CampaignStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class AccountConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., description="Tenant workspace ID")
    account_id: str = Field(..., description="Google Ads Customer ID (10 digits without hyphens)")
    platform: str = Field(default="google_ads")
    account_name: str = Field(default="Main Ad Account")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE)
    currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Kolkata")
    login_customer_id: Optional[str] = Field(default=None, description="Manager (MCC) ID if managed")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CampaignRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(...)
    account_id: str = Field(...)
    name: str = Field(...)
    status: CampaignStatus = Field(default=CampaignStatus.ACTIVE)
    channel_type: str = Field(default="SEARCH")
    daily_budget_paise: int = Field(default=0, ge=0)


class RawGoogleAdsRow(BaseModel):
    """
    Representation of raw GAQL response row from Google Ads SearchStream.
    Money fields are reported in Google's native micros.
    """
    model_config = ConfigDict(extra="ignore")

    campaign_id: str
    campaign_name: str
    campaign_status: str  # "ENABLED", "PAUSED", "REMOVED"
    date: str             # "YYYY-MM-DD"
    cost_micros: int = 0
    impressions: int = 0
    clicks: int = 0
    conversions: float = 0.0
    conversions_value_micros: int = 0


class AdsCampaignDaily(BaseModel):
    """
    Canonical 12-field normalized daily performance record consumed by GrowthOS AI Module.
    Monetary amounts are stored in strict integer paise with decimal currency provided for convenience.
    """
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    platform: str = "google_ads"
    account_id: str
    campaign_id: str
    campaign_name: str
    date: str                          # ISO date YYYY-MM-DD
    spend_paise: int = Field(..., ge=0, description="Spend in integer paise")
    spend_inr: float = Field(..., ge=0.0, description="Spend in decimal INR")
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: float = Field(default=0.0, ge=0.0)
    conversion_value_paise: int = Field(default=0, ge=0)
    ctr: float = Field(default=0.0, ge=0.0, le=1.0)
    cpc_paise: int = Field(default=0, ge=0)
    cpa_paise: int = Field(default=0, ge=0)
    roas: float = Field(default=0.0, ge=0.0)
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    status: str = "ACTIVE"
    synced_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
