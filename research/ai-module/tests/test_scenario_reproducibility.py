"""
Phase 0 Verification Tests: Scenario Seeding, Reproducibility & Domain Freezing
GrowthOS Randomized Scenario Test Environment

Strictly NO emojis in code, docstrings, or logs.
"""

import json
import pytest
from pathlib import Path

from sim.scenario import (
    ScenarioSpec,
    RunMode,
    TenantSizeTier,
)
from sim.sampler import ScenarioSampler, SeedStreamManager
from sim.card import render_scenario_card, render_ground_truth
from sim.storage import save_run_artifacts


def test_identical_seed_produces_identical_scenario():
    """Verifies that the same seed produces byte-identical ScenarioSpec and scenario hash."""
    seed = 48213907
    sampler1 = ScenarioSampler(root_seed=seed)
    sampler2 = ScenarioSampler(root_seed=seed)

    scen1 = sampler1.sample_scenario()
    scen2 = sampler2.sample_scenario()

    assert scen1.scenario_hash() == scen2.scenario_hash()
    assert scen1.canonical_json() == scen2.canonical_json()

    # Deep equality of all tenant and loyalty fields
    assert scen1.tenants[0].loyalty.model_dump() == scen2.tenants[0].loyalty.model_dump()
    assert scen1.ads.model_dump() == scen2.ads.model_dump()
    assert scen1.traffic.model_dump() == scen2.traffic.model_dump()


def test_different_seeds_produce_distinct_scenarios():
    """Verifies that different seeds yield different scenario hashes and parameters."""
    scen1 = ScenarioSampler(root_seed=10001).sample_scenario()
    scen2 = ScenarioSampler(root_seed=20002).sample_scenario()

    assert scen1.scenario_hash() != scen2.scenario_hash()


def test_freeze_loyalty_preserves_loyalty_profile():
    """Verifies that freezing the loyalty domain keeps loyalty parameters invariant across seeds."""
    sampler1 = ScenarioSampler(root_seed=1111, frozen_domains=["loyalty"])
    sampler2 = ScenarioSampler(root_seed=9999, frozen_domains=["loyalty"])

    scen1 = sampler1.sample_scenario()
    scen2 = sampler2.sample_scenario()

    # Loyalty profile must be identical
    loyalty1 = scen1.tenants[0].loyalty.model_dump()
    loyalty2 = scen2.tenants[0].loyalty.model_dump()
    assert loyalty1 == loyalty2

    # Unfrozen domain (e.g. ads total budget or campaigns) should vary
    # Or overall scenario hash must differ
    assert scen1.scenario_hash() != scen2.scenario_hash()


def test_freeze_ads_preserves_ads_spec():
    """Verifies that freezing the ads domain keeps campaigns invariant across seeds."""
    sampler1 = ScenarioSampler(root_seed=12345, frozen_domains=["ads"])
    sampler2 = ScenarioSampler(root_seed=67890, frozen_domains=["ads"])

    scen1 = sampler1.sample_scenario()
    scen2 = sampler2.sample_scenario()

    assert scen1.ads.model_dump() == scen2.ads.model_dump()
    assert scen1.scenario_hash() != scen2.scenario_hash()


def test_edge_mode_scenario_boundaries():
    """Verifies boundary values in edge run mode."""
    sampler = ScenarioSampler(root_seed=77777)
    scen = sampler.sample_scenario(mode=RunMode.EDGE)

    assert scen.mode == RunMode.EDGE
    assert scen.traffic.sessions_per_day == 1
    assert scen.tenants[0].aov_paise == 1000
    assert scen.faults.circuit_breaker_failures == 3
    assert scen.faults.adapter_timeout_after_success is True


def test_scenario_card_rendering():
    """Verifies scenario card ASCII output includes all required sections."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()

    card_hidden = render_scenario_card(scen, reveal_planted=False)
    assert "SCENARIO" in card_hidden
    assert "TENANT" in card_hidden
    assert "LOYALTY" in card_hidden
    assert "ADS" in card_hidden
    assert "FAULTS" in card_hidden
    assert "PLANTED" in card_hidden
    assert "hidden" in card_hidden

    card_revealed = render_scenario_card(scen, reveal_planted=True)
    assert "hidden" not in card_revealed


def test_ground_truth_rendering():
    """Verifies ground truth output renders campaign true ROAS and loyalty parameters."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    truth = render_ground_truth(scen)

    assert "GROUND TRUTH REVEAL" in truth
    assert "Hidden True ROAS" in truth
    assert "Loyalty Ground Truth" in truth


def test_save_run_artifacts(tmp_path: Path):
    """Verifies persistence of scenario.json, card.txt, and report.json."""
    scen = ScenarioSampler(root_seed=48213907).sample_scenario()
    card_text = render_scenario_card(scen)

    run_dir = save_run_artifacts(scen, card_text, base_dir=str(tmp_path))
    assert run_dir.exists()

    scenario_file = run_dir / "scenario.json"
    card_file = run_dir / "card.txt"
    report_file = run_dir / "report.json"

    assert scenario_file.exists()
    assert card_file.exists()
    assert report_file.exists()

    # Verify scenario.json round-trips into ScenarioSpec
    with open(scenario_file, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    loaded_scen = ScenarioSpec.model_validate(loaded_data)
    assert loaded_scen.scenario_hash() == scen.scenario_hash()
