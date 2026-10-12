# GrowthOS Planning State

## Active Context
- Focus: GrowthOS Randomized Scenario Test Environment Implementation
- Scope: Module 1 (Loyalty), Module 2 (Behavior), Module 3 (Ads), Module 4 (AI Brain)
- Last Updated: 2026-10-12
- Environment: Python 3.14 (`research/ai-module/.venv`)

## Pending Todos
- [ ] `todo-001-randomized-scenario-test-environment-plan.md`: Understand Randomized Scenario Test Environment Plan and Execute Phase-Wise Implementation with Loyalty Module Scope.

## Phase Progress: Randomized Scenario Test Environment
- [x] **Phase 0: Reproducibility Harness & Core Scenario Architecture** (COMPLETED)
  - `sim/scenario.py`: `ScenarioSpec` with `TenantLoyaltyProfile`, hash generation, Pydantic validation.
  - `sim/sampler.py`: `SeedStreamManager` with NumPy `SeedSequence` spawning 8 streams, domain freeze (`--freeze loyalty`, `--freeze ads`).
  - `sim/card.py`: ASCII Scenario Card formatter and ground truth revealer.
  - `sim/storage.py`: Run artifact persistence under `runs/DATE_SEED/`.
  - `research/growthos_cli.py`: Integrated CLI flags (`--seed`, `--mode`, `--scenario`, `--freeze`, `--size`, `--reveal`, `--sim-only`).
  - Verified with 8/8 tests in `research/ai-module/tests/test_scenario_reproducibility.py`.
- [x] **Phase 1: Catalogs & Multiverse Synthetic Generators** (COMPLETED)
  - `sim/catalog/`: `tenants.yaml`, `loyalty.yaml`, `funnel.yaml`, `ads.yaml`.
  - `sim/generators/loyalty.py`: `SimulatedCustomer`, `LoyaltyGenerator` tracking true customer points ledger, tier transitions, and delivery fee waiver actions.
  - `sim/generators/funnel.py`: `SimulatedSession`, `FunnelGenerator` simulating per-step conversions, cart values, fee waiver applications, and checkout points earn.
  - `sim/oracle/metrics.py`: `ExactMetricsOracle` computing exact counts and revenue.
  - `sim/oracle/loyalty.py`: `ExactLoyaltyOracle` verifying point conservation, non-negativity, and cooldown compliance.
  - Exit criterion met: Zero oracle mismatches across 200 random seeds in `test_phase1_generators_and_oracles.py`.
- [ ] **Phase 2: Invariant Engine & Data Fault Injection** (UP NEXT)
- [ ] **Phase 3: Closed-Loop Governance, Holdouts & Attribution**
- [ ] **Phase 4: Cross-Module Ads & Loyalty Optimization**
- [ ] **Phase 5: Chaos Simulation & Service Fault Injection**
- [ ] **Phase 6: Coverage Tracking, CLI Integration & Golden Regression Suite**

## Completed Remediations (Committed in 1e84c12)
- Pre-policy ITT holdout assignment implemented (`HoldoutEngine`).
- Unified budget ownership and cooldown validation in `PolicyEngine`.
- Verified external order ingestion feed (`MockOrderPort`, `SyntheticOrderIngester`).
- Consent verification source of truth (`ConsentStore`).
- Ephemeral HMAC session tokens for telemetry ingestion authentication.
- Exact count matching (zero tolerance) and display-rate precision in `EvidenceLinker`.
- Non-circular benchmarks with counterfactual regret scoring in `benchmark_evaluator.py`.

