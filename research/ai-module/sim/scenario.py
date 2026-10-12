"""
Scenario Specification Models and Scenario Hashing
GrowthOS Randomized Scenario Test Environment

Strictly NO emojis in code, docstrings, or logs.
"""

import json
import hashlib
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class TenantVertical(str, Enum):
    QSR = "qsr"
    FASHION = "fashion"
    ELECTRONICS = "electronics"
    GROCERY = "grocery"
    D2C_SUBSCRIPTION = "d2c_subscription"
    TRAVEL = "travel"
    LENDING = "lending"
    SAAS = "saas"


class TenantSizeTier(str, Enum):
    SMALL = "small"
    STANDARD = "standard"
    STRESS = "stress"


class RunMode(str, Enum):
    RANDOM = "random"
    EDGE = "edge"
    COVERAGE = "coverage"
    GOLDEN = "golden"
    STRESS = "stress"


class LoyaltyTier(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


class AdPlatform(str, Enum):
    GOOGLE = "google"
    META = "meta"


class TenantLoyaltyProfile(BaseModel):
    """Module 1 Loyalty & Rewards parameters for a tenant."""
    model_config = ConfigDict(extra="forbid")

    points_earn_ratio: float = Field(default=0.1, description="Points earned per INR spent (e.g. 0.1 = 1 pt / 10 INR)")
    points_burn_rate_paise: int = Field(default=100, description="Value of 1 point in paise when burned (e.g. 100 paise = 1 INR)")
    delivery_fee_waiver_cost_points: int = Field(default=50, description="Points required to waive a delivery fee")
    tier_thresholds: Dict[str, int] = Field(
        default_factory=lambda: {
            "Bronze": 0,
            "Silver": 500,
            "Gold": 1500,
            "Platinum": 5000,
        }
    )
    daily_waiver_budget_paise: int = Field(default=15000, description="Merchant daily budget cap for delivery fee waivers in paise")
    waiver_cooldown_hours: int = Field(default=48, description="Minimum hours required between fee waivers per customer")
    max_bonus_points_per_grant: int = Field(default=200, description="Maximum retention bonus points per single grant")


class TenantSpec(BaseModel):
    """Specification of a single merchant tenant."""
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    name: str
    vertical: TenantVertical
    size_tier: TenantSizeTier
    city: str
    timezone: str = "Asia/Kolkata"
    aov_paise: int = Field(gt=0, description="Average Order Value in integer paise")
    margin_pct: float = Field(ge=0.0, le=100.0)
    delivery_fee_paise: int = Field(ge=0)
    free_delivery_threshold_paise: int = Field(ge=0)
    payment_mix: Dict[str, float] = Field(
        default_factory=lambda: {
            "upi": 0.55,
            "card": 0.20,
            "wallet": 0.10,
            "cod": 0.15,
        }
    )
    loyalty: TenantLoyaltyProfile = Field(default_factory=TenantLoyaltyProfile)


class TrafficSpec(BaseModel):
    """Traffic generation parameters for simulated storefront."""
    model_config = ConfigDict(extra="forbid")

    sessions_per_day: int = Field(gt=0)
    channel_mix: Dict[str, float] = Field(
        default_factory=lambda: {
            "direct": 0.25,
            "organic_search": 0.30,
            "paid_search": 0.25,
            "social": 0.15,
            "referral": 0.05,
        }
    )
    new_vs_returning_ratio: float = Field(ge=0.0, le=1.0, default=0.60)
    mobile_share: float = Field(ge=0.0, le=1.0, default=0.75)
    bot_share: float = Field(ge=0.0, le=1.0, default=0.03)
    ad_blocker_share: float = Field(ge=0.0, le=1.0, default=0.08)


class CampaignSpec(BaseModel):
    """Ad campaign configuration and hidden true performance parameters."""
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    name: str
    platform: AdPlatform
    campaign_type: str = "performance"
    daily_budget_paise: int = Field(gt=0)
    target_cpa_paise: int = Field(gt=0)
    true_roas: float = Field(gt=0.0, description="Hidden true ROAS used by generator")
    quality_score: float = Field(ge=1.0, le=10.0, default=7.0)


class AdsSpec(BaseModel):
    """Module 3 Ads configuration."""
    model_config = ConfigDict(extra="forbid")

    campaigns: List[CampaignSpec]
    total_daily_budget_paise: int = Field(ge=0)


class FaultSpec(BaseModel):
    """Fault and chaos parameters injected into simulation."""
    model_config = ConfigDict(extra="forbid")

    duplicate_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    late_event_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    sdk_loss_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    clock_skew_seconds: int = Field(ge=0, default=0)
    adapter_timeout_after_success: bool = False
    circuit_breaker_failures: int = Field(ge=0, default=0)
    llm_429_call_index: Optional[int] = None


class PlantedEffectSpec(BaseModel):
    """Planted anomalous effect or treatment lift."""
    model_config = ConfigDict(extra="forbid")

    effect_type: str
    magnitude: float
    start_day: int
    duration_days: int
    target_segment: Optional[str] = None


class ScenarioSpec(BaseModel):
    """Complete specification of a simulation run."""
    model_config = ConfigDict(extra="forbid")

    seed: int
    catalog_version: str = "v1"
    mode: RunMode = RunMode.RANDOM
    size: TenantSizeTier = TenantSizeTier.STANDARD
    tenants: List[TenantSpec]
    traffic: TrafficSpec
    ads: AdsSpec
    faults: FaultSpec = Field(default_factory=FaultSpec)
    planted_effects: List[PlantedEffectSpec] = Field(default_factory=list)
    frozen_domains: List[str] = Field(default_factory=list)

    def canonical_json(self) -> str:
        """Returns deterministic canonical JSON string with sorted keys."""
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def scenario_hash(self) -> str:
        """Computes SHA-256 scenario hash over catalog version and canonical JSON."""
        content = f"{self.catalog_version}:{self.canonical_json()}".encode("utf-8")
        return hashlib.sha256(content).hexdigest()[:8]
