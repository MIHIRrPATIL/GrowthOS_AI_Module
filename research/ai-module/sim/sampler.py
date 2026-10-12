"""
Hierarchical Seeded Scenario Sampler with NumPy SeedSequence
GrowthOS Randomized Scenario Test Environment

Spawns independent seed streams for:
- tenants
- loyalty
- traffic
- funnel
- ads
- customers
- faults
- queries

Supports domain freezing (--freeze loyalty, --freeze ads) to keep specific sub-trees
invariant across root seed changes.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from numpy.random import SeedSequence, default_rng

from .scenario import (
    TenantVertical,
    TenantSizeTier,
    RunMode,
    LoyaltyTier,
    AdPlatform,
    TenantLoyaltyProfile,
    TenantSpec,
    TrafficSpec,
    CampaignSpec,
    AdsSpec,
    FaultSpec,
    PlantedEffectSpec,
    ScenarioSpec,
)


class SeedStreamManager:
    """
    Manages deterministic sub-streams using NumPy SeedSequence.
    If a domain is included in frozen_domains, it uses a fixed seed anchor
    so changes to the root seed do not alter the frozen domain's draws.
    """
    DOMAIN_ORDER = [
        "tenants",
        "loyalty",
        "traffic",
        "funnel",
        "ads",
        "customers",
        "faults",
        "queries",
    ]
    FROZEN_ANCHOR_SEED = 133742

    def __init__(self, root_seed: int, frozen_domains: Optional[List[str]] = None):
        self.root_seed = root_seed
        self.frozen_domains = set(frozen_domains or [])
        self.rngs: Dict[str, np.random.Generator] = {}

        root_seq = SeedSequence(root_seed)
        spawned = root_seq.spawn(len(self.DOMAIN_ORDER))

        frozen_root = SeedSequence(self.FROZEN_ANCHOR_SEED)
        frozen_spawned = frozen_root.spawn(len(self.DOMAIN_ORDER))

        for idx, domain in enumerate(self.DOMAIN_ORDER):
            if domain in self.frozen_domains:
                self.rngs[domain] = default_rng(frozen_spawned[idx])
            else:
                self.rngs[domain] = default_rng(spawned[idx])

    def get_rng(self, domain: str) -> np.random.Generator:
        if domain not in self.rngs:
            # Fallback for unexpected domain
            return default_rng(SeedSequence(self.root_seed + 100))
        return self.rngs[domain]


class ScenarioSampler:
    """
    Samples coherent ScenarioSpec instances using parametric distributions.
    """

    CITIES = [
        "Mumbai",
        "Bengaluru",
        "Delhi NCR",
        "Hyderabad",
        "Pune",
        "Chennai",
        "Kolkata",
        "Ahmedabad",
    ]

    VERTICAL_DEFAULTS = {
        TenantVertical.QSR: {
            "aov_range": (35000, 85000),             # 350 - 850 INR
            "delivery_fee_range": (3500, 6000),      # 35 - 60 INR
            "free_delivery_threshold": 50000,        # 500 INR
            "margin_range": (0.60, 0.75),
            "loyalty_earn": 0.10,                    # 1 pt per 10 INR
            "waiver_cost": 40,
            "waiver_budget": 250000,                 # 2,500 INR
            "cooldown_hours": 48,
        },
        TenantVertical.FASHION: {
            "aov_range": (120000, 320000),           # 1200 - 3200 INR
            "delivery_fee_range": (5000, 10000),     # 50 - 100 INR
            "free_delivery_threshold": 150000,       # 1500 INR
            "margin_range": (0.50, 0.65),
            "loyalty_earn": 0.05,
            "waiver_cost": 60,
            "waiver_budget": 350000,
            "cooldown_hours": 72,
        },
        TenantVertical.ELECTRONICS: {
            "aov_range": (250000, 850000),           # 2500 - 8500 INR
            "delivery_fee_range": (0, 15000),
            "free_delivery_threshold": 300000,
            "margin_range": (0.15, 0.30),
            "loyalty_earn": 0.02,
            "waiver_cost": 80,
            "waiver_budget": 400000,
            "cooldown_hours": 168,                   # 7 days
        },
        TenantVertical.GROCERY: {
            "aov_range": (45000, 110000),            # 450 - 1100 INR
            "delivery_fee_range": (2500, 4500),      # 25 - 45 INR
            "free_delivery_threshold": 75000,
            "margin_range": (0.20, 0.35),
            "loyalty_earn": 0.15,
            "waiver_cost": 30,
            "waiver_budget": 180000,
            "cooldown_hours": 24,
        },
        TenantVertical.D2C_SUBSCRIPTION: {
            "aov_range": (80000, 180000),
            "delivery_fee_range": (0, 5000),
            "free_delivery_threshold": 100000,
            "margin_range": (0.55, 0.70),
            "loyalty_earn": 0.10,
            "waiver_cost": 50,
            "waiver_budget": 200000,
            "cooldown_hours": 48,
        },
    }

    SIZE_VOLUMES = {
        TenantSizeTier.SMALL: 2500,
        TenantSizeTier.STANDARD: 12000,
        TenantSizeTier.STRESS: 60000,
    }

    def __init__(self, root_seed: int, frozen_domains: Optional[List[str]] = None):
        self.root_seed = root_seed
        self.frozen_domains = frozen_domains or []
        self.streams = SeedStreamManager(root_seed, self.frozen_domains)

    def sample_scenario(
        self,
        mode: RunMode = RunMode.RANDOM,
        size: TenantSizeTier = TenantSizeTier.STANDARD
    ) -> ScenarioSpec:
        """Samples a complete ScenarioSpec."""
        if mode == RunMode.EDGE:
            return self._sample_edge_scenario(size)

        tenants_rng = self.streams.get_rng("tenants")
        loyalty_rng = self.streams.get_rng("loyalty")
        traffic_rng = self.streams.get_rng("traffic")
        ads_rng = self.streams.get_rng("ads")
        faults_rng = self.streams.get_rng("faults")

        # 1. Tenants & Loyalty
        verticals = list(self.VERTICAL_DEFAULTS.keys())
        vertical_idx = int(tenants_rng.integers(0, len(verticals)))
        vertical = verticals[vertical_idx]
        v_def = self.VERTICAL_DEFAULTS[vertical]

        city_idx = int(tenants_rng.integers(0, len(self.CITIES)))
        city = self.CITIES[city_idx]

        aov = int(tenants_rng.integers(v_def["aov_range"][0], v_def["aov_range"][1]))
        delivery_fee = int(tenants_rng.integers(v_def["delivery_fee_range"][0], max(v_def["delivery_fee_range"][0] + 1, v_def["delivery_fee_range"][1])))
        free_del_threshold = v_def["free_delivery_threshold"]
        margin = round(float(tenants_rng.uniform(v_def["margin_range"][0], v_def["margin_range"][1])), 4)

        # Loyalty profile (governed exclusively by loyalty_rng for stream isolation)
        earn_options = [0.05, 0.10, 0.15, 0.02]
        earn_idx = int(loyalty_rng.integers(0, len(earn_options)))
        loyalty_earn = earn_options[earn_idx]

        waiver_costs = [30, 40, 50, 60, 80]
        cost_idx = int(loyalty_rng.integers(0, len(waiver_costs)))
        waiver_cost = waiver_costs[cost_idx]

        cooldown_options = [24, 48, 72, 168]
        cd_idx = int(loyalty_rng.integers(0, len(cooldown_options)))
        cooldown = cooldown_options[cd_idx]

        base_waiver_budget = int(loyalty_rng.integers(150000, 400000))
        budget_jitter = float(loyalty_rng.uniform(0.85, 1.15))
        daily_waiver_budget_paise = int(round(base_waiver_budget * budget_jitter))

        loyalty_profile = TenantLoyaltyProfile(
            points_earn_ratio=loyalty_earn,
            points_burn_rate_paise=100,
            delivery_fee_waiver_cost_points=waiver_cost,
            tier_thresholds={
                "Bronze": 0,
                "Silver": 500,
                "Gold": 1500,
                "Platinum": 5000,
            },
            daily_waiver_budget_paise=daily_waiver_budget_paise,
            waiver_cooldown_hours=cooldown,
            max_bonus_points_per_grant=200,
        )

        tenant = TenantSpec(
            tenant_id="tenant_sim_01",
            name=f"GrowthOS {vertical.value.upper()} Store",
            vertical=vertical,
            size_tier=size,
            city=city,
            timezone="Asia/Kolkata",
            aov_paise=aov,
            margin_pct=round(margin * 100, 2),
            delivery_fee_paise=delivery_fee,
            free_delivery_threshold_paise=free_del_threshold,
            payment_mix={
                "upi": 0.58,
                "card": 0.22,
                "wallet": 0.08,
                "cod": 0.12,
            },
            loyalty=loyalty_profile,
        )

        # 2. Traffic
        base_sessions = self.SIZE_VOLUMES.get(size, 12000)
        sessions_jitter = float(traffic_rng.uniform(0.85, 1.15))
        sessions_per_day = int(round(base_sessions * sessions_jitter))

        traffic = TrafficSpec(
            sessions_per_day=sessions_per_day,
            channel_mix={
                "direct": 0.22,
                "organic_search": 0.28,
                "paid_search": 0.32,
                "social": 0.14,
                "referral": 0.04,
            },
            new_vs_returning_ratio=round(float(traffic_rng.uniform(0.55, 0.70)), 2),
            mobile_share=round(float(traffic_rng.uniform(0.70, 0.85)), 2),
            bot_share=round(float(traffic_rng.uniform(0.01, 0.04)), 3),
            ad_blocker_share=round(float(traffic_rng.uniform(0.05, 0.12)), 3),
        )

        # 3. Ads
        num_campaigns = int(ads_rng.integers(3, 8))
        campaigns: List[CampaignSpec] = []
        total_ad_budget = 0

        platforms = [AdPlatform.GOOGLE, AdPlatform.META]
        campaign_types = ["search", "shopping", "performance", "retargeting"]

        for i in range(num_campaigns):
            platform = platforms[int(ads_rng.integers(0, 2))]
            c_type = campaign_types[int(ads_rng.integers(0, len(campaign_types)))]
            daily_budget = int(ads_rng.integers(800000, 3000000))  # 8,000 - 30,000 INR
            target_cpa = int(ads_rng.integers(18000, 45000))       # 180 - 450 INR
            true_roas = round(float(ads_rng.uniform(1.2, 3.8)), 2)
            quality_score = round(float(ads_rng.uniform(5.5, 9.5)), 1)

            total_ad_budget += daily_budget
            campaigns.append(
                CampaignSpec(
                    campaign_id=f"camp_{platform.value}_{i+1:02d}",
                    name=f"{platform.value.capitalize()} {c_type.capitalize()} Campaign {i+1}",
                    platform=platform,
                    campaign_type=c_type,
                    daily_budget_paise=daily_budget,
                    target_cpa_paise=target_cpa,
                    true_roas=true_roas,
                    quality_score=quality_score,
                )
            )

        ads = AdsSpec(
            campaigns=campaigns,
            total_daily_budget_paise=total_ad_budget,
        )

        # 4. Faults
        faults = FaultSpec(
            duplicate_rate=round(float(faults_rng.uniform(0.005, 0.020)), 3),
            late_event_rate=round(float(faults_rng.uniform(0.010, 0.035)), 3),
            sdk_loss_rate=round(float(faults_rng.uniform(0.002, 0.015)), 3),
            clock_skew_seconds=int(faults_rng.integers(0, 15)),
            adapter_timeout_after_success=bool(faults_rng.choice([True, False], p=[0.15, 0.85])),
            circuit_breaker_failures=int(faults_rng.choice([0, 1, 2], p=[0.70, 0.20, 0.10])),
            llm_429_call_index=int(faults_rng.integers(3, 8)) if faults_rng.uniform() < 0.20 else None,
        )

        # 5. Planted Effects
        planted_effects: List[PlantedEffectSpec] = []
        if faults_rng.uniform() < 0.40:
            planted_effects.append(
                PlantedEffectSpec(
                    effect_type="step_friction_spike",
                    magnitude=round(float(faults_rng.uniform(0.15, 0.35)), 2),
                    start_day=3,
                    duration_days=2,
                    target_segment="mobile_web",
                )
            )

        return ScenarioSpec(
            seed=self.root_seed,
            catalog_version="v1",
            mode=mode,
            size=size,
            tenants=[tenant],
            traffic=traffic,
            ads=ads,
            faults=faults,
            planted_effects=planted_effects,
            frozen_domains=list(self.frozen_domains),
        )

    def _sample_edge_scenario(self, size: TenantSizeTier) -> ScenarioSpec:
        """Boundary/edge case scenario with minimum/maximum values."""
        tenant = TenantSpec(
            tenant_id="tenant_edge_01",
            name="GrowthOS Edge Testing Merchant",
            vertical=TenantVertical.QSR,
            size_tier=size,
            city="Mumbai",
            timezone="Asia/Kolkata",
            aov_paise=1000,                  # Minimal 10 INR
            margin_pct=5.0,
            delivery_fee_paise=0,            # Zero delivery fee
            free_delivery_threshold_paise=0,
            payment_mix={"upi": 1.0, "card": 0.0, "wallet": 0.0, "cod": 0.0},
            loyalty=TenantLoyaltyProfile(
                points_earn_ratio=0.0,
                points_burn_rate_paise=100,
                delivery_fee_waiver_cost_points=0,
                tier_thresholds={"Bronze": 0, "Silver": 100, "Gold": 500, "Platinum": 1000},
                daily_waiver_budget_paise=10000000, # 100,000 INR
                waiver_cooldown_hours=0,
            ),
        )

        traffic = TrafficSpec(
            sessions_per_day=1,              # Single session edge case
            channel_mix={"direct": 1.0, "organic_search": 0.0, "paid_search": 0.0, "social": 0.0, "referral": 0.0},
            new_vs_returning_ratio=1.0,
            mobile_share=1.0,
            bot_share=0.0,
            ad_blocker_share=0.0,
        )

        ads = AdsSpec(
            campaigns=[
                CampaignSpec(
                    campaign_id="camp_edge_01",
                    name="Edge Single Campaign",
                    platform=AdPlatform.GOOGLE,
                    campaign_type="search",
                    daily_budget_paise=10000000,
                    target_cpa_paise=50000,
                    true_roas=1.0,
                    quality_score=5.0,
                )
            ],
            total_daily_budget_paise=10000000,
        )

        faults = FaultSpec(
            duplicate_rate=0.50,
            late_event_rate=0.50,
            sdk_loss_rate=0.20,
            clock_skew_seconds=300,
            adapter_timeout_after_success=True,
            circuit_breaker_failures=3,
        )

        return ScenarioSpec(
            seed=self.root_seed,
            catalog_version="v1",
            mode=RunMode.EDGE,
            size=size,
            tenants=[tenant],
            traffic=traffic,
            ads=ads,
            faults=faults,
            planted_effects=[],
            frozen_domains=list(self.frozen_domains),
        )
