"""
Campaign Planning and Deployment Domain Models
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ObjectiveType(str, Enum):
    SALES = "SALES"
    LEADS = "LEADS"
    WEBSITE_TRAFFIC = "WEBSITE_TRAFFIC"
    BRAND_AWARENESS = "BRAND_AWARENESS"


class BiddingStrategyType(str, Enum):
    TARGET_CPA = "TARGET_CPA"
    TARGET_ROAS = "TARGET_ROAS"
    MAXIMIZE_CONVERSIONS = "MAXIMIZE_CONVERSIONS"
    MAXIMIZE_CLICKS = "MAXIMIZE_CLICKS"
    MANUAL_CPC = "MANUAL_CPC"


class KeywordMatchType(str, Enum):
    EXACT = "EXACT"
    PHRASE = "PHRASE"
    BROAD = "BROAD"


class KeywordMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, description="Keyword text")
    match_type: KeywordMatchType = Field(default=KeywordMatchType.PHRASE)
    bid_paise: Optional[int] = Field(default=None, ge=0, description="Optional custom bid in paise")


class KeywordCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Cluster name (e.g., High Intent, Competitor, Brand)")
    keywords: List[KeywordMatch] = Field(default_factory=list, min_length=1)


class AdCopy(BaseModel):
    """
    Responsive Search Ad specification conforming to Google Ads constraints:
    - Headlines: 3 to 15 headlines, each <= 30 characters
    - Descriptions: 2 to 4 descriptions, each <= 90 characters
    - Final URL: HTTPS URL
    """
    model_config = ConfigDict(extra="forbid")

    headlines: List[str] = Field(..., min_length=3, max_length=15)
    descriptions: List[str] = Field(..., min_length=2, max_length=4)
    final_url: str = Field(...)
    display_path_1: Optional[str] = Field(default=None, max_length=15)
    display_path_2: Optional[str] = Field(default=None, max_length=15)

    @field_validator("headlines")
    @classmethod
    def validate_headlines(cls, v: List[str]) -> List[str]:
        for h in v:
            if not h.strip():
                raise ValueError("Headline cannot be blank")
            if len(h) > 30:
                raise ValueError(f"Headline exceeds 30 characters: '{h}' ({len(h)} chars)")
        return v

    @field_validator("descriptions")
    @classmethod
    def validate_descriptions(cls, v: List[str]) -> List[str]:
        for d in v:
            if not d.strip():
                raise ValueError("Description cannot be blank")
            if len(d) > 90:
                raise ValueError(f"Description exceeds 90 characters: '{d}' ({len(d)} chars)")
        return v

    @field_validator("final_url")
    @classmethod
    def validate_final_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"Final URL must use https:// protocol, got: {v}")
        return v


class TargetGeography(BaseModel):
    model_config = ConfigDict(extra="forbid")

    countries: List[str] = Field(default=["IN"])
    cities: List[str] = Field(default_factory=list)
    radius_km: Optional[int] = Field(default=None, ge=1)
    postal_codes: List[str] = Field(default_factory=list)


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
    PLATFORM_REJECTED = "PLATFORM_REJECTED"


class CampaignPlan(BaseModel):
    """
    Comprehensive campaign proposal produced by PlanningEngine, validated by ValidationEngine,
    and deployed via DeploymentService.
    Monetary bounds strictly in integer paise.
    """
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    workspace_id: str = Field(...)
    account_id: str = Field(...)
    name: str = Field(..., min_length=3, max_length=128)
    objective: ObjectiveType = Field(default=ObjectiveType.SALES)
    channel_type: str = Field(default="SEARCH")
    daily_budget_paise: int = Field(..., ge=10000, description="Budget in paise (min 100 INR)")
    daily_budget_inr: float = Field(..., ge=100.0, description="Budget in decimal INR")
    bidding_strategy: BiddingStrategyType = Field(default=BiddingStrategyType.TARGET_CPA)
    target_cpa_paise: Optional[int] = Field(default=None, ge=0)
    target_cpa_inr: Optional[float] = Field(default=None, ge=0.0)
    target_roas: Optional[float] = Field(default=None, ge=0.0)
    target_geography: TargetGeography = Field(default_factory=TargetGeography)
    keyword_clusters: List[KeywordCluster] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    ad_copies: List[AdCopy] = Field(default_factory=list)
    status: PlanStatus = Field(default=PlanStatus.DRAFT)
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    approval_notes: Optional[str] = None
    approved_by: Optional[str] = None
    deployed_campaign_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PlanGenerationRequest(BaseModel):
    """
    Request payload to generate a CampaignPlan from natural language prompt or goal.
    """
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    account_id: str
    goal_prompt: str = Field(..., min_length=5, description="Marketing intent (e.g., 'Increase weekend pizza delivery orders in Mumbai')")
    store_name: str = Field(default="Store", description="Merchant business name")
    store_url: str = Field(default="https://example.com", description="Destination store URL")
    daily_budget_inr: Optional[float] = Field(default=2000.0, ge=100.0)
    target_cpa_inr: Optional[float] = Field(default=250.0, ge=10.0)
    target_cities: List[str] = Field(default_factory=lambda: ["Mumbai"])
    product_category: Optional[str] = Field(default="Food & Dining")
