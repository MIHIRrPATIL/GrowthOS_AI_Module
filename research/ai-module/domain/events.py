"""
Universal Event Envelope and Telemetry Schemas
Conforms to:
- research/docs/event_taxonomy_spec.md
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator
import uuid


class PageMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str = Field(default="https://dominos.co.in/menu")
    path: str = Field(default="/menu")
    title: str = Field(default="Domino's Pizza India")
    referrer: Optional[str] = None
    search: Optional[str] = None


class UTMMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    term: Optional[str] = None
    content: Optional[str] = None


class DeviceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    screen_width: int = Field(default=1280)
    screen_height: int = Field(default=800)
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    pixel_ratio: float = Field(default=1.0)
    orientation: str = Field(default="landscape")
    user_agent: str = Field(default="Mozilla/5.0 (X11; Linux x86_64)")
    browser: str = Field(default="Chrome")
    browser_version: str = Field(default="120.0")
    os: str = Field(default="Linux")
    os_version: str = Field(default="6.0")
    device_type: str = Field(default="desktop")
    language: str = Field(default="en-IN")
    timezone: str = Field(default="Asia/Kolkata")
    timezone_offset: int = Field(default=-330)


class NetworkMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    effective_type: str = Field(default="4g")
    downlink: float = Field(default=10.0)
    rtt: int = Field(default=50)
    save_data: bool = Field(default=False)


class ConsentState(BaseModel):
    model_config = ConfigDict(extra="allow")

    analytics: bool = Field(default=True)
    marketing: bool = Field(default=True)
    outreach: bool = Field(default=True)
    profiling: bool = Field(default=True)


class EventEnvelope(BaseModel):
    """
    Canonical Universal Event Envelope for GrowthOS.
    Every event ingested or normalized across all modules adheres to this contract.
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    schema_version: str = Field(default="1.0.0")
    tenant_id: str = Field(..., alias="workspace_id", description="Tenant / Workspace identifier")
    project_id: str = Field(default="proj_growth_01")
    source_module: str = Field(default="module_2_sdk")
    event_name: str = Field(..., description="Canonical event name e.g. product.viewed, checkout.abandoned")
    
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        alias="timestamp"
    )
    received_at: str = Field(default="")
    
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:16]}")
    anonymous_id: str = Field(default_factory=lambda: f"anon_{uuid.uuid4().hex[:16]}")
    customer_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _ensure_timestamps(cls, data: Any):
        if isinstance(data, dict):
            occ = data.get("occurred_at") or data.get("timestamp")
            if not occ:
                occ = datetime.now(timezone.utc).isoformat()
                data["occurred_at"] = occ
            if not data.get("received_at"):
                data["received_at"] = occ
        return data
    
    page: PageMetadata = Field(default_factory=PageMetadata)
    utm: UTMMetadata = Field(default_factory=UTMMetadata)
    device: DeviceMetadata = Field(default_factory=DeviceMetadata)
    network: NetworkMetadata = Field(default_factory=NetworkMetadata)
    consent: ConsentState = Field(default_factory=ConsentState)
    
    properties: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "sdk_version": "1.0.0",
        "sdk_name": "growthos-ai-core",
        "environment": "production"
    })

    def get_idempotency_key(self) -> str:
        return self.idempotency_key or self.event_id

    def get_user_identifier(self) -> str:
        return self.customer_id or self.anonymous_id
