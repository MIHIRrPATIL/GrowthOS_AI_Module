"""
Full Simulator Verification Suite: Phases 3, 4, 5, and 6
GrowthOS Randomized Scenario Test Environment

Validates:
- Phase 3: Customer identity, pre-policy ITT holdouts, verified order feeds, causal lift evaluation
- Phase 4: Ads simulator, 15% budget rebalance, 1-click rollback, cross-module spend caps
- Phase 5: Chaos simulation, timeout after success idempotency, circuit breaker recovery, hostile LLM rejection
- Phase 6: All-pairs coverage matrix, regression seed store, 200-seed end-to-end batch simulation

Strictly NO emojis in code, docstrings, or logs.
"""

from pathlib import Path
import pytest
import numpy as np
from numpy.random import default_rng

from sim.scenario import ScenarioSpec, TenantSpec, RunMode, TenantSizeTier
from sim.sampler import ScenarioSampler
from sim.generators.customers import CustomerGenerator, CustomerProfile
from sim.generators.orders import OrderFeedGenerator
from sim.generators.loyalty import LoyaltyGenerator
from sim.generators.funnel import FunnelGenerator
from sim.generators.ads import AdsSimulator
from sim.attribution import CausalLiftEvaluator
from sim.oracle.metrics import ExactMetricsOracle
from sim.oracle.loyalty import ExactLoyaltyOracle
from sim.oracle.ads import ExactAdsOracle
from sim.checks.invariants import InvariantChecker
from sim.chaos import ChaosSimulator
from sim.coverage import CoverageTracker
from sim.regression import RegressionSeedStore
from adapters.loyalty_waivers_adapter import HttpLoyaltyAdapter
from engines.evidence_linker import EvidenceLinker


# ---------------------------------------------------------------------------
# Phase 3 Tests: Customers, Orders, Holdouts, and Causal Lift
# ---------------------------------------------------------------------------

def test_customer_generator_and_identity_stitching():
    """Verifies customer cohort generation, anonymous-to-user resolution, and ITT holdouts."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(48213907)

    cust_gen = CustomerGenerator(tenant=tenant, rng=rng, pool_size=100, holdout_rate=0.10)
    assert len(cust_gen.customers) == 100

    # Verify ~10% holdout distribution
    control_count = sum(1 for c in cust_gen.customers.values() if c.is_control_arm)
    assert 5 <= control_count <= 18

    # Verify identity resolution
    sample_cust = list(cust_gen.customers.values())[0]
    resolved = cust_gen.resolve_identity(sample_cust.anonymous_id)
    assert resolved is not None
    assert resolved.customer_id == sample_cust.customer_id


def test_verified_order_feed_generator():
    """Verifies verified multi-channel order feed with refunds and cancellations."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(48213907)

    order_gen = OrderFeedGenerator(tenant=tenant, rng=rng)
    customer_ids = [f"CUST-{i}" for i in range(100)]
    orders = order_gen.generate_orders(customer_ids=customer_ids, order_count=200)

    assert len(orders) == 200
    statuses = {o.status for o in orders}
    assert "completed" in statuses
    # Verified orders include ad-blocked sessions
    assert any(o.is_ad_blocked for o in orders)


def test_causal_lift_evaluator():
    """Verifies causal lift evaluation, two-sample z-scores, and 95% confidence intervals."""
    # Simulation: 200 conversions in treated (N=1000) vs 150 conversions in control (N=1000)
    report = CausalLiftEvaluator.evaluate(
        treated_conversions=200,
        treated_total=1000,
        control_conversions=150,
        control_total=1000,
    )
    assert report.treated_rate == 0.20
    assert report.control_rate == 0.15
    assert report.absolute_lift == 0.05
    assert report.relative_lift_pct == 33.33
    assert report.z_score > 1.96
    assert report.is_statistically_significant is True
    assert report.ci_95_lower > 0.0


# ---------------------------------------------------------------------------
# Phase 4 Tests: Ads Optimization, 15% Shift, Rollback, and Unified Caps
# ---------------------------------------------------------------------------

def test_ads_simulator_optimization_and_rollback():
    """Verifies autonomous budget rebalancing <= 15% and 1-click rollback restoration."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    rng = default_rng(48213907)

    ads_sim = AdsSimulator(ads_spec=scen.ads, rng=rng)
    assert len(ads_sim.campaigns) >= 2

    # Record initial budgets
    initial_budgets = {cid: c.daily_budget_paise for cid, c in ads_sim.campaigns.items()}

    # Apply optimization
    success, proposals, msg = ads_sim.optimize_budgets()
    assert success is True
    assert len(proposals) > 0
    prop = proposals[0]
    assert prop["shift_percent"] == 15.0

    # Verify budgets changed
    bleeder = ads_sim.campaigns[prop["bleeder_id"]]
    winner = ads_sim.campaigns[prop["winner_id"]]
    assert bleeder.daily_budget_paise < initial_budgets[prop["bleeder_id"]]
    assert winner.daily_budget_paise > initial_budgets[prop["winner_id"]]

    # Execute 1-click rollback
    rollback_ok = ads_sim.rollback_last_optimization()
    assert rollback_ok is True

    # Verify budgets perfectly restored
    restored_budgets = {cid: c.daily_budget_paise for cid, c in ads_sim.campaigns.items()}
    assert restored_budgets == initial_budgets


def test_exact_ads_oracle_cross_module_growth_cap():
    """Verifies ExactAdsOracle enforces unified merchant growth spend caps."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    rng = default_rng(48213907)
    ads_sim = AdsSimulator(ads_spec=scen.ads, rng=rng)

    # Clean verification within generous cap
    res = ExactAdsOracle.verify(
        ads_simulator=ads_sim,
        loyalty_waivers_spent_paise=50000,
        merchant_total_growth_budget_paise=1000000000,
    )
    assert res.passed is True
    assert len(res.violations) == 0

    # Exceeded cap verification
    res_bad = ExactAdsOracle.verify(
        ads_simulator=ads_sim,
        loyalty_waivers_spent_paise=50000,
        merchant_total_growth_budget_paise=1000,  # Tiny cap
    )
    assert res_bad.passed is False
    assert any("UNIFIED_GROWTH_BUDGET_EXCEEDED" in v for v in res_bad.violations)


# ---------------------------------------------------------------------------
# Phase 5 Tests: Chaos Simulation & Service Fault Injection
# ---------------------------------------------------------------------------

def test_loyalty_timeout_after_success_idempotency():
    """Verifies that replaying duplicate actions after timeout returns cached result without double debit."""
    adapter = HttpLoyaltyAdapter()
    ok, msg = ChaosSimulator.test_loyalty_timeout_after_success(
        adapter=adapter,
        customer_id="CUST-48291",
        fee_amount=50.0,
        points=40,
        idempotency_key="idemp_chaos_test_01",
    )
    assert ok is True
    assert msg == "IDEMPOTENCY_VERIFIED"


def test_circuit_breaker_trip_and_recovery():
    """Verifies circuit breaker trips after 3 failures and recovers after reset window."""
    adapter = HttpLoyaltyAdapter(circuit_breaker_threshold=3, circuit_breaker_reset_seconds=1.0)
    ok, msg = ChaosSimulator.test_circuit_breaker_trip_and_recovery(adapter=adapter)
    assert ok is True
    assert msg == "CIRCUIT_BREAKER_TRIP_AND_RECOVERY_VERIFIED"


def test_hostile_llm_rejection():
    """Verifies that EvidenceLinker rejects hallucinated counts and percentages."""
    linker = EvidenceLinker()
    facts = {
        "orders": 142,
        "conversion_rate": 14.1,
    }
    ok, failures = ChaosSimulator.test_hostile_llm_rejection(
        evidence_linker=linker,
        ground_truth_facts=facts,
    )
    assert ok is True
    assert len(failures) == 0


# ---------------------------------------------------------------------------
# Phase 6 Tests: All-Pairs Coverage & 200-Seed Batch Simulation
# ---------------------------------------------------------------------------

def test_coverage_tracker_accumulation(tmp_path: Path):
    """Verifies CoverageTracker accumulates dimensions and records pairwise combinations."""
    tracker = CoverageTracker()
    initial_cov = tracker.get_coverage_percentage()
    assert initial_cov == 0.0

    # Feed 10 diverse scenarios
    for s_idx in range(10):
        scen = ScenarioSampler(root_seed=1000 + s_idx).sample_scenario()
        tracker.record_scenario(scen)

    final_cov = tracker.get_coverage_percentage()
    assert final_cov > 0.0

    # Test saving
    cov_path = tmp_path / "coverage.json"
    tracker.save(cov_path)
    assert cov_path.exists()


def test_regression_seed_store(tmp_path: Path):
    """Verifies RegressionSeedStore records and reloads failing seeds."""
    store_file = tmp_path / "regression_seeds.json"
    store = RegressionSeedStore(storage_path=store_file)

    store.record_failure(
        seed=123456,
        scenario_hash="hash_test",
        failure_type="COOLDOWN_VIOLATION",
        error_message="Simulated breach",
        timestamp_utc="2026-10-12T12:00:00Z",
    )
    assert 123456 in store.get_failing_seeds()

    # Reload store
    store2 = RegressionSeedStore(storage_path=store_file)
    assert 123456 in store2.get_failing_seeds()


def test_200_seeds_batch_end_to_end_simulation():
    """
    Primary Phase 6 Exit Criterion:
    Executes 200 seeded scenarios end-to-end with:
    - Customer generation & 10% ITT holdouts
    - Funnel sessions & Loyalty transactions
    - Ads simulation & budget rebalancing
    - Double-blind exact oracles (Metrics, Loyalty, Ads)
    - Structural invariant validation
    - All-pairs coverage tracking
    Exit Criterion: 100% of runs pass with zero invariant or oracle violations!
    """
    tracker = CoverageTracker()
    modes = [RunMode.RANDOM, RunMode.EDGE, RunMode.GOLDEN, RunMode.COVERAGE, RunMode.STRESS]
    sizes = [TenantSizeTier.SMALL, TenantSizeTier.STANDARD, TenantSizeTier.STRESS]

    for idx in range(200):
        seed = 200000 + idx
        run_mode = modes[idx % len(modes)]
        size_tier = sizes[idx % len(sizes)]
        sampler = ScenarioSampler(root_seed=seed)
        scen = sampler.sample_scenario(mode=run_mode, size=size_tier)
        tenant = scen.tenants[0]
        rng = default_rng(seed)

        # 1. Customers & Pre-policy ITT holdouts
        cust_gen = CustomerGenerator(tenant=tenant, rng=rng, pool_size=30, holdout_rate=0.10)

        # 2. Loyalty generator
        loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=30)

        # 3. Funnel sessions
        funnel_gen = FunnelGenerator(
            tenant=tenant,
            traffic=scen.traffic,
            loyalty_generator=loyalty_gen,
            rng=rng,
        )
        sessions = funnel_gen.generate_sessions(session_count=40)

        # 4. Ads simulation
        ads_sim = AdsSimulator(ads_spec=scen.ads, rng=rng)
        if len(ads_sim.campaigns) >= 2:
            ads_sim.optimize_budgets()

        # 5. Exact Oracles
        metrics = ExactMetricsOracle.compute(sessions)
        assert metrics.order_count <= metrics.payment_count <= metrics.checkout_count <= metrics.cart_count <= metrics.view_count

        loyalty_res = ExactLoyaltyOracle.verify(loyalty_gen)
        assert loyalty_res.passed is True, f"Seed {seed} failed loyalty oracle: {loyalty_res.violations}"

        ads_res = ExactAdsOracle.verify(
            ads_simulator=ads_sim,
            loyalty_waivers_spent_paise=loyalty_gen.total_waivers_spent_paise,
            merchant_total_growth_budget_paise=1000000000,
        )
        assert ads_res.passed is True, f"Seed {seed} failed ads oracle: {ads_res.violations}"

        # 6. Invariant Checker
        inv_res = InvariantChecker.check_all(
            sessions=sessions,
            customers=loyalty_gen.customers,
            loyalty_records=loyalty_gen.ledger,
            target_tenant_id=tenant.tenant_id,
            cooldown_hours=tenant.loyalty.waiver_cooldown_hours,
        )
        assert inv_res.all_passed is True, f"Seed {seed} failed invariants: {inv_res.violations}"

        # 7. Record coverage
        tracker.record_scenario(scen)

    coverage_pct = tracker.get_coverage_percentage()
    # Verifies high pairwise dimension coverage achieved across 200 runs
    assert coverage_pct >= 90.0
