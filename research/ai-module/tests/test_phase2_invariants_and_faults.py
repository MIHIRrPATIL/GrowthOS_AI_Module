"""
Phase 2 Verification Tests: Invariant Checker, Fault Injection & Golden Scenarios
GrowthOS Randomized Scenario Test Environment

Validates:
- Monotonic funnel invariant
- Loyalty non-negativity and cooldown invariants
- Tenant data isolation invariant
- Integer paise and integer points purity
- Data fault injection (duplicates, late events, telemetry drops)
- Golden regression scenarios

Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
import numpy as np
from numpy.random import default_rng

from sim.scenario import ScenarioSpec, TenantSpec, TenantVertical, TenantSizeTier, FaultSpec
from sim.sampler import ScenarioSampler
from sim.generators.loyalty import LoyaltyGenerator, SimulatedCustomer
from sim.generators.funnel import FunnelGenerator, SimulatedSession
from sim.generators.faults import FaultInjector
from sim.checks.invariants import InvariantChecker
from sim.golden import (
    make_null_week_scenario,
    make_step2_spike_scenario,
    make_bot_flood_scenario,
    make_loyalty_cooldown_boundary_scenario,
)


def test_funnel_monotonicity_invariant():
    """Verifies that InvariantChecker validates valid funnels and rejects non-monotonic counts."""
    valid_sessions = [
        SimulatedSession(
            session_id=f"s_{i}",
            tenant_id="t01",
            customer_id="c01",
            device="mobile",
            channel="direct",
            timestamp=1000.0 + i,
            steps=["view", "cart", "checkout", "payment", "order"] if i < 5 else ["view", "cart"] if i < 15 else ["view"],
            cart_total_paise=50000,
            final_amount_paid_paise=50000 if i < 5 else 0,
        )
        for i in range(20)
    ]
    ok, viols = InvariantChecker.check_funnel_monotonicity(valid_sessions)
    assert ok is True
    assert len(viols) == 0

    # Inverted broken funnel
    broken_sessions = [
        SimulatedSession(
            session_id="s_broken",
            tenant_id="t01",
            customer_id="c01",
            device="mobile",
            channel="direct",
            timestamp=1000.0,
            steps=["cart", "checkout", "order"],  # Skipped view!
            cart_total_paise=50000,
            final_amount_paid_paise=50000,
        )
    ]
    ok_b, viols_b = InvariantChecker.check_funnel_monotonicity(broken_sessions)
    assert ok_b is False
    assert any("FUNNEL_NON_MONOTONIC" in v for v in viols_b)


def test_loyalty_non_negativity_and_cooldown_invariants():
    """Verifies that negative points and cooldown violations are caught."""
    cust_valid = {
        "CUST-01": SimulatedCustomer(
            customer_id="CUST-01",
            name="Test User",
            tier="Bronze",
            opening_points=100,
            closing_points=50,
            lifetime_points_earned=100,
            lifetime_points_redeemed=50,
            waiver_timestamps=[1000.0, 1000.0 + (50 * 3600)],  # 50h gap >= 48h
        )
    }
    ok_pts, viols_pts = InvariantChecker.check_loyalty_non_negativity(cust_valid)
    assert ok_pts is True

    ok_cd, viols_cd = InvariantChecker.check_loyalty_cooldowns(cust_valid, cooldown_hours=48)
    assert ok_cd is True

    # Broken cooldown customer
    cust_broken_cd = {
        "CUST-02": SimulatedCustomer(
            customer_id="CUST-02",
            name="Broken User",
            tier="Bronze",
            opening_points=200,
            closing_points=100,
            lifetime_points_earned=200,
            lifetime_points_redeemed=100,
            waiver_timestamps=[1000.0, 1000.0 + (24 * 3600)],  # Only 24h gap (< 48h)!
        )
    }
    ok_bad_cd, viols_bad_cd = InvariantChecker.check_loyalty_cooldowns(cust_broken_cd, cooldown_hours=48)
    assert ok_bad_cd is False
    assert any("COOLDOWN_BREACH" in v for v in viols_bad_cd)


def test_loyalty_cooldown_exact_boundary():
    """Tests exact 48h cooldown boundary enforcement."""
    scen = make_loyalty_cooldown_boundary_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(12345)

    loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=10)
    cust_id = list(loyalty_gen.customers.keys())[0]
    cust = loyalty_gen.customers[cust_id]
    cust.closing_points = 500  # Ensure ample points

    t0 = 1000000.0
    # 1st waiver at t0
    ok1, rec1, msg1 = loyalty_gen.apply_delivery_fee_waiver(cust_id, 4000, timestamp=t0)
    assert ok1 is True
    assert msg1 == "SUCCESS"

    # 2nd waiver at t0 + 47 hours and 59 minutes (1 minute before cooldown ends)
    t_early = t0 + (47 * 3600) + (59 * 60)
    ok2, rec2, msg2 = loyalty_gen.apply_delivery_fee_waiver(cust_id, 4000, timestamp=t_early)
    assert ok2 is False
    assert msg2 == "COOLDOWN_ACTIVE"

    # 3rd waiver at t0 + 48 hours and 1 minute (cooldown elapsed)
    t_allowed = t0 + (48 * 3600) + (60)
    ok3, rec3, msg3 = loyalty_gen.apply_delivery_fee_waiver(cust_id, 4000, timestamp=t_allowed)
    assert ok3 is True
    assert msg3 == "SUCCESS"

    # Verify invariants pass on final state
    ok_inv, viols_inv = InvariantChecker.check_loyalty_cooldowns(loyalty_gen.customers, cooldown_hours=48)
    assert ok_inv is True
    assert len(viols_inv) == 0


def test_fault_injector_duplicates_and_idempotency():
    """Verifies that FaultInjector correctly clones events with identical idempotency keys."""
    fault_spec = FaultSpec(duplicate_rate=0.20)
    injector = FaultInjector(fault_spec=fault_spec, rng=default_rng(999))

    events = [{"event_id": f"ev_{i}", "event_type": "view", "idempotency_key": f"key_{i}"} for i in range(100)]
    output_events, dup_count = injector.inject_event_duplicates(events)

    assert dup_count > 0
    assert len(output_events) == 100 + dup_count

    # Verify duplicate event retention
    keys = [e["idempotency_key"] for e in output_events]
    assert len(set(keys)) == 100


def test_fault_injector_telemetry_drops_preserve_orders():
    """Verifies that telemetry drops never drop critical purchase orders."""
    fault_spec = FaultSpec(sdk_loss_rate=0.30)
    injector = FaultInjector(fault_spec=fault_spec, rng=default_rng(999))

    mixed_events = [
        {"event_id": f"ev_{i}", "event_type": "view" if i % 2 == 0 else "order_completed"}
        for i in range(100)
    ]
    surviving_events, dropped_count = injector.inject_telemetry_drops(mixed_events)

    assert dropped_count > 0
    # Every order must survive
    surviving_orders = [e for e in surviving_events if e["event_type"] == "order_completed"]
    assert len(surviving_orders) == 50


def test_tenant_isolation_and_currency_purity():
    """Verifies tenant isolation and currency integer purity invariants."""
    scen = make_null_week_scenario()
    tenant = scen.tenants[0]
    rng = default_rng(42)

    loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=10)
    funnel_gen = FunnelGenerator(tenant=tenant, traffic=scen.traffic, loyalty_generator=loyalty_gen, rng=rng)
    sessions = funnel_gen.generate_sessions(session_count=50)

    # Clean check
    report = InvariantChecker.check_all(
        sessions=sessions,
        customers=loyalty_gen.customers,
        loyalty_records=loyalty_gen.ledger,
        target_tenant_id=tenant.tenant_id,
        cooldown_hours=tenant.loyalty.waiver_cooldown_hours,
    )
    assert report.all_passed is True
    assert len(report.violations) == 0

    # Leak foreign tenant
    sessions[0].tenant_id = "foreign_competitor_tenant"
    bad_report = InvariantChecker.check_all(
        sessions=sessions,
        customers=loyalty_gen.customers,
        loyalty_records=loyalty_gen.ledger,
        target_tenant_id=tenant.tenant_id,
        cooldown_hours=tenant.loyalty.waiver_cooldown_hours,
    )
    assert bad_report.all_passed is False
    assert any("FOREIGN_SESSION_TENANT" in v for v in bad_report.violations)


def test_all_golden_scenarios_pass_invariants():
    """Verifies all defined golden scenarios pass comprehensive invariant checks."""
    goldens = [
        make_null_week_scenario(),
        make_step2_spike_scenario(),
        make_bot_flood_scenario(),
        make_loyalty_cooldown_boundary_scenario(),
    ]

    for scen in goldens:
        tenant = scen.tenants[0]
        rng = default_rng(scen.seed)
        loyalty_gen = LoyaltyGenerator(tenant=tenant, rng=rng, pool_size=20)
        funnel_gen = FunnelGenerator(tenant=tenant, traffic=scen.traffic, loyalty_generator=loyalty_gen, rng=rng)
        sessions = funnel_gen.generate_sessions(session_count=60)

        report = InvariantChecker.check_all(
            sessions=sessions,
            customers=loyalty_gen.customers,
            loyalty_records=loyalty_gen.ledger,
            target_tenant_id=tenant.tenant_id,
            cooldown_hours=tenant.loyalty.waiver_cooldown_hours,
        )
        assert report.all_passed is True, f"Golden scenario {scen.seed} failed: {report.violations}"
