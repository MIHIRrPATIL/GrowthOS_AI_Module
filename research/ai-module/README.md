# GrowthOS Module 4: AI Growth Brain & Customer Intelligence Service

## 1. Executive Summary & Design Philosophy

The **AI Growth Brain (Module 4)** is the central semantic reasoning, prediction, and policy orchestration layer of GrowthOS. It connects customer acquisition (Module 3 Ads), customer conversion (Module 2 Behavior SDK), and customer retention (Module 1 Loyalty) into a unified decision-making engine.

### Decoupling Invariant (Hexagonal / Ports & Adapters Architecture)
Because the internal implementations, APIs, and schemas of the other modules are assumed to be unknown or evolving, this service is built strictly using **Ports and Adapters**:
- The AI Module owns its own **Domain Models**, **Ontologies**, and **Contracts**.
- All external interactions go through pluggable **Inbound Ports** (how data gets in) and **Outbound Ports** (how actions get dispatched).
- Mock and stub adapters are provided out-of-the-box so the service is 100% testable, runnable, and verifiable in total isolation.

```
                          ┌───────────────────────────┐
                          │   Inbound HTTP / Events   │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Inbound Ports)
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI Module Core Domain                            │
│                                                                             │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐  │
│  │ Semantic Query Engine │ │ Grounded Math Engine  │ │  Digest Engine    │  │
│  │ (RAG + NL Interface)  │ │ (Exact Sample Metrics)│ │ (Anomaly Detector)│  │
│  └───────────┬───────────┘ └───────────┬───────────┘ └─────────┬─────────┘  │
│              │                         │                       │            │
│              └────────────────┐        │        ┌──────────────┘            │
│                               ▼        ▼        ▼                           │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐  │
│  │ Customer Graph        │ │ Predictive Models     │ │ Policy Governance │  │
│  │ (Identity & Topology) │ │ (Churn, LTV, Propens.)│ │ (Limits, Approval)│  │
│  └───────────────────────┘ └───────────────────────┘ └─────────┬─────────┘  │
│                                                                │            │
│                               ▼                                             │
│                  ┌───────────────────────────┐                              │
│                  │  Action Orchestrator      │                              │
│                  └─────────────┬─────────────┘                              │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼ (Outbound Ports)
    ┌────────────────┬───────────┴────────────┬────────────────┐
    ▼                ▼                        ▼                ▼
┌──────────────┐ ┌──────────────┐      ┌──────────────┐ ┌──────────────┐
│ Module 1 Port│ │ Module 2 Port│      │ Module 3 Port│ │ Storage Port │
│  (Loyalty)   │ │  (Behavior)  │      │    (Ads)     │ │(Graph/DB/Vec)│
└──────────────┘ └──────────────┘      └──────────────┘ └──────────────┘
```

---

## 2. Comprehensive Feature Matrix

### Feature Group A: Semantic Business Query & Natural Language Interface
1. **Natural Language Query Parsing & Intent Classification**
   - Translates merchant questions (e.g. *"Why did conversion drop on mobile this weekend?"*) into structured retrieval filters (timeframe, metrics, segments).
2. **Progressive Abstraction Synthesizer**
   - Produces three-tiered outputs:
     - Tier 1: One-sentence Executive Diagnosis (for CEOs/Founders).
     - Tier 2: Analytical Breakdown with confidence score and evidence (for Growth/Product managers).
     - Tier 3: Technical Audit Payload with node traces and event IDs (for Data/Engineering teams).
3. **Structured Evidence & Citation Linker**
   - Binds every AI claim to concrete underlying facts (exact session counts, funnel steps, delta percentages).
   - Zero-unsupported-claims policy (if data is insufficient, state uncertainty rather than guessing).

### Feature Group B: Grounded Deterministic Intelligence (No-Hallucination Layer)
4. **Deterministic Metrics Engine (Component 1)**
   - Pure mathematical calculations for conversion rates, step drop-offs, cart abandonment rates, and cohort totals.
   - Parameterized by business vertical (E-Commerce, SaaS, Bookings, Media).
   - Returns explicit sample sizes (`sample_size`, `prior_sample_size`) and ISO timestamps with every number.
5. **Period-over-Period Digest Anomaly Engine (Component 2)**
   - Scheduled comparator evaluating period-over-period drift (Week-over-Week, Month-over-Month, Day-over-Day).
   - Detects metric deltas crossing configurable thresholds (default: 10%).
   - Severity classification: Low (<20%), Medium (20-35%), High (>35%).
6. **Absence Signal & Dormant Cohort Detector**
   - Identifies non-events (e.g. user added to cart >60 min ago without purchase, high-intent user showed no activity for 7 days).

### Feature Group C: Customer Intelligence & Graph Representation
7. **Unified Customer Graph Engine**
   - Entity nodes: `Customer`, `AnonymousDevice`, `Session`, `Product`, `Order`, `Campaign`, `FrictionPoint`, `BehavioralSignal`.
   - Relationships: `PERFORMED_SESSION`, `VIEWED`, `ADDED_TO_CART`, `EXHIBITED_SIGNAL`, `ACQUIRED_BY`, `DROPPED_AT`.
   - In-memory NetworkX implementation for zero-dependency execution, with pluggable Neo4j driver.
8. **Identity Resolution & Entity Stitching**
   - Merges anonymous device histories into identified customer profiles upon login or checkout.
   - Preserves lineage so pre-login attribution is never lost.
9. **Dynamic Behavioral Segmentation**
   - Generates and refreshes dynamic cohorts (e.g., *"Cart Abandoners with High Product Intent"*, *"Delivery Fee Sensitive Gold Members"*, *"Churning Weekend Regulars"*).

### Feature Group D: Predictive Machine Learning & Heuristics
10. **Churn Risk Evaluator**
    - Multi-factor scoring (inactivity cadence, drop-off severity, previous order frequency).
11. **Customer Lifetime Value (LTV) Predictor**
    - Estimates future monetary value based on recency, frequency, and cart history.
12. **Purchase Propensity & Conversion Likelihood Scorer**
    - Evaluates real-time intent level (e.g. 3+ views on high-margin product + crust customization = 91% purchase propensity).

### Feature Group E: Policy Governance, Guardrails & Execution Modes
13. **Three-Mode Operating Controller**
    - **Manual Mode:** Produces explanations and suggestions only; human executes.
    - **Approval Mode:** Drafts action plans with cost/reward estimates; queues for human one-click approval.
    - **Autonomous Mode:** Executes immediately if policy constraints, confidence thresholds, and budget limits are satisfied.
14. **Deterministic Policy Boundary Engine**
    - Hardcoded invariants that LLMs cannot override:
      - Max discount amount or percentage (e.g., max 20% or ₹150).
      - Max daily autonomous budget shifts (e.g., max 15% daily campaign change).
      - Cooldown intervals (e.g., do not send more than 1 WhatsApp message per user per 48 hours).
15. **Execution Audit Ledger & Rollback Support**
    - Immutable log of all AI decisions, prompts, reasoning steps, policy validations, and execution receipts.

### Feature Group F: Action Orchestration & Modular Adapter Ports
16. **Action Plan Synthesizer**
    - Deconstructs an approved recommendation into discrete operational tasks across modules.
17. **Pluggable Outbound Ports:**
    - `LoyaltyPort`: Trigger delivery fee waiver, grant bonus points, issue coupon.
    - `BehaviorPort`: Request granular session tracing, report UI friction bug.
    - `AdsPort`: Push retargeting audience segment, propose campaign budget reallocation.
    - `MessagingPort`: Webhook/email/WhatsApp notification trigger.

---

## 3. How to Build It (Technical Step-by-Step Blueprint)

### Step 1: Core Domain Contracts & Models (`ai-module/domain/`)
- Define strict Pydantic v2 schemas:
  - `EventEnvelope`, `CustomerProfile`, `GraphNode`, `GraphEdge`
  - `MetricResult`, `DigestFlag`, `DigestReport`
  - `AIInsight`, `ActionPlan`, `PolicyRule`, `ExecutionReceipt`
- No dependency on any external module or network connection.

### Step 2: Storage & Graph Engine (`ai-module/graph/`)
- Implement `CustomerGraph` using `networkx` for fast local testing and topological queries.
- Build query helpers: shortest path between customer and friction points, high-intent product clusters, cohort neighborhoods.
- Provide a `Neo4jCustomerGraph` adapter when a live database connection string is provided.

### Step 3: Grounded Reasoning & Anomaly Detection (`ai-module/engines/`)
- Implement `MetricsEngine` providing deterministic calculations with explicit sample sizes (see [Metrics Engine Specification](file:///home/mihir/Codes/internship/GrowthOS/research/docs/metrics_engine_specification.md)).
- Implement `DigestEngine` providing period-over-period comparisons, delta calculation, and threshold-based flag generation.
- Implement `PredictiveEngine` providing RFM heuristics and propensity scoring.

### Step 4: Policy & Safety Guardrails (`ai-module/policy/`)
- Implement `PolicyEngine` evaluating candidate actions against business limits (max discounts, spend limits, frequency caps).
- Implement `AuditLedger` writing JSONL audit entries with execution timestamps and confidence scores.

### Step 5: Semantic AI Reasoning & RAG (`ai-module/reasoning/`)
- Implement prompt templates that feed deterministic metric outputs, graph context, and policy constraints into the LLM.
- Enforce structured JSON output using Pydantic validation (guaranteeing confidence scores and evidence arrays).
- Include offline/mock fallback responses so the service functions without an active external LLM API key.

### Step 6: Outbound Adapter Ports (`ai-module/adapters/`)
- Create abstract interfaces (`BaseLoyaltyAdapter`, `BaseBehaviorAdapter`, `BaseAdsAdapter`, `BaseNotificationAdapter`).
- Implement `Mock*Adapter` classes that record dispatches in memory.
- Implement `Http*Adapter` classes for production webhooks and REST endpoints.

### Step 7: Service Entrypoint & FastAPI Server (`ai-module/api/`)
- Expose REST API:
  - `POST /api/v1/ai/query`: Natural language semantic query endpoint.
  - `GET  /api/v1/ai/metrics`: Grounded deterministic metrics.
  - `GET  /api/v1/ai/digest`: Periodic anomaly flags.
  - `POST /api/v1/ai/actions/approve`: Action plan approval & execution.
  - `GET  /api/v1/ai/graph/{id}`: Customer graph visualization data.
  - `GET  /api/v1/ai/audit`: Complete decision audit log.

---

## 4. Planned Project Structure

```
research/ai-module/
├── README.md                  # This specification and architectural blueprint
├── pyproject.toml             # Modern package definition with uv/pip
├── domain/                    # Pure domain models and contract interfaces
│   ├── __init__.py
│   ├── contracts.py           # Universal Inbound and Outbound port definitions
│   ├── entities.py            # Customer, Session, Product, Campaign models
│   ├── signals.py             # Behavioral and Derived signals
│   └── actions.py             # Action plans, policies, and audit models
├── graph/                     # Graph intelligence layer
│   ├── __init__.py
│   ├── base.py                # Graph interface
│   ├── networkx_graph.py      # Zero-dependency local graph engine
│   └── neo4j_adapter.py       # Production Neo4j connector
├── engines/                   # Deterministic & predictive computational engines
│   ├── __init__.py
│   ├── metrics_engine.py      # Grounded metric calculation with sample sizes
│   ├── digest_engine.py       # Period-over-period anomaly comparator
│   └── predictive_engine.py   # LTV, Churn, and Propensity scoring
├── policy/                    # Safety guardrails and execution governance
│   ├── __init__.py
│   ├── policy_checker.py      # Hard limit enforcement & operating mode router
│   └── audit_ledger.py        # Immutable decision and execution logger
├── reasoning/                 # LLM semantic reasoning and prompt orchestration
│   ├── __init__.py
│   ├── prompt_templates.py    # Grounded prompts with progressive abstraction
│   ├── semantic_router.py     # Intent classification and context assembler
│   └── provider_client.py     # Agnostic LLM client (with mock offline fallback)
├── adapters/                  # Pluggable connectors to other modules & systems
│   ├── __init__.py
│   ├── mock_adapters.py       # Self-contained mocks for Module 1, 2, and 3
│   ├── http_adapters.py       # REST/Webhook connectors
│   └── storage_adapters.py    # Database adapters
├── api/                       # FastAPI application & route controllers
│   ├── __init__.py
│   ├── server.py              # Application factory & CORS
│   └── routes.py              # API endpoint handlers
└── tests/                     # Automated unit and integration test suite
    ├── __init__.py
    ├── test_metrics_engine.py # Deterministic metric calculations
    ├── test_digest_engine.py  # Anomaly detection & flag thresholds
    ├── test_customer_graph.py # Identity resolution & graph queries
    ├── test_policy_engine.py  # Governance & hard safety limits
    └── test_api_routes.py     # End-to-end API integration tests
```
