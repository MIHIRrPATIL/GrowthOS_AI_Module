# GrowthOS Randomized Scenario Test Environment: Plan

Oct 12, 2026 · @Mihir Patil

Turn growthos\_cli.py into a seeded scenario simulator: every run draws a new mix of tenants, traffic, ads and faults, prints it, and is checked against known ground truth.

## Review of the idea

The core idea is right, but random runs only find real bugs when each one can be replayed exactly and has something independent to be checked against.

| Your idea | Verdict | Change |
| --- | --- | --- |
| Pick a random scenario on every run | Keep | Seed it and print the seed first, so any failure can be replayed exactly |
| A huge pool for every variable | Change | Use parametric distributions for numbers and short lists for categories; variety comes from combinations, not pool size |
| Pull data from the internet | Partly | Use public datasets to calibrate distributions and for optional replay; they have no ground truth and rarely match Indian QSR traffic |
| Randomize everything at once | Change | One seed stream per component plus freeze flags, so a failure points to one cause |
| Print the data used | Keep | Print a scenario card at the start and the hidden ground truth at the end; save both as JSON |
| Uniform random values | Change | Draw from realistic distributions, with a separate edge-case mode for extremes |
| Run and look at the output | Change | Every run needs an independent oracle and invariant checks; otherwise random runs only find crashes |

## Which earlier findings are prototype-level

About half of my earlier findings change what a prototype test can prove; the rest are production hardening you can defer.

| Finding | Level | Why it matters now |
| --- | --- | --- |
| Holdout assigned only in the autonomous path and after policy gates | Prototype design flaw | Treated and control arms differ before treatment, so lift is biased, and Approval mode produces no experiment data |
| Module 3 and Module 4 both shift budgets | Architecture | Two optimizers with different attribution can oscillate; one must own budget decisions |
| Orders and revenue come only from SDK events | Architecture | Ad-blocked users, refunds and cancellations are invisible; the simulator needs a separate order feed to test this |
| Consent has no source of truth | Architecture | The policy engine checks a store that nothing populates or updates on withdrawal |
| Browser-side event signing | Architecture | A secret in client JavaScript cannot authenticate events; decide the trust model before building more ingestion |
| Z-test baseline and multiple comparisons | Prototype correctness | A median baseline is not a proportion, and many metrics per run produce false flags |
| 0.5% tolerance in EvidenceLinker for counts | Prototype bug | Counts must match exactly; rates must match at the displayed precision |
| Benchmark labels derived from the rules they judge | Prototype test validity | Rules score near 100% by construction; labels need outcomes or independent judgment |
| Conflicting attribution windows (30 days and 24 hours) | Prototype design | Metrics and lift disagree across modules until one definition is chosen |
| Loyalty module absent | Scope | Decide whether retention is in the MVP; the simulator needs to know |

Defer to production: merchant login and approval UI, Postgres migrations, observability and alerting, queue and scheduler hardening, secrets management, CI and deployment, load tests, retention and erasure workflows, legal review, documentation and the merchant pilot.

## What the simulator is

The simulator samples a ScenarioSpec from versioned catalogs, generates events with a hidden ground-truth ledger, runs the real engines, and compares their output with independent oracles.

```text
research/ai-module/sim/
  catalog/        versioned YAML: distributions, categories, sources
  scenario.py     ScenarioSpec model and scenario hash
  sampler.py      seeded, hierarchical sampler
  generators/     tenants, traffic, funnel, customers, orders, ads, faults, queries
  oracle/         independent expected-value calculators
  loaders/        public datasets to catalog fits or replay
  checks/         invariants and statistical checks
  coverage.py     tracks which values and pairs have been exercised
  card.py         scenario card and ground-truth printing
```

1. Sample a ScenarioSpec from the seed and the chosen mode.
2. Generate tenants, customers, ad campaigns, events and faults, recording the true ledger of every session.
3. Print the scenario card.
4. Feed the events through the real ingestion path, not a shortcut into the database.
5. Run the selected CLI option against the real engines.
6. Compare results with the oracles and run the invariant checks.
7. Print the ground-truth reveal and save the run folder.

The oracle must be written with different logic from the engines, for example by counting the generator ledger directly. If both derive from the same code, a shared bug passes silently.

## Seeds and reproducibility

Every run must be replayable from one number.

- Derive one random stream per component (tenants, traffic, ads, customers, faults, queries, llm) from the root seed with numpy SeedSequence spawning, so changing one component does not shift the others.
- Scenario hash = hash of the catalog version plus the ScenarioSpec JSON; print both.
- Inject the clock and never use wall time; avoid Python hash() and unordered iteration.
- Test that the same seed yields a byte-identical event stream.
- Save every run under runs/DATE\_SEED/ as scenario.json, events.jsonl.gz, card.txt and report.json, using synthetic data only.
- A failing run is saved automatically as a regression seed; shrink it by cutting tenants, days and volume until the failure is minimal.

## What varies

Every variable below is drawn per run; categories come from short lists and numbers from distributions fitted per vertical.

| Domain | Variables | How drawn |
| --- | --- | --- |
| Tenant | Vertical (QSR, fashion, electronics, grocery, D2C subscription, travel, lending, SaaS), size tier, city and timezone, AOV, margin, delivery fee, free-delivery threshold, catalog size, payment mix (UPI, card, wallet, COD), COD share, language | Vertical profile plus log-normal draws |
| Traffic | Sessions per day, weekday and hour shape, sale and festival spikes, new vs returning, device, browser, channel mix, bot share, ad-blocker share | Negative-binomial counts times shape curves |
| Funnel | Per-step conversion by segment, payment failure rate, friction events such as rage clicks, cart value | Beta draws per vertical, multiplied by segment effects |
| Planted effects | Step friction spike, payment outage, conversion lift or drop, traffic quality shift, fee or price change; each with size, start day, duration and segment; also none | Explicit magnitudes; a null scenario is a normal draw |
| Customers | Repeat rate, inter-purchase gap, value tier, churn, logged-in share, multi-device and shared devices, consent by purpose, phone and email present, WhatsApp opt-in | Gamma and log-normal draws; Bernoulli flags |
| Identity | Anonymous to login timing, cookie clearing, merges that should and should not happen | Fixed patterns mixed in by seed |
| Ads | Number of campaigns (1 to 50), platform, type (search, shopping, performance, brand, retargeting), daily budget in paise, CPC, CTR, quality score, ad fatigue, conversion lag, target CPA, bleeder campaigns, missing UTM or click ID rate, invalid traffic, budget exhausted early, disapproval, API errors | Each campaign gets a hidden true ROAS; spend, clicks, conversions, CAC and ROAS then emerge from simulation instead of being inputs |
| Merchant policy | Caps, cooldown, execution mode, autonomy allowlist, kill switch, approval delay (instant, hours, never), thresholds, holdout share | Presets with jitter |
| Data faults | Duplicates, late events, out-of-order events, clock skew, missing fields, malformed payloads, SDK loss rate, tracking gaps, IST midnight boundary events | Each rate drawn from none, low or high |
| Service faults | LLM 429, timeout, malformed JSON, wrong numbers, adapter timeout after success, duplicate webhook, expired token, concurrent approvals | Scheduled by seed |
| NL queries | Paraphrases, typos, Hinglish, ambiguous metrics, out-of-scope questions, prompt-injection text inside product names or UTM values | Frozen labeled pool, human reviewed |

Budgets and volumes use log-uniform draws within a size tier, because uniform draws from rupees 1 to 1,000,000 produce unrealistic merchants almost every time.

## Using public and online data

Public datasets calibrate the distributions and give realistic timing and long tails, but they cannot replace the generator because they carry no ground truth. As far as I know the sources below exist; check current availability and licenses before relying on them.

| Source | Use |
| --- | --- |
| REES46 multi-category store behavior, Retailrocket events (view, cart, purchase streams) | Fit session length, funnel rates, hour-of-day shape and long-tail behavior; optional replay after mapping to EventEnvelope |
| Olist Brazilian e-commerce, UCI Online Retail | Order value, basket size and repeat-purchase patterns |
| Criteo uplift, Hillstrom email test (treatment and control) | Test the holdout and uplift estimators against real treatment effects |
| Faker with the en\_IN locale | Names, cities and addresses for synthetic customers |

Rules for external data:

- Download once into data/external/ with a manifest (source, license, date, checksum); never fetch during a run.
- Store the fitted parameters in the catalog with the dataset version they came from.
- Mark assumptions with no public source (UPI, COD, IST, festivals, Indian ad costs) as assumptions in the catalog, and replace them with real shadow-mode numbers later.

## Run modes and coverage

Random runs alone miss corners, so use several modes.

| Mode | Draws | Purpose |
| --- | --- | --- |
| random (default) | Realistic distributions for every dimension | Exploration with a new scenario each run |
| edge | Boundary values: zero traffic, one session, all anonymous, no consent, maximum budget, single campaign | Corners that realistic draws rarely reach |
| coverage | The least-covered values and pairs from earlier runs | Fill gaps in what has been tested |
| golden | Named fixed scenarios: null week, step 2 spike, bot flood, late events, budget bleeder | Regression tests with known expected results |
| stress | Large volumes, many tenants and campaigns | Performance and memory |

Size tiers (tune later): small is 1 tenant and about 2,000 sessions, standard is 3 tenants and about 50,000 sessions, stress is 10 tenants and about 1,000,000 events.

For coverage, keep runs/coverage.json counting every dimension value and every pair of categorical values seen so far. Use an all-pairs generator such as allpairspy so every pair appears at least once across a batch, and report coverage as a percentage.

## Interface and scenario card

The CLI gains a few flags; every option in the menu runs against the same scenario.

```text
python growthos_cli.py                          random scenario, standard size
python growthos_cli.py --seed 48213907          exact replay
python growthos_cli.py --mode edge
python growthos_cli.py --scenario runs/2026-10-12_48213907/scenario.json
python growthos_cli.py --freeze ads --seed 7    keep ads, vary the rest
python growthos_cli.py --size small --llm replay --reveal
```

At the start of every run, print a scenario card (numbers below are illustrative):

```text
SCENARIO  seed=48213907  hash=9c1f2a7e  catalog=v3  mode=random  size=standard  llm=replay
TENANT    t01  qsr_delivery  Mumbai (IST)  ~4,200 sessions/day  AOV 612  delivery fee 49  COD 38%
          traffic: mobile 78%  paid 41%  new 63%  bots 3%  ad-block 9%
WINDOWS   current 2026-10-05..10-12   prior 2026-09-28..10-05   (IST day boundaries)
ADS       7 campaigns  total budget 85,000/day  google 4, meta 3  target CPA 220
POLICY    mode=approval  fee waiver cap 150  cooldown 48h  holdout 10%  approval delay median 3h
FAULTS    duplicates 1.2%  late events 2.0%  llm_429 at call 4  adapter_timeout_after_success x1
PLANTED   hidden (shown at the end, or now with --reveal)
```

Each option then prints the slice it uses (for example the metric windows for diagnostics, or the campaign table for ads optimization) with the pool and catalog entry each value came from. At the end it prints the planted effects, the oracle comparison, the invariant results and the run folder path. The CLI exits non-zero on any mismatch.

## Oracles and checks

**Exact oracles (every run)**

- The generator ledger knows the true path of every session; an independent counter computes every metric, window and dimension slice, and the engine must match exactly
- Spend, clicks, conversions, CAC and ROAS from the ads simulator are recomputed independently from campaign ledgers

**Invariants (every run)**

- Funnel steps are monotonic, and 0 <= numerator <= denominator
- Re-ingesting the same events changes nothing, and adjacent windows add up to the combined window
- A late event never changes a result computed at an earlier as\_of
- No output row or ledger entry crosses tenants
- Money is integer paise end to end
- The policy engine never passes a plan beyond a cap, cooldown or consent rule; the daily spend ledger never exceeds its cap
- Nothing dispatches without a ledger record; the hash chain verifies; reruns create no duplicate plans; only legal state transitions occur
- Budget shifts stay within the daily limit and rollback restores the exact prior state; the kill switch stops all dispatch
- Every narrative claim traces to a computed fact

**Statistical checks (nightly, 200 or more seeds)**

- False-flag rate on null scenarios stays at or below the target
- Detection recall for planted effects, reported by effect size and traffic volume (a power curve)
- Propensity heuristic AUC and calibration against the generator's true conversion probability
- The holdout estimator recovers the planted lift, and its 95% intervals cover the true value about 95% of the time
- The optimizer moves budget toward truly better campaigns
- NL router accuracy on the frozen labeled pool, with confidence intervals

## Faults, crashes and concurrency

Fault injection is where most production bugs hide, so seed it deliberately.

- Choose crash points by seed (between reserve and call, between call and ledger write, mid-approval), kill and restart the process, and verify recovery with no duplicate or lost action.
- Run parallel approvals and parallel plans for the same customer on real threads.
- Replay duplicate and out-of-order webhooks, and an adapter that succeeds but times out.
- Feed malformed, oversized and wrong-tenant payloads.

## LLM handling in random runs

Random runs must not burn quota or flake on a provider.

- Modes: mock (deterministic), replay (recorded responses keyed by prompt hash), live (capped by --llm-budget N calls).
- CI uses replay; live runs are a small smoke test only.
- A hostile mock emits wrong numbers, inverted direction and causal claims, one defect per sentence, to test the evidence gate separately for each.
- Log exactly what fields are sent to any provider.

## Build phases

| Phase | Build | Exit criterion |
| --- | --- | --- |
| 0 | ScenarioSpec, seeding, scenario card, JSON save, --seed and --scenario | Same seed gives an identical event hash |
| 1 | Catalogs, tenant, traffic and funnel generators, exact metric oracle, null scenario | Zero oracle mismatches over 200 seeds |
| 2 | Invariant checker, data-fault injection, golden scenarios | Every invariant passes; each fault is caught or tolerated as specified |
| 3 | Customers, identity, consent, order feed, policy, approval and attribution simulation with a planted lift | Lift interval coverage near 95% over 200 seeds |
| 4 | Ads simulator and optimizer oracles | Caps respected in 100% of runs; budget moves to better campaigns at an agreed rate |
| 5 | Public-data calibration and replay; NL query pool | Fitted parameters stored; router accuracy measured |
| 6 | Coverage tracker, regression seed store, CI (20 seeds per change, 200 nightly), crash and concurrency tests | At least 95% of dimension values exercised after 200 runs |

## Risks

| Risk | Mitigation |
| --- | --- |
| The simulator shares your assumptions, so the system passes by construction | Independent oracle logic, calibration from public data and later shadow-mode data, planted surprises |
| Failures cannot be reproduced | Seeds, saved scenarios, automatic regression seeds |
| Too many random dimensions to find a cause | Per-component streams and --freeze flags |
| Combinatorial explosion | All-pairs selection and coverage mode |
| Long runtimes | Size tiers; small by default on every change |
| LLM flakiness and cost | Replay cassettes, call budgets |
| Privacy | Synthetic data only; never load real customer data into runs |
