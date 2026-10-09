"""
Unit Test Suite for Heuristic Scoring Engine
GrowthOS Module 4: AI Growth Brain

Validates transparent, auditable, deterministic scoring baselines:
1. Purchase Propensity (S_propensity in [0.0, 1.0])
2. Customer Churn Risk (S_churn in [0.0, 1.0])
3. Customer Lifetime Value (V_CLTV and incentive allowances)

Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
import math
from engines.heuristic_scoring import (
    HeuristicWeightsConfig,
    PropensityScoreResult,
    ChurnScoreResult,
    CLTVScoreResult,
    score_purchase_propensity,
    score_churn_risk,
    score_customer_cltv,
    DEFAULT_HEURISTIC_CONFIG,
)


# ==============================================================================
# Propensity Scoring Tests
# ==============================================================================

def test_purchase_propensity_organic_buyer_suppression():
    """High intent session with large cart at checkout review should be flagged for suppression."""
    result = score_purchase_propensity(
        cart_subtotal_paise=500000,   # INR 5,000 (>= AOV)
        tenant_aov_paise=400000,      # INR 4,000
        product_views_count=3,
        cart_adds_count=2,            # ratio = 1.5 (sweet-spot 1.0)
        funnel_stage="checkout_review_step_2", # 0.90
        idle_minutes=2.0              # < 15m, decay = 1.0
    )
    assert isinstance(result, PropensityScoreResult)
    assert result.score >= 0.85
    assert result.eligibility == "SUPPRESS_ORGANIC_BUYER"
    assert result.decay_component == 1.0
    assert result.stage_component == 0.90
    assert result.velocity_component == 1.0


def test_purchase_propensity_low_intent_suppression():
    """Window shopping session with tiny cart, heavy views, and long idle time should be suppressed."""
    result = score_purchase_propensity(
        cart_subtotal_paise=20000,    # INR 200 (low)
        tenant_aov_paise=500000,      # INR 5,000
        product_views_count=50,
        cart_adds_count=1,            # ratio = 50 (window shopper)
        funnel_stage="homepage",      # 0.20
        idle_minutes=180.0            # 3 hours idle
    )
    assert result.score <= 0.15
    assert result.eligibility == "SUPPRESS_LOW_INTENT"
    assert result.decay_component < 0.10


def test_purchase_propensity_eligible_for_incentive():
    """Moderate deliberation with cart abandonment in active window qualifies for incentive."""
    result = score_purchase_propensity(
        cart_subtotal_paise=250000,   # INR 2,500 (approx 0.6x AOV)
        tenant_aov_paise=400000,      # INR 4,000
        product_views_count=6,
        cart_adds_count=2,            # ratio = 3.0 (sweet spot)
        funnel_stage="cart_drawer",   # 0.40
        idle_minutes=20.0             # 20m (just entering idle decay)
    )
    assert 0.15 < result.score < 0.85
    assert result.eligibility == "ELIGIBLE_FOR_INCENTIVE"


def test_purchase_propensity_idle_decay_curve():
    """Decay score must be 1.0 at or below threshold and exponentially decrease thereafter."""
    cfg = HeuristicWeightsConfig()
    
    # At 15 min (threshold)
    r_15 = score_purchase_propensity(
        cart_subtotal_paise=100000,
        tenant_aov_paise=100000,
        product_views_count=2,
        cart_adds_count=1,
        funnel_stage="cart",
        idle_minutes=15.0,
        config=cfg
    )
    assert r_15.decay_component == 1.0

    # At 60 min (15 + 45 min halflife) -> exp(-1) ~= 0.3679
    r_60 = score_purchase_propensity(
        cart_subtotal_paise=100000,
        tenant_aov_paise=100000,
        product_views_count=2,
        cart_adds_count=1,
        funnel_stage="cart",
        idle_minutes=60.0,
        config=cfg
    )
    expected_decay = round(math.exp(-45.0 / 45.0), 4)
    assert abs(r_60.decay_component - expected_decay) < 0.001
    assert r_60.score < r_15.score


def test_purchase_propensity_zero_aov_safety():
    """Handles zero or negative AOV without division by zero error."""
    result = score_purchase_propensity(
        cart_subtotal_paise=50000,
        tenant_aov_paise=0,
        product_views_count=1,
        cart_adds_count=1,
        funnel_stage="cart",
        idle_minutes=5.0
    )
    assert 0.0 <= result.score <= 1.0


# ==============================================================================
# Churn Risk Scoring Tests
# ==============================================================================

def test_churn_risk_cold_start_new_customer():
    """Customer with fewer than 2 lifetime orders receives neutral 0.50 cold-start baseline."""
    result = score_churn_risk(
        days_since_last_order=10.0,
        historical_interpurchase_days=14.0,
        lifetime_orders_count=1,       # Cold-start trigger
        sessions_count_last_30d=5,
        sessions_count_prior_60d=10,
        friction_events_count_last_14d=0
    )
    assert isinstance(result, ChurnScoreResult)
    assert result.score == 0.50
    assert result.risk_tier == "NEUTRAL"
    assert result.is_cold_start is True
    assert result.recency_component is None


def test_churn_risk_cold_start_none_recency():
    """Customer with None days_since_last_order receives neutral cold-start baseline."""
    result = score_churn_risk(
        days_since_last_order=None,
        historical_interpurchase_days=None,
        lifetime_orders_count=5,
        sessions_count_last_30d=2,
        sessions_count_prior_60d=4,
        friction_events_count_last_14d=1
    )
    assert result.score == 0.50
    assert result.risk_tier == "NEUTRAL"
    assert result.is_cold_start is True


def test_churn_risk_active_healthy_customer():
    """Frequent buyer with recent purchase and steady visits should have LOW churn risk."""
    result = score_churn_risk(
        days_since_last_order=3.0,
        historical_interpurchase_days=14.0,
        lifetime_orders_count=8,
        sessions_count_last_30d=12,    # rate = 0.40/day
        sessions_count_prior_60d=20,   # rate = 0.33/day (growing!)
        friction_events_count_last_14d=0
    )
    assert result.is_cold_start is False
    assert result.score < 0.35
    assert result.risk_tier == "LOW"
    assert result.frequency_component == 0.0  # Stable/expanding engagement


def test_churn_risk_dormant_high_friction_customer():
    """Customer past their typical cadence with session drop-off and friction has HIGH churn risk."""
    result = score_churn_risk(
        days_since_last_order=75.0,    # severe dormancy
        historical_interpurchase_days=20.0, # cadence 20d
        lifetime_orders_count=6,
        sessions_count_last_30d=1,     # sharp collapse
        sessions_count_prior_60d=30,
        friction_events_count_last_14d=3 # 3 friction errors
    )
    assert result.is_cold_start is False
    assert result.score > 0.70
    assert result.risk_tier == "HIGH"
    assert result.friction_component == 1.0


# ==============================================================================
# CLTV Scoring & Allowance Tests
# ==============================================================================

def test_cltv_vip_customer_allowance():
    """High-value customer categorized as VIP gets allowance capped at INR 100."""
    result = score_customer_cltv(
        historical_aov_paise=1000000,  # INR 10,000
        annual_orders_cadence=6.0,     # Gross = INR 60,000 (6,000,000 paise)
        category_margin_pct=0.35,      # Margin = 2,100,000 paise
        churn_score=0.20               # discount factor = 0.80 -> net margin = 1,680,000 paise (>= p90)
    )
    assert isinstance(result, CLTVScoreResult)
    assert result.customer_tier == "VIP"
    assert result.projected_net_margin_paise >= 1000000
    # 10% of order margin: 10,000 * 0.35 * 0.10 = INR 350 (35,000 paise)
    # Capped at INR 100 (10,000 paise)
    assert result.max_incentive_allowance_paise == 10000


def test_cltv_core_customer_allowance():
    """Core customer gets allowance capped at INR 50."""
    result = score_customer_cltv(
        historical_aov_paise=250000,   # INR 2,500
        annual_orders_cadence=4.0,     # Gross = INR 10,000
        category_margin_pct=0.40,      # 40% margin
        churn_score=0.25               # net margin ~ 300,000 paise (core)
    )
    assert result.customer_tier == "CORE"
    # 5% of order margin: 2,500 * 0.40 * 0.05 = INR 50 (5,000 paise)
    assert result.max_incentive_allowance_paise == 5000


def test_cltv_low_tier_zero_allowance():
    """Low tier customer must receive 0 paise monetary incentive allowance."""
    result = score_customer_cltv(
        historical_aov_paise=50000,    # INR 500
        annual_orders_cadence=1.0,     # Gross = INR 500
        category_margin_pct=0.20,
        churn_score=0.80
    )
    assert result.customer_tier == "LOW"
    assert result.max_incentive_allowance_paise == 0
