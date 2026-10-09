"""
Configuration reader for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional
import os
from pydantic import BaseModel, Field


class AdsModuleConfig(BaseModel):
    # Google Ads Credentials
    developer_token: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"))
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_CLIENT_SECRET"))
    refresh_token: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_REFRESH_TOKEN"))
    login_customer_id: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))
    client_customer_id: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_CLIENT_CUSTOMER_ID"))
    use_proto_plus: bool = Field(default=True)

    # Local Service Configuration
    port: int = Field(default=8001)
    db_url: str = Field(default_factory=lambda: os.getenv("ADS_MODULE_DB_URL", "sqlite:///./ads_module.db"))
    workspace_id: str = Field(default_factory=lambda: os.getenv("WORKSPACE_ID", "tenant_dominos_qsr"))
    ai_module_webhook_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("AI_MODULE_WEBHOOK_URL", "http://localhost:8000/v1/telemetry/events")
    )

    # Operational Parameters
    sync_interval_hours: int = Field(default=2)
    default_lookback_days: int = Field(default=3)
    timezone: str = Field(default="Asia/Kolkata")
    currency: str = Field(default="INR")


def get_config() -> AdsModuleConfig:
    return AdsModuleConfig()
