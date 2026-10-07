# GrowthOS Module 4: AI Growth Brain, Architecture and Plan

Oct 2, 2026 · @Mihir Patil

## Purpose, scope and assumptions

Module 4 is the decision layer of GrowthOS: it turns events from the other modules into explained, policy-checked actions for merchants, and every number it shows comes from deterministic code, not from the LLM.

**Module 4 owns**

- Normalizing incoming events and resolving anonymous visitors into customers
- Exact metrics with sample sizes, and period-over-period anomaly digests
- Churn, lifetime value and purchase-propensity scoring
- Natural-language answers to merchant questions, grounded in evidence
- Proposing actions, checking them against hard policy limits, gating them by execution mode, dispatching them, and auditing everything

**Module 4 does not own**

- Loyalty rules and the points or rewards ledger (Module 1)
- Event capture in the browser or app (Module 2)
- Ad platform connections and campaign management (Module 3)

**Working assumptions**

1. The internals of Modules 1 to 3 are unknown, so Module 4 defines the contracts it needs. The other owners either adapt to them or write adapters; Module 4 never imports their schemas.
2. Deterministic computation and LLM narration stay strictly separate: the LLM reads computed signals and never calculates metrics.
3. The product is Web2-first with on-chain features optional, matching the ChainLoyalty decision.
4. If Module 2 builds on PostHog, the inbound event shape follows PostHog's (event name, distinct id, properties, timestamp). To be confirmed.
5. Proposed stack: Python, FastAPI, Pydantic v2, Postgres, with the LLM and decision providers behind interfaces.

## Architecture overview

Module 4 is layered so that exact numbers are computed first, models only read those results, and a policy gate controls every outbound action.

&#91;embedded content: Module 4 architecture · 3 layers, inbound and outbound ports\]

Events enter through inbound ports; the deterministic layer produces metrics and flags; the reasoning layer chooses and explains from those results; the control layer decides what may leave through the outbound ports.

**Proposed deployment shape**

- One FastAPI service for the ports, plus a background worker for digests, scoring and dispatch
- Postgres for events, identities, results and the ledger; a queue for ingestion and outbound retries
- NetworkX for local graph work, and a Neo4j adapter only if graph queries prove necessary
- LLM and decision providers behind interfaces, with offline fallbacks so tests need no API keys

## How it works end to end

An event becomes an action in six steps, and a failed policy check stops it before any mode is consulted.

&#91;embedded content: event to action flow · 1 policy check, 3 execution modes\]

Events are normalized and measured before any model is involved. A proposal that breaks a limit or lacks customer consent is rejected and logged; otherwise the merchant's mode decides whether it is shown, queued for approval, or run automatically.

1. **Ingest:** the event is validated, deduplicated by event\_id, and linked to a customer or anonymous visitor
2. **Compute:** exact metrics, period comparisons, absence checks and scores are calculated in plain code
3. **Propose:** the decision layer picks from the fixed action menu, and the LLM writes the explanation with evidence links
4. **Check:** the policy gate tests discount, budget and contact limits plus consent; failures stop here
5. **Gate:** Manual shows the suggestion, Approval queues it for a named human, Autonomous runs it only if confidence clears that action's threshold
6. **Act and learn:** the action goes out through the port with an idempotency key, and later the outcome is measured and fed back into evaluation

## Domain model and contracts

Module 4 owns its own schemas and publishes them as versioned contracts; other modules connect through ports, and an anti-corruption layer translates their formats so nothing foreign enters the core.

**Inbound event (EventEnvelope)**

| Field | Purpose |
| --- | --- |
| event\_id | Idempotency key, so replays never double-count |
| schema\_version | Lets the contract evolve without breaking senders |
| tenant\_id | The merchant; every query and rule is scoped by it |
| source\_module | Which module emitted it |
| event\_name, occurred\_at, received\_at | What happened, and when (event time vs arrival time) |
| anonymous\_id, customer\_id, session\_id | Identity hooks; customer\_id is empty until the visitor is known |
| properties | Free-form payload, validated per event name |
| consent | Whether the customer allows profiling and outreach |

**Core entities**

| Entity | Role |
| --- | --- |
| Customer, AnonymousDevice | Identified person and pre-login visitor, merged on signup, login or checkout |
| Session, Order, Product | Behavior and commerce facts |
| Campaign | Where the customer came from |
| FrictionPoint, BehavioralSignal | Detected problem spots and patterns (rage clicks, idle cart, repeated errors) |
| MetricResult, DigestFlag | Computed outputs, each with sample size and timestamp |
| ActionPlan, PolicyRule, AuditRecord | Proposed actions, hard limits, and the ledger entry |

Identity merges are stored as reversible links, not overwrites, because a wrong merge must be undoable.

**Ports**

| Port | Direction | What crosses it |
| --- | --- | --- |
| Event ingestion | In | Batches of EventEnvelope |
| Context | In | Merchant settings, product catalog, vertical template, policy limits |
| Merchant query | In | Natural-language question plus tenant and time range |
| Approval | In | Human approve or reject of a pending ActionPlan |
| LoyaltyPort | Out | Waive fee, grant points, issue discount code |
| BehaviorPort | Out | Request denser telemetry, register a UI friction bug |
| AdsPort | Out | Sync a segment, shift budget between campaigns |
| NotificationPort | Out | WhatsApp or email recovery links |
| DecisionPort, LLMPort | Internal | Scoring and reasoning providers (see the decision layer) |

Each outbound port ships with a mock adapter that records what would have been sent, so Module 4 runs and tests with no other module present.

**Contract rules**

1. Write contracts first as JSON Schema or OpenAPI, then generate the Pydantic models from them.
2. Version every contract; accept the previous version for a stated period.
3. Run contract tests against each adapter, so a changed partner schema fails a test and not production.
4. Share the inbound contracts with the other module owners early; they are the ask, not a final answer.

## Features by component

Eight components make up Module 4; the first four are deterministic and the model-driven ones sit on top of them.

**1. Metrics engine**

- Exact conversion rates, step drop-off, cart abandonment and cohort totals, defined by a template per business vertical
- Every result carries sample\_size, prior\_sample\_size and an ISO timestamp, and refuses to report when the sample is too small

**2. Digest and anomaly engine**

- Compares week over week and month over month; a change beyond the threshold (default 10%) becomes a flag ranked Low, Medium or High
- Absence detection for non-events, for example a high-value cart idle for over 60 minutes with no checkout
- Severity comes from configured thresholds, never from the LLM

**3. Identity resolution and customer graph**

- Merges anonymous sessions into customers on signup, login or checkout, with reversible links
- Start with relational tables; add NetworkX locally or Neo4j in production only when a question needs path traversal, such as the route to a friction point

**4. Predictive scoring**

- Churn risk from dormancy, friction history and order cadence; lifetime value from RFM; purchase propensity from in-session behavior
- Heuristics first, trained models once real event history exists, with the heuristic kept as the baseline to beat

**5. Natural-language query engine**

- Classifies a merchant's question into a known analysis from a fixed metric catalog; the LLM never writes free-form SQL
- Answers at three levels: an executive one-liner, an analytical breakdown with confidence, and a technical trace of event IDs and graph paths
- An evidence linker ties each claim to the computed result behind it; a claim without evidence is dropped

**6. Action proposer**

- Takes flags and scores, and proposes actions from a fixed menu (waive fee, bonus points, discount, segment sync, budget shift, recovery message, do nothing) with expected impact

**7. Policy governance and execution modes**

- Manual: insights only. Approval: a plan is drafted and waits for a human. Autonomous: runs if confidence and policy both allow
- Hard limits in plain code: maximum discount, maximum daily budget shift, contact cooldown, consent required. The model cannot override them
- Default is Approval; Autonomous is switched on per action type, only after measured accuracy supports it

**8. Orchestration and audit ledger**

- Dispatches approved plans through the outbound ports with retries and idempotency keys
- Append-only ledger of every prompt, retrieved context, decision, policy result and dispatch outcome
- Later measures what happened after each action and feeds it back into evaluation

## Decision layer

Every "which option?" question goes through one DecisionPort, so a rule set, an LLM or TypeSafe's Jev can answer it and be compared on the same test set.

A decision request is a typed question: the state (computed signals, never raw prose from customers), the allowed options, and the provider returns a probability per option. Examples: which retention action fits this customer (waive fee, bonus points, discount, none); which analysis a merchant question maps to; whether a drafted claim is supported by its evidence.

| Provider | Strengths | Weaknesses | Role |
| --- | --- | --- | --- |
| Rules and heuristics | Transparent, free, instant, no data sent out | Rigid, hand-tuned | Baseline and fallback; ships first |
| LLM with structured output | Flexible, handles odd phrasing | Slower, costlier, probabilities are self-reported text | Merchant Q&A, explanations, odd cases |
| Jev (TypeSafe System One) | Returns a probability per option in one pass; vendor reports 70 to 500 ms | New (September 2026), hosted only, early access, closed weights, 32,000-token state limit | Candidate for routing and action choice; adopt only if it wins the comparison |
| Trained model (later) | Learns each merchant's own history | Needs data and retraining | Replaces heuristics for churn and propensity once data exists |

**How a provider is chosen**

1. Build a labeled set of real decisions (a merchant question and its correct analysis; a customer state and the action a marketer would pick).
2. Run every provider on it and compare accuracy, latency, cost per decision and calibration.
3. Calibration means a stated 0.9 is right about 90% of the time. An independent crash-narrative study found a Jev-based pipeline accurate but not calibrated as delivered, so calibrate or audit before using a probability as an autonomy threshold.
4. Keep the winner behind the port, the others as fallbacks, and re-run the comparison when a provider releases a new version.

**Rules that do not change by provider**

- Policy limits and consent checks stay in plain code
- A provider outage degrades to the heuristic, never to a blocked pipeline
- Customer data sent to a hosted provider is minimized and covered by the privacy rules below

Sources: [TypeSafe Jev overview](https://www.getmaxim.ai/articles/what-is-jev-system-one-model/) (vendor-described); [crash-narrative study](https://arxiv.org/pdf/2609.24052) (independent measurement). Details are from search results and may change as Jev matures.

## Known issues and risks

The biggest risks are an unconfirmed contract with the other modules and an overambitious first build; the rest are manageable with the mitigations below.

| Issue | Why it matters | Mitigation |
| --- | --- | --- |
| Other modules' contracts unknown | Real events may not match the assumed EventEnvelope | Publish contracts early, add an anti-corruption layer, run contract tests, keep mock adapters |
| Scope too large | Eight components and three predictors will not finish at once | Build one thin vertical slice first (see the roadmap) |
| Cold start | No event history means no trained models and weak baselines | Heuristics first; seed with synthetic and replayed data; do not claim accuracy until measured |
| Small samples | Percent changes on tiny counts create false anomalies | Minimum sample size per metric; suppress or flag low-confidence results |
| LLM errors | Wrong or unsupported explanations erode merchant trust | LLM sees only computed signals; evidence linker drops unsupported claims; eval set |
| Uncalibrated probabilities | A confident wrong score could trigger an autonomous action | Calibrate on labeled data; autonomy off by default; per-action thresholds |
| Identity merge errors | Merging two people corrupts scores and messaging | Reversible links, confidence on merges, merge only on strong signals |
| Privacy and consent | Profiling and WhatsApp or email outreach are regulated (India's DPDP Act among them) | Consent flag on every event, minimize data sent to providers, retention limits, legal review before launch |
| Vendor dependence | Hosted Jev and LLM APIs can change, fail or be repriced | DecisionPort and LLMPort, fallbacks, pinned model versions |
| Runaway automation | Repeated or conflicting actions (double discount, message spam) | Idempotency keys, cooldowns, per-customer and per-day caps, a kill switch |
| Delayed feedback | Action outcomes arrive days later, so quality is hard to judge | Outcome tracking job, holdout groups where merchants allow it |
| Late and duplicate events | Counts drift if events arrive out of order or twice | Event-time processing, dedupe by event\_id, recompute windows |
| Multi-tenant leakage | One merchant seeing another's data is a severe failure | tenant\_id on every row and query, isolation tests |

## Non-functional requirements

Five qualities decide whether Module 4 can be trusted in production: isolation, privacy, observability, speed with cost control, and graceful failure.

**Multi-tenancy and security**

- tenant\_id on every table, event, rule and ledger entry; automated tests that try to read across tenants
- Authentication on every inbound port; signed requests between modules; secrets in a vault, never in code
- Approval actions tied to a named human user

**Privacy and consent**

- Consent stored with each event; no profiling or outreach without it
- Send only the fields a provider needs; avoid raw personal data in prompts
- Retention limits and a deletion path for a customer's data, including the ledger's references to it
- Review against India's DPDP Act before any real customer data is processed

**Observability**

- Structured logs with a trace id from ingestion to dispatch
- Metrics for ingestion lag, query latency, provider errors, policy rejections and approval rates
- Every claim shown to a merchant can be traced to its source events

**Latency and cost**

- Real-time scoring (propensity during a session) runs on local heuristics or a fast model, in milliseconds
- LLM calls are for questions, digests and explanations, where seconds are acceptable
- Cache digests, use a smaller model for classification, and track cost per merchant per day with a budget cap

**Graceful degradation**

- If the LLM is down, metrics and digests still work and explanations fall back to templates
- If a decision provider is down, the heuristic answers
- If an outbound module is down, actions queue with retries and expire after a stated time

## Testing and evaluation

Testing has two jobs: prove the deterministic parts are exactly right, and measure how often the model-driven parts are right.

| Layer | What it checks | How |
| --- | --- | --- |
| Unit | Metrics, anomaly thresholds, policy limits, identity merges | pytest with fixed inputs and exact expected outputs |
| Contract | Each port's schema, including partner adapters | Schema tests against the published contracts; replayed sample payloads |
| End to end | Event in, digest, proposal, policy check, mock dispatch, ledger entry | Scripted scenarios on mock adapters, one per execution mode |
| Safety | Limits cannot be bypassed, consent is enforced, tenants stay isolated | Adversarial cases, including prompts that try to exceed a discount cap |
| Model evaluation | Query routing, action choice, claim support | Labeled set of real decisions; accuracy, calibration, latency, cost per provider |
| Outcome | Whether approved actions helped | Track results after each action; compare against holdouts where allowed |

**Success measures for the first release**

1. Every metric shown matches a hand calculation on the test data, with its sample size
2. Every AI claim links to evidence, and unsupported claims are dropped
3. No action passes the policy check beyond a configured limit in any test
4. Query routing accuracy and approval rate are measured on a labeled set, and the target is agreed with the manager before building further

## Roadmap and open questions

Build in four phases, each ending at a gate that must pass before the next begins, and keep Autonomous mode for the last.

&#91;embedded content: roadmap · 4 phases, 4 gates\]

Phase 1 proves the numbers, phase 2 adds explanations and safety, phase 3 connects the real modules and compares providers, and phase 4 earns autonomy through measured accuracy.

**Open questions to settle with the other module owners and the manager**

1. What event format will Module 2 emit, and is it PostHog-shaped?
2. How will Module 1 expose actions (API, webhook or on-chain call), and does it support idempotency keys?
3. What can Module 3 accept for segment sync and budget changes?
4. Who uses Module 4 day to day (a merchant dashboard?), and which team builds that interface?
5. Who sets the policy defaults: maximum discount, daily budget shift, contact cooldown?
6. Which business verticals get metric templates first?
7. Is sending customer data to hosted providers (an LLM, Jev) allowed under the product's privacy terms?
8. Where will it be deployed, and what is the monthly provider budget?
