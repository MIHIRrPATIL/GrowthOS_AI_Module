"""
Domain Events published by GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, ConfigDict


class MetricsUpdatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: f"evt_ads_{uuid.uuid4().hex[:12]}")
    event_name: str = "ads.metrics.updated"
    workspace_id: str
    account_id: str
    platform: str = "google_ads"
    date_start: str
    date_end: str
    record_count: int
    emitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
