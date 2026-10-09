"""
Heuristic Scoring Engine
GrowthOS Module 4: AI Growth Brain

Provides transparent, auditable, deterministic scoring baselines:
1. Purchase Propensity ($S_propensity in [0.0, 1.0]$):
   Weighted function of cart value vs catalog AOV, browsing deliberation velocity,
   funnel stage reached, and inactivity decay after 15m.
   Informs incentive eligibility:
   - >= 0.85: SUPPRESS_ORGANIC_BUYER (avoids fee waiver cannibalization)
   - <= 0.15: SUPPRESS_LOW_INTENT (preserves message budget)
   - 0.15 to 0.85: ELIGIBLE_FOR_INCENTIVE

2. Customer Churn Risk ($S_churn in [0.0, 1.0]$):
   Function of order recency relative to personal cadence, 30-day vs 60-day daily session frequency,
   and friction events (payment gateway stalls, rage clicks, checkout drop-offs).
   Cold-start rule: Customers with < 2 lifetime orders receive neutral baseline (0.50).

3. Customer Lifetime Value ($V_CLTV$):
   12-month net revenue projection based on historical AOV, annual order cadence,
   category margins, and churn risk. Computes tenant-relative tiers (VIP, Core, Low)
   and maximum allowable incentive budget caps (never loosens merchant policy caps).

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any, Optional
import math
from pydantic import BaseModel, Field, ConfigDict


# ==============================================================================
# Versioned Configuration Model
# ==============================================================================

class HeuristicWeightsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "v1.0.0"
    
    # Propensity Weights (Must sum to 1.0)
    propensity_cart_weight: float = 0.30
    propensity_velocity_weight: float = 0.25
    propensity_stage_weight: float = 0.30
    propensity_decay_weight: float = 0.15
    
    # Inactivity Decay Parameters
    idle_decay_threshold_mins: float = 15.0
    idle_decay_halflife_mins: float = 45.0
    
    # Churn Weights (Must sum to 1.0)
    churn_recency_weight: float = 0.40
    churn_frequency_weight: float = 0.30
    churn_friction_weight: float = 0.30
    
    # Actionability Thresholds
    organic_buyer_threshold: float = 0.85
    low_intent_threshold: float = 0.15


DEFAULT_HEURISTIC_CONFIG = HeuristicWeightsConfig()


# ==============================================================================
# Propensity Result Model
# ==============================================================================

class PropensityScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., ge=0.0, le=1.0)
    eligibility: str = Field(..., description="SUPPRESS_ORGANIC_BUYER | SUPPRESS_LOW_INTENT | ELIGIBLE_FOR_INCENTIVE")
    cart_norm_component: float
    velocity_component: float
    stage_component: float
    decay_component: float
    config_version: str


def score_purchase_propensity(
    cart_subtotal_paise: int,
    tenant_aov_paise: int,
    product_views_count: int,
    cart_adds_count: int,
    funnel_stage: str,
    idle_minutes: float,
    config: Optional[HeuristicWeightsConfig] = None
) -> PropensityScoreResult:
    """
    Computes real-time purchase propensity for an active or abandoned session.
    """
    cfg = config or DEFAULT_HEURISTIC_CONFIG

    # 1. Cart Value Component (normalized against merchant average order value)
    safe_aov = max(100, tenant_aov_paise)
    cart_norm = min(1.0, max(0.0, cart_subtotal_paise / safe_aov))

    # 2. Session Velocity Component (browsing deliberation ratio)
    # Ratio = views per cart addition
    safe_adds = max(1, cart_adds_count)
    view_ratio = product_views_count / safe_adds
    
    if view_ratio < 1.0:
        # Fast intent: added directly without prior views
        velocity_score = 0.90
    elif 1.0 <= view_ratio <= 4.0:
        # High consideration sweet-spot: evaluated 1-4 items per addition
        velocity_score = 1.00
    elif 4.0 < view_ratio <= 10.0:
        # Moderate hesitation
        velocity_score = 0.70
    else:
        # High browse ratio (>10 views per add): window shopping / low purchase conviction
        velocity_score = max(0.15, 1.0 - ((view_ratio - 4.0) * 0.08))

    # 3. Funnel Progression Stage Component
    stage_lower = funnel_stage.lower().strip()
    if any(k in stage_lower for k in ("payment", "step_2", "checkout_step_2", "review")):
        stage_score = 0.90
    elif any(k in stage_lower for k in ("address", "shipping", "step_1", "checkout_step_1", "checkout")):
        stage_score = 0.70
    elif any(k in stage_lower for k in ("cart", "cart_drawer")):
        stage_score = 0.40
    else:
        stage_score = 0.20

    # 4. Inactivity Decay Component
    # Flat 1.0 before threshold (15m), exponential decay thereafter
    if idle_minutes <= cfg.idle_decay_threshold_mins:
        decay_score = 1.0
    else:
        excess_idle = idle_minutes - cfg.idle_decay_threshold_mins
        decay_score = math.exp(-excess_idle / cfg.idle_decay_halflife_mins)
    decay_score = max(0.01, min(1.0, decay_score))

    # Weighted Sum
    raw_score = (
        cfg.propensity_cart_weight * cart_norm +
        cfg.propensity_velocity_weight * velocity_score +
        cfg.propensity_stage_weight * stage_score +
        cfg.propensity_decay_weight * decay_score
    )
    final_score = round(max(0.0, min(1.0, raw_score)), 4)

    # Determine Outreach Eligibility
    if final_score >= cfg.organic_buyer_threshold:
        eligibility = "SUPPRESS_ORGANIC_BUYER"
    elif final_score <= cfg.low_intent_threshold:
        eligibility = "SUPPRESS_LOW_INTENT"
    else:
        eligibility = "ELIGIBLE_FOR_INCENTIVE"

    return PropensityScoreResult(
        score=final_score,
        eligibility=eligibility,
        cart_norm_component=round(cart_norm, 4),
        velocity_component=round(velocity_score, 4),
        stage_component=round(stage_score, 4),
        decay_component=round(decay_score, 4),
        config_version=cfg.version
    )


# ==============================================================================
# Churn Risk Result Model
# ==============================================================================

class ChurnScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str = Field(..., description="LOW | MODERATE | HIGH | NEUTRAL")
    is_cold_start: bool
    recency_component: Optional[float] = None
    frequency_component: Optional[float] = None
    friction_component: Optional[float] = None
    config_version: str


def score_churn_risk(
    days_since_last_order: Optional[float],
    historical_interpurchase_days: Optional[float],
    lifetime_orders_count: int,
    sessions_count_last_30d: int,
    sessions_count_prior_60d: int,
    friction_events_count_last_14d: int,
    config: Optional[HeuristicWeightsConfig] = None
) -> ChurnScoreResult:
    """
    Computes customer churn risk score.
    Cold-start rule: Customers with < 2 lifetime orders receive neutral baseline (0.50).
    """
    cfg = config or DEFAULT_HEURISTIC_CONFIG

    # Cold-start check
    if lifetime_orders_count < 2 or days_since_last_order is None:
        return ChurnScoreResult(
            score=0.50,
            risk_tier="NEUTRAL",
            is_cold_start=True,
            recency_component=None,
            frequency_component=None,
            friction_component=None,
            config_version=cfg.version
        )

    # 1. Recency Penalty (days since last order relative to expected cadence)
    expected_cadence = max(7.0, historical_interpurchase_days or 30.0)
    # Recency ratio: 1.5x expected cadence represents severe dormancy
    recency_ratio = days_since_last_order / (1.5 * expected_cadence)
    recency_component = min(1.0, max(0.0, recency_ratio))

    # 2. Frequency Trajectory Component (Daily rate comparison: last 30d vs prior 60d)
    daily_rate_30d = sessions_count_last_30d / 30.0
    daily_rate_60d = sessions_count_prior_60d / 60.0

    if daily_rate_60d > 0.0:
        if daily_rate_30d >= daily_rate_60d:
            freq_component = 0.0  # Stable or expanding engagement
        else:
            freq_component = min(1.0, 1.0 - (daily_rate_30d / daily_rate_60d))
    else:
        # Zero baseline activity in prior 60 days
        freq_component = 0.40

    # 3. Friction History Component (rage clicks, drop-offs, payment errors in last 14d)
    friction_component = min(1.0, max(0.0, friction_events_count_last_14d / 3.0))

    # Weighted Sum
    raw_score = (
        cfg.churn_recency_weight * recency_component +
        cfg.churn_frequency_weight * freq_component +
        cfg.churn_friction_weight * friction_component
    )
    final_score = round(max(0.0, min(1.0, raw_score)), 4)

    if final_score < 0.35:
        tier = "LOW"
    elif final_score <= 0.70:
        tier = "MODERATE"
    else:
        tier = "HIGH"

    return ChurnScoreResult(
        score=final_score,
        risk_tier=tier,
        is_cold_start=False,
        recency_component=round(recency_component, 4),
        frequency_component=round(freq_component, 4),
        friction_component=round(friction_component, 4),
        config_version=cfg.version
    )


# ==============================================================================
# Customer Lifetime Value (CLTV) Result Model
# ==============================================================================

class CLTVScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projected_annual_value_paise: int
    projected_net_margin_paise: int
    customer_tier: str = Field(..., description="VIP | CORE | LOW")
    max_incentive_allowance_paise: int
    churn_discount_factor: float
    category_margin_pct: float


def score_customer_cltv(
    historical_aov_paise: int,
    annual_orders_cadence: float,
    category_margin_pct: float = 0.30,
    churn_score: float = 0.50,
    tenant_cltv_distribution: Optional[Dict[str, int]] = None
) -> CLTVScoreResult:
    """
    Computes 12-month projected customer lifetime value and maximum incentive allowance.
    Enforces that CLTV can tighten merchant policy spend limits, but never loosen them.
    """
    safe_aov = max(0, historical_aov_paise)
    safe_cadence = max(0.1, annual_orders_cadence)
    safe_margin = max(0.05, min(0.95, category_margin_pct))

    # Churn discount factor: 1 - min(0.90, churn_score)
    discount_factor = round(1.0 - min(0.90, max(0.0, churn_score)), 4)

    # Annual Projected Revenue & Net Margin
    annual_gross_paise = int(safe_aov * safe_cadence)
    annual_net_margin_paise = int(annual_gross_paise * safe_margin * discount_factor)

    # Tenant-Relative Percentiles (defaults based on standard ecommerce baselines in paise)
    dist = tenant_cltv_distribution or {
        "p40": 300000,    # INR 3,000 net margin threshold
        "p90": 1000000    # INR 10,000 net margin threshold
    }

    p40 = dist.get("p40", 300000)
    p90 = dist.get("p90", 1000000)

    if annual_net_margin_paise >= p90:
        tier = "VIP"
        # VIP: Up to 10% of order margin allowable as dynamic fee waiver (capped at INR 100 / 10,000 paise)
        max_incentive = min(10000, int(safe_aov * safe_margin * 0.10))
    elif annual_net_margin_paise >= p40:
        tier = "CORE"
        # Core: Up to 5% of order margin (capped at INR 50 / 5,000 paise)
        max_incentive = min(5000, int(safe_aov * safe_margin * 0.05))
    else:
        tier = "LOW"
        # Low: 0 paise incentive allowance (strict rules apply; outreach restricted to non-monetary recovery)
        max_incentive = 0

    return CLTVScoreResult(
        projected_annual_value_paise=annual_gross_paise,
        projected_net_margin_paise=annual_net_margin_paise,
        customer_tier=tier,
        max_incentive_allowance_paise=max_incentive,
        churn_discount_factor=discount_factor,
        category_margin_pct=safe_margin
    )
