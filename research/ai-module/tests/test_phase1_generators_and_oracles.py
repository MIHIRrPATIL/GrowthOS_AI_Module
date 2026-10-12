"""
Phase 1 Verification Tests: Multiverse Generators & Exact Oracles
GrowthOS Randomized Scenario Test Environment

Validates:
- Catalog YAML files
- Synthetic Loyalty & Funnel Generators
- ExactMetricsOracle & ExactLoyaltyOracle
- Exit Criterion: 200 seeds null oracle verification with zero mismatches

Strictly NO emojis in code, docstrings, or logs.
"""

from pathlib import Path
import yaml
import pytest
import numpy as np
from numpy.random import default_rng

from sim.scenario import ScenarioSpec, TenantSpec, TenantVertical, TenantSizeTier
from sim.sampler import ScenarioSampler
from sim.generators.loyalty import LoyaltyGenerator
from sim.generators.funnel import FunnelGenerator
from sim.oracle.metrics import ExactMetricsOracle
from sim.oracle.loyalty import ExactLoyaltyOracle


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_catalog_yaml_loading():
    """Verifies that all Phase 1 catalog YAML files parse cleanly with valid parameters."""
    catalog_dir = WORKSPACE_ROOT / "sim" / "catalog"
    assert catalog_dir.exists()

    tenants_yaml = catalog_dir / "tenants.yaml"
    loyalty_yaml = catalog_dir / "loyalty.yaml"
    funnel_yaml = catalog_dir / "funnel.yaml"
    ads_yaml = catalog_dir / "ads.yaml"

    for path in [tenants_yaml, loyalty_yaml, funnel_yaml, ads_yaml]:
        assert path.exists(), f"Missing catalog file {path.name}"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert "version" in data
            assert data["version"] == "v1"


def test_loyalty_generator_cohort_initialization():
    """Verifies that LoyaltyGenerator initializes realistic cohorts and point brackets."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(48213907)

    loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=50)
    assert len(loyalty_gen.customers) == 50

    tiers = {c.tier.value for c in loyalty_gen.customers.values()}
    assert "Bronze" in tiers or "Silver" in tiers or "Gold" in tiers

    # Verify all opening balances >= 0
    assert all(c.opening_points >= 0 for c in loyalty_gen.customers.values())
    assert all(c.closing_points == c.opening_points for c in loyalty_gen.customers.values())


def test_loyalty_oracle_exact_verification():
    """Verifies that ExactLoyaltyOracle validates point conservation and cooldowns."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(48213907)

    loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=40)
    cust_id = list(loyalty_gen.customers.keys())[0]

    # Award points on order
    earn_rec = loyalty_gen.earn_points_on_order(
        customer_id=cust_id,
        order_subtotal_paise=50000,
        timestamp=1000.0,
    )
    assert earn_rec is not None
    assert earn_rec.points > 0

    # Apply delivery fee waiver
    success, waiver_rec, reason = loyalty_gen.apply_delivery_fee_waiver(
        customer_id=cust_id,
        fee_amount_paise=tenant.delivery_fee_paise,
        timestamp=2000.0,
    )
    if success:
        assert waiver_rec is not None
        assert waiver_rec.points > 0

    # Run ExactLoyaltyOracle
    result = ExactLoyaltyOracle.verify(loyalty_gen)
    assert result.passed is True
    assert len(result.violations) == 0


def test_funnel_generator_and_monotonic_invariants():
    """Verifies FunnelGenerator produces monotonic funnels and valid revenue."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(48213907)

    loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=60)
    funnel_gen = FunnelGenerator(
        tenant=tenant,
        traffic=scen.traffic,
        loyalty_generator=loyalty_gen,
        rng=rng,
    )

    sessions = funnel_gen.generate_sessions(session_count=300)
    assert len(sessions) == 300

    metrics = ExactMetricsOracle.compute(sessions)
    assert metrics.total_sessions == 300
    assert metrics.order_count <= metrics.payment_count <= metrics.checkout_count <= metrics.cart_count <= metrics.view_count
    assert metrics.gross_revenue_paise >= 0

    # Check loyalty oracle on final state
    loyalty_result = ExactLoyaltyOracle.verify(loyalty_gen)
    assert loyalty_result.passed is True
    assert len(loyalty_result.violations) == 0


def test_200_seeds_null_oracle_verification():
    """
    Phase 1 Exit Criterion:
    Zero oracle mismatches over 200 seeds on null simulation scenarios.
    """
    for seed_idx in range(200):
        seed = 100000 + seed_idx
        scen = ScenarioSampler(root_seed=seed).sample_scenario()
        tenant = scen.tenants[0]
        rng = default_rng(seed)

        loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=25)
        funnel_gen = FunnelGenerator(
            tenant=tenant,
            traffic=scen.traffic,
            loyalty_generator=loyalty_gen,
            rng=rng,
        )

        sessions = funnel_gen.generate_sessions(session_count=50)
        metrics = ExactMetricsOracle.compute(sessions)

        # Monotonicity checks
        assert metrics.order_count <= metrics.payment_count <= metrics.checkout_count <= metrics.cart_count <= metrics.view_count

        # Exact Loyalty Oracle check
        loyalty_result = ExactLoyaltyOracle.verify(loyalty_gen)
        assert loyalty_result.passed is True, f"Seed {seed} failed loyalty oracle: {loyalty_result.violations}"
