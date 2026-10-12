"""
Golden Regression Scenarios
GrowthOS Randomized Scenario Test Environment

Named fixed scenarios with deterministic expected behaviors:
1. null_week: Zero faults, zero planted anomalies. Tests false-positive baseline.
2. step2_spike: High friction spike on cart step.
3. bot_flood: 35% automated bot traffic flood.
4. loyalty_cooldown_boundary: Exact boundary testing of 48h loyalty waiver cooldown.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any
from sim.scenario import (
    ScenarioSpec,
    RunMode,
    TenantSizeTier,
    TenantSpec,
    TenantVertical,
    TenantLoyaltyProfile,
    TrafficSpec,
    AdsSpec,
    CampaignSpec,
    AdPlatform,
    FaultSpec,
    PlantedEffectSpec,
)


def make_null_week_scenario() -> ScenarioSpec:
    """Baseline clean scenario with zero faults and zero planted anomalies."""
    tenant = TenantSpec(
        tenant_id="tenant_golden_null",
        name="Golden Clean Store",
        vertical=TenantVertical.QSR,
        size_tier=TenantSizeTier.STANDARD,
        city="Mumbai",
        timezone="Asia/Kolkata",
        aov_paise=55000,
        margin_pct=65.0,
        delivery_fee_paise=4000,
        free_delivery_threshold_paise=50000,
        payment_mix={"upi": 0.60, "card": 0.25, "wallet": 0.05, "cod": 0.10},
        loyalty=TenantLoyaltyProfile(
            points_earn_ratio=0.10,
            points_burn_rate_paise=100,
            delivery_fee_waiver_cost_points=40,
            daily_waiver_budget_paise=250000,
            waiver_cooldown_hours=48,
        ),
    )
    return ScenarioSpec(
        seed=100001,
        catalog_version="v1",
        mode=RunMode.GOLDEN,
        size=TenantSizeTier.STANDARD,
        tenants=[tenant],
        traffic=TrafficSpec(sessions_per_day=10000, bot_share=0.01),
        ads=AdsSpec(campaigns=[], total_daily_budget_paise=0),
        faults=FaultSpec(),
        planted_effects=[],
    )


def make_step2_spike_scenario() -> ScenarioSpec:
    """Planted checkout friction spike."""
    scen = make_null_week_scenario()
    scen.seed = 100002
    scen.planted_effects = [
        PlantedEffectSpec(
            effect_type="step_friction_spike",
            magnitude=0.35,
            start_day=2,
            duration_days=3,
            target_segment="mobile_web",
        )
    ]
    return scen


def make_bot_flood_scenario() -> ScenarioSpec:
    """High bot flood scenario."""
    scen = make_null_week_scenario()
    scen.seed = 100003
    scen.traffic.bot_share = 0.35
    return scen


def make_loyalty_cooldown_boundary_scenario() -> ScenarioSpec:
    """Scenario tailored for exact cooldown boundary validation."""
    scen = make_null_week_scenario()
    scen.seed = 100004
    scen.tenants[0].loyalty.waiver_cooldown_hours = 48
    scen.tenants[0].loyalty.delivery_fee_waiver_cost_points = 50
    return scen
