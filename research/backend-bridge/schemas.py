"""
GrowthOS Canonical Schemas for Event Ingestion & Behavioral Signals
Module 2 -> Module 4 Pipeline
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PageMetadata(BaseModel):
    url: str
    path: str
    title: Optional[str] = None
    referrer: Optional[str] = None
    search: Optional[str] = None


class UTMMetadata(BaseModel):
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    term: Optional[str] = None
    content: Optional[str] = None


class DeviceMetadata(BaseModel):
    screen_width: int
    screen_height: int
    viewport_width: int
    viewport_height: int
    pixel_ratio: float = 1.0
    orientation: str = "portrait"
    user_agent: str = ""
    browser: str = "unknown"
    browser_version: str = ""
    os: str = "unknown"
    os_version: str = ""
    device_type: str = "desktop"
    language: str = "en"
    timezone: str = "UTC"
    timezone_offset: int = 0


class NetworkMetadata(BaseModel):
    effective_type: Optional[str] = None
    downlink: Optional[float] = None
    rtt: Optional[int] = None
    save_data: Optional[bool] = None


class EventEnvelope(BaseModel):
    event_id: str
    event_name: str
    timestamp: str
    workspace_id: Optional[str] = None
    project_id: str
    anonymous_id: str
    customer_id: Optional[str] = None
    session_id: str
    idempotency_key: str
    page: PageMetadata
    utm: UTMMetadata
    device: DeviceMetadata
    network: Optional[NetworkMetadata] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchEventRequest(BaseModel):
    events: List[EventEnvelope]


class DerivedBehavioralSignal(BaseModel):
    signal_id: str
    signal_type: str
    customer_id: Optional[str] = None
    anonymous_id: str
    session_id: str
    workspace_id: Optional[str] = None
    confidence: float
    detected_at: str
    summary: str
    evidence: Dict[str, Any]
    recommended_action: Optional[str] = None
    affected_module: str = "Module 4"
