# GrowthOS Platform Directory & Five-Pillar Module Architecture

**Document Version:** 1.0.0  
**Status:** Approved  
**Location:** `research/docs/GROWTHOS_PLATFORM_DIRECTORY_AND_MODULE_ARCHITECTURE.md` (Accessible via `docs/`)

---

## 1. Executive Summary

GrowthOS is an omnichannel, AI-native Growth Operating System designed to acquire customers, optimize conversions, retain users, and understand customer behavior through a unified reasoning engine.

To support rapid, isolated feature iteration while preserving strict cross-module contracts, the repository is organized into five core directories under `platform/`:

1. **Shared Platform (`platform/shared/`)**: Foundational infrastructure, universal event envelope schemas (`EventEnvelope`), multi-tenant routing, database connections, and shared utility libraries.
2. **Loyalty Module (`platform/loyalty/`)**: Customer retention, points and tier management, immutable insert-only transactions ledger, earn/redeem/refund business logic, and referral mechanics.
   - Upstream Source: `https://github.com/KavyaKankonkar/Loyalty-and-rewards-platform.git`
3. **SDK Module (`platform/sdk/`)**: High-frequency client-side telemetry capture, browser client SDK (`@growthos/browser`), Chrome Manifest V3 QA debugger extension, and real-time behavioral friction detection.
   - Upstream Source: `https://github.com/djtechminds-satview/growthos.git`
4. **Ads Module (`platform/ads/`)**: Multi-channel campaign plan generation, Google Ads API connectors, offline conversion uploading, and deterministic closed-loop attribution matching.
5. **AI Module (`platform/ai/`)**: The AI Growth Brain decision and reasoning layer. Features deterministic metric computations, period-over-period anomaly digests, customer graph identity resolution, predictive scoring, policy governance with execution gating (Manual, Approval, Autonomous), JEV candidate routing, and tamper-evident audit logging.

---

## 2. Directory Layout & Module Responsibilities

```
platform/
├── shared/
│   ├── contracts/        # Shared protocols, anti-corruption interfaces, and OpenAPI specs
│   ├── events/           # Canonical EventEnvelope, event taxonomy validators
│   ├── config/           # Centralized environment configuration and tenant settings
│   ├── database/         # Common database session management and migration helpers
│   └── utils/            # Shared cryptographic hashing, token math, and logging
├── loyalty/
│   ├── app/              # FastAPI application, auth, database, models, schemas, services
│   ├── migrations/       # SQL migrations for insert-only ledger and tenant isolation
│   └── tests/            # Pytest suite for earn, redeem, refund, and tenancy
├── sdk/
│   ├── browser-sdk/      # @growthos/browser source and build configuration
│   ├── chrome-extension/ # Manifest V3 extension for live DOM and event inspection
│   ├── dashboard/        # Real-time event observability dashboard
│   └── tests/            # Playwright E2E and unit test coverage
├── ads/
│   ├── api/              # FastAPI routes (port 8001) for metrics and campaign deployment
│   ├── attribution/      # Click tracker, conversion matcher, offline uploader
│   ├── connectors/       # Google Ads API client and offline playback fixtures
│   ├── domain/           # Ad models, schemas, and campaign entities
│   └── storage/          # Daily performance metric store and attribution records
└── ai/
    ├── api/              # FastAPI routes for merchant natural language queries
    ├── core/             # MetricsEngine, AnomalyDigest, IdentityResolution, Scoring
    ├── decision/         # JEV discrete candidate selector and LLM narrative providers
    ├── governance/       # PolicyEngine, consent evaluation, causal holdout allocator
    ├── ledger/           # Append-only tamper-evident hash-chained audit storage
    └── ports/            # Outbound adapters connecting to Loyalty, SDK, Ads, and Messaging
```

---

## 3. Inter-Module Dataflow & Integration Architecture

```
+-----------------------------------------------------------------------------------+
|                        Client Layer (Browsers & Apps)                             |
|             Domino's Pizza E-Commerce Storefront / Merchant Web Apps              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Micro-interactions & Clicks
                                          v
+-----------------------------------------------------------------------------------+
|                     Module 2: Behavior Intelligence SDK                           |
|  - Autocapture Engine (DOM clicks, forms, scrolls, visibility)                    |
|  - Real-time Heuristic Friction (Rage click, dead click, exit intent, hesitation) |
|  - Privacy Shield (Luhn credit card check, password/SSN redaction)                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Batched EventEnvelope Streams
                                          v
+-----------------------------------------------------------------------------------+
|                           Shared Platform Ingestion                               |
|  - Ingestion Deduplication (event_id, idempotency_key)                            |
|  - Multi-tenant Context Validation (workspace_id, project_id)                     |
|  - Normalized Storage & Event Bus                                                 |
+-----------------------+--------------------+-------------------+------------------+
                        |                    |                   |
                        v                    v                   v
              +---------+--------+  +--------+--------+  +-------+--------+
              | Module 1         |  | Module 3        |  | Module 4       |
              | Loyalty Platform |  | Ads Layer       |  | AI Growth      |
              | - Points Ledger  |  | - Google Ads    |  |   Brain        |
              | - Earn & Redeem  |  | - Offline Conv  |  | - MetricsMath  |
              | - Tier Mechanics |  | - Attribution   |  | - JEV Router   |
              +---------+--------+  +--------+--------+  +-------+--------+
                        ^                    ^                   |
                        | Outbound Action    | Outbound Action   | ActionPlan
                        | (e.g. Waive Fee)   | (e.g. Shift Cap)  | & Policy Gate
                        +--------------------+-------------------+
```

---

## 4. Key Invariants & Non-Negotiable Rules

1. **Deterministic Metrics Guarantee**:
   - The LLM never calculates numbers, sample sizes, or conversion rates.
   - All arithmetic and period comparisons occur in deterministic Python code (`MetricsEngine`).
   - Every metric reported must carry `sample_size`, `prior_sample_size`, and an ISO timestamp.
2. **Immutable Insert-Only Loyalty Accounting**:
   - The loyalty module never executes SQL `UPDATE` operations on point balance rows.
   - Current balances are computed as sums over an append-only ledger of verified events.
3. **Discrete Candidate Routing (System 1 vs System 2)**:
   - Queries and anomalies are classified by TypeSafe Jev against discrete candidate spaces (`M0-M10` for metrics, `A0-A6` for actions) consuming ~120 tokens.
   - Full LLM narrative generation is invoked on demand only when strategic advice is requested.
4. **Fail-Closed Policy Governance**:
   - Outbound actions to external modules must pass hard constraints (budget shift limits, discount maximums, customer consent, contact cooldowns).
   - If an action violates any policy rule, it is immediately rejected and recorded in the audit ledger.
5. **Tamper-Evident Auditability**:
   - All prompts, retrieved contexts, decision outputs, policy evaluations, and dispatch results are appended to a hash-chained audit ledger (`SqlAuditLedgerAdapter`).
