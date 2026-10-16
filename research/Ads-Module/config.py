"""
Configuration reader for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional
import os
from pathlib import Path
from pydantic import BaseModel, Field


def _load_env_file() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
        Path(__file__).parents[1] / ".env",
        Path(__file__).parents[2] / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()


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
