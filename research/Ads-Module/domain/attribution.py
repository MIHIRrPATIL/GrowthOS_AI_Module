"""
Closed-Loop Attribution Domain Models
Maps Google Click IDs (gclid), UTM tracking, and purchase conversions.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ClickRecord(BaseModel):
    """
    Represents an incoming ad click or session landing with tracking parameters.
    """
    model_config = ConfigDict(extra="forbid")

    click_id: str = Field(default_factory=lambda: f"clk_{uuid.uuid4().hex[:12]}")
    workspace_id: str = Field(..., min_length=1)
    gclid: Optional[str] = Field(default=None, description="Google Click Identifier")
    utm_source: Optional[str] = Field(default=None)
    utm_campaign: Optional[str] = Field(default=None)
    utm_medium: Optional[str] = Field(default=None)
    utm_term: Optional[str] = Field(default=None)
    utm_content: Optional[str] = Field(default=None)
    anonymous_id: str = Field(..., min_length=1, description="Device/cookie anonymous ID")
    user_id: Optional[str] = Field(default=None, description="Identified customer phone/email ID")
    landing_page: str = Field(default="/")
    clicked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConversionRecord(BaseModel):
    """
    Represents an order completed event matched back to Google Ads clicks for closed-loop attribution.
    Monetary amounts strictly stored in integer paise.
    """
    model_config = ConfigDict(extra="forbid")

    conversion_id: str = Field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}")
    workspace_id: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1, description="Google Ads Customer ID")
    order_id: str = Field(..., min_length=1)
    anonymous_id: str = Field(..., min_length=1)
    user_id: Optional[str] = Field(default=None)
    amount_paise: int = Field(..., ge=0, description="Order transaction amount in integer paise")
    amount_inr: float = Field(..., ge=0.0, description="Order transaction amount in decimal INR")
    currency: str = Field(default="INR")
    converted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    matched_gclid: Optional[str] = Field(default=None)
    matched_click_id: Optional[str] = Field(default=None)
    attribution_type: Literal["DIRECT_GCLID", "LAST_TOUCH_UTM", "ORGANIC"] = "ORGANIC"
    conversion_action_name: str = Field(default="Purchases")
    uploaded_to_google: bool = Field(default=False)
    uploaded_at: Optional[str] = Field(default=None)


class IngestClickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    gclid: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    anonymous_id: str
    user_id: Optional[str] = None
    landing_page: str = "/"
    clicked_at: Optional[str] = None


class IngestConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    account_id: str
    order_id: str
    anonymous_id: str
    user_id: Optional[str] = None
    amount_inr: float = Field(..., ge=0.0)
    currency: str = "INR"
    converted_at: Optional[str] = None
    conversion_action_name: str = "Purchases"


class AttributionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_conversions: int
    direct_gclid_conversions: int
    utm_conversions: int
    organic_conversions: int
    total_attributed_revenue_paise: int
    total_attributed_revenue_inr: float
    total_revenue_inr: float
    uploaded_conversions_count: int
    pending_upload_count: int
