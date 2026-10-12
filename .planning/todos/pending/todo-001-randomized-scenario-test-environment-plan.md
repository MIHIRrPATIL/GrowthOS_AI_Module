---
title: GrowthOS Randomized Scenario Test Environment with Loyalty Integration
area: research/ai-module/sim
created: 2026-10-12
status: pending
priority: high
tags:
  - simulation
  - randomized-testing
  - loyalty-module
  - module-1
  - module-2
  - module-3
  - module-4
  - oracles
  - invariants
  - fault-injection
  - reproducibility
---

# GrowthOS Randomized Scenario Test Environment Plan (Phased Roadmap)

## Context & Objectives
Based on `research/ai-module/docs/GrowthOS Randomized Scenario Test Environment Plan.md`, the objective is to transform `research/growthos_cli.py` into a fully seeded, reproducible, randomized scenario simulator. Every run draws a distinct combination of tenants, traffic, ad campaigns, customer loyalty profiles, and system faults, renders an initial scenario card, feeds generated events through actual ingestion paths, and strictly compares engine outputs against independent exact oracles and invariant checkers.

Crucially, **Module 1 (Loyalty & Rewards Platform)** is explicitly incorporated into the simulator scope alongside Module 2 (Behavior), Module 3 (Ads), and Module 4 (AI Growth Brain).

---

## Loyalty Module (Module 1) Integration Architecture

The test environment incorporates loyalty across every architectural tier:

### 1. Tenant Loyalty Profile
- Point earn rate: e.g. 1 loyalty point per 10 INR spent (1000 paise).
- Point burn conversion: e.g. 1 point = 1 INR discount (100 paise) or tier-based multipliers.
- Delivery fee waiver points cost: e.g. 50 points per waiver, or free for VIP tiers.
- Loyalty tier thresholds: Bronze (0 pts), Silver (500 pts), Gold (1500 pts), Platinum (5000 pts).
- Merchant loyalty spend cap: Daily maximum allowance for subsidized delivery fee waivers and bonus credits.
- Cooldown period: Minimum time window between fee waivers per customer (e.g. 48 hours or 7 days).

### 2. Customer Loyalty State
- `loyalty_tier`: Bronze / Silver / Gold / Platinum.
- `loyalty_points_balance`: Non-negative integer points ledger.
- `lifetime_points_earned` and `lifetime_points_redeemed`.
- `last_waiver_timestamp`: Cooldown tracking timestamp.
- `consent_purposes`: Consent store verified for `"retention"` and `"marketing"`.

### 3. Simulator Loyalty Events & True Ledger
- `loyalty.points_earned`: Emitted upon verified order checkout.
- `loyalty.points_redeemed`: Emitted when points are exchanged for discounts or waivers.
- `loyalty.waiver_applied`: Emitted when `waive_delivery_fee` executes.
- `loyalty.bonus_granted`: Emitted when retention credits are awarded.
- `loyalty.tier_upgraded`: Emitted when milestone point boundaries are crossed.

### 4. Loyalty Port & Adapter Contracts
- `LoyaltyPort` integration (`ports/outbound.py`):
  - `waive_delivery_fee(customer_id, fee_amount, points_deducted, idempotency_key)`
  - `grant_bonus_points(customer_id, points, reason, idempotency_key)`
  - `issue_discount_coupon(customer_id, coupon_code, discount_amount, idempotency_key)`
- `HttpLoyaltyAdapter` (`adapters/loyalty_waivers_adapter.py`):
  - HMAC-SHA256 authenticated request signing.
  - Idempotency key tracking.
  - Circuit breaker trips after N consecutive failures.
  - Timeout and fault injection handling.

### 5. Loyalty Oracles & Invariants
- **Point Conservation Oracle**: $OpeningBalance + \sum Earned - \sum Redeemed == ClosingBalance$.
- **Non-Negative Balance Invariant**: $\forall c: Balance(c) \ge 0$.
- **Eligibility Invariant**: Points redeemed $\le$ current point balance.
- **Cooldown Invariant**: Zero duplicate fee waivers within merchant cooldown window.
- **Spend Cap Invariant**: Daily total waiver disbursements $\le$ merchant daily budget cap.

---

## Phased Implementation Plan

```text
research/ai-module/sim/
  catalog/        versioned YAML: distributions, categories, sources, loyalty
  scenario.py     ScenarioSpec model, hash calculation, validation
  sampler.py      hierarchical seeded sampler with NumPy SeedSequence
  generators/
    tenants.py    vertical profiles, sizes, loyalty configurations
    loyalty.py    customer points ledgers, tier allocations, earn/burn events
    traffic.py    session counts, diurnal curves, bots, ad-blockers
    funnel.py     step transitions, rage clicks, cart values, dropoffs
    customers.py  repeat rates, identity aliases, consent records
    orders.py     verified multi-channel order feeds, refunds, cancellations
    ads.py        campaigns, platforms, clicks, spend, true ROAS
    faults.py     data faults, network drops, circuit breaker trips, LLM errors
  oracle/
    metrics.py    independent exact counters for funnel, revenue, and AOV
    loyalty.py    independent points accounting, waiver ledger, and cooldown validator
    ads.py        independent campaign spend, CAC, and ROAS validator
  checks/
    invariants.py monotonic funnels, non-negative points, zero cross-tenant leakage
    statistical.py false-flag calibration, 95% lift interval coverage
  card.py         scenario card printing and ground-truth reveal
  coverage.py     all-pairs categorical tracker and numerical range coverage
```

### Phase 0: Reproducibility Harness & Core Scenario Architecture
- **Objective**: Establish single-seed deterministic replay with NumPy `SeedSequence` spawning.
- **Tasks**:
  1. Create `ScenarioSpec` schema in `research/ai-module/sim/scenario.py` including `TenantLoyaltyProfile` and `LoyaltyPolicySpec`.
  2. Implement `SeedSequence` multi-stream hierarchy in `research/ai-module/sim/sampler.py` with separate streams for `tenants`, `loyalty`, `traffic`, `ads`, `customers`, `faults`, `queries`, `llm`.
  3. Implement CLI flags in `research/growthos_cli.py`: `--seed`, `--mode`, `--scenario`, `--freeze`, `--size`, `--reveal`.
  4. Implement scenario card renderer in `research/ai-module/sim/card.py` displaying tenant, loyalty, traffic, ads, policy, and fault parameters.
  5. Implement run directory persistence under `runs/DATE_SEED/` saving `scenario.json`, `card.txt`, `events.jsonl.gz`, and `report.json`.
- **Exit Criterion**: Same seed generates byte-identical scenario spec, event stream hash, and run configuration across independent executions.

### Phase 1: Catalogs & Multiverse Synthetic Generators
- **Objective**: Construct realistic parametric distributions and baseline exact metric oracles.
- **Tasks**:
  1. Build versioned catalog YAML files under `research/ai-module/sim/catalog/` (`tenants.yaml`, `loyalty.yaml`, `funnel.yaml`, `ads.yaml`).
  2. Implement `TenantGenerator` and `LoyaltyGenerator` drawing vertical profiles (QSR, Fashion, Electronics, Grocery) and loyalty rules.
  3. Implement `TrafficGenerator` and `FunnelGenerator` for session paths, device types, payment failure rates, and cart values.
  4. Implement `MetricOracle` and `LoyaltyOracle` to compute exact ground-truth values directly from generator ledgers.
  5. Test baseline null scenarios with zero planted effects.
- **Exit Criterion**: Zero oracle mismatches across 200 randomly seeded runs on standard funnel, revenue, and loyalty point totals.

### Phase 2: Invariant Engine & Data Fault Injection
- **Objective**: Enforce structural system invariants and verify data fault resilience.
- **Tasks**:
  1. Implement `InvariantChecker` (`sim/checks/invariants.py`):
     - Funnel monotonicity: $Sessions \ge Carts \ge Orders$.
     - Loyalty point non-negativity: $PointsBalance \ge 0$.
     - Cooldown compliance: $\Delta t(waivers) \ge Cooldown$.
     - Tenant data isolation: Zero cross-tenant data in state or output.
     - Integer paise and integer points end-to-end.
     - Replay idempotency: Duplicate event ingestion causes zero state delta.
  2. Implement data fault injector (`sim/generators/faults.py`):
     - Duplicate events, out-of-order events, late-arriving events.
     - Clock skew and IST midnight boundary transitions.
     - Telemetry drop rates and missing consent fields.
  3. Create golden regression scenarios (`null_week`, `step2_spike`, `bot_flood`, `loyalty_cooldown_boundary`).
- **Exit Criterion**: 100% of invariants pass; all injected data faults are either cleanly tolerated or rejected as specified.

### Phase 3: Closed-Loop Governance, Holdouts & Attribution
- **Objective**: Simulate customer identity, consent verification, approval delays, and 24-hour attribution.
- **Tasks**:
  1. Ingest simulated events via real ports and verified external order feeds (`MockOrderPort`).
  2. Implement pre-policy Intent-To-Treat (ITT) holdout split for loyalty delivery fee waivers and retention triggers.
  3. Integrate `ConsentStore` checks for retention purposes before executing Module 1 actions.
  4. Simulate approval workflow latencies (instant, hours, rejected, expired).
  5. Plant controlled conversion and retention lift, and verify `AttributionClosingWorker` lift estimation.
- **Exit Criterion**: 95% confidence interval for estimated treatment lift covers the true planted lift in ~95% of 200 seeded runs.

### Phase 4: Cross-Module Budget & Co-Optimization
- **Objective**: Prevent budget oscillation and enforce unified growth spend caps between Module 1 and Module 3.
- **Tasks**:
  1. Implement unified 24h spend ledger tracking ad spend (Module 3) and subsidized fee waivers (Module 1 / Module 4).
  2. Implement `PolicyEngine` joint budget checks ensuring total growth spend never exceeds merchant daily limit.
  3. Implement Ad Campaign Optimizer oracle verifying budget shifts move from underperforming to high-ROAS campaigns.
  4. Validate 1-click rollback restoring previous ad budget allocations and fee waiver policy parameters.
- **Exit Criterion**: Zero budget cap violations across 100% of runs; budget rebalancing shifts toward higher-ROAS campaigns at verified rate.

### Phase 5: Service Fault Injection, Chaos Simulation & Resilience
- **Objective**: Validate error handling against service outages, circuit breaker trips, and LLM anomalies.
- **Tasks**:
  1. Inject `HttpLoyaltyAdapter` faults: HTTP 500/503 errors, socket timeouts.
  2. Inject "Timeout after success" fault in loyalty fee waiver execution to test idempotency key deduplication.
  3. Validate circuit breaker tripping after 3 consecutive failures and half-open reset behavior.
  4. Inject LLM faults: HTTP 429 rate limits, malformed JSON, and hallucinated numbers, verifying evidence linker rejection.
  5. Execute concurrent approval requests for identical customers to verify race condition protection.
- **Exit Criterion**: Zero duplicate fee waivers under retries; circuit breakers recover properly; hostile LLM outputs fail-closed.

### Phase 6: Coverage Tracking, CLI Integration & Golden Regression Suite
- **Objective**: Provide comprehensive test coverage reporting, full CLI integration, and nightly regression tooling.
- **Tasks**:
  1. Implement `CoverageTracker` (`sim/coverage.py`) tracking all categorical values and pairwise combinations using all-pairs generator.
  2. Wire simulator CLI commands into `research/growthos_cli.py`:
     - `python growthos_cli.py --seed <N>`
     - `python growthos_cli.py --mode [random|edge|coverage|golden|stress]`
     - `python growthos_cli.py --freeze [loyalty|ads|traffic]`
     - `python growthos_cli.py --scenario <path> --reveal`
  3. Build automated regression seed shrinker minimizing failing scenarios to minimal reproduction cases.
  4. Establish test runner executing 20 seeds on fast verification and 200 seeds in nightly regression.
- **Exit Criterion**: At least 95% of defined dimension values and pairwise combinations exercised; full CLI execution passing without manual setup.
