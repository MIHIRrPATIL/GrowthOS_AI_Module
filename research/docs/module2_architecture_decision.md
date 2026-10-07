# Architecture Decision Record (ADR) — GrowthOS Module 2: Behavior Intelligence SDK

**Status:** Accepted  
**Scope:** GrowthOS Module 2 (Behavior Intelligence SDK) & Integration with Module 4 (AI Growth Brain)  
**Location:** `research/`

---

## 1. Context & Business Problem

GrowthOS requires a behavioral tracking and conversion intelligence layer (Module 2) to:
1. Capture granular client-side interactions (pageviews, clicks, forms, scroll, rage clicks, exit intent, web vitals).
2. Record transactional custom events (products, carts, checkouts, orders, rewards).
3. Sessionize raw streams into user journeys and identify friction points (e.g. checkout abandonment).
4. Feed structured behavioral signals into Module 4's Unified Customer Graph (Neo4j) and AI Growth Brain for LTV, churn prediction, and semantic business query reasoning.

Building a full-scale behavioral capture engine from scratch (cross-browser queueing, Beacon API retries, DOM mutation observers, session replay recorder, Kafka stream partitions, ClickHouse schema clustering) is an enormous engineering overhead that distracts from GrowthOS's core differentiator: **AI Growth Reasoning & Cross-Module Orchestration**.

---

## 2. Decision: The Facade & Engine Strategy (PostHog Engine + GrowthOS Facade)

We adopt a **Facade Wrapper Pattern**:
- **Public API:** Merchants install `<script src="https://cdn.growthos.io/sdk.js">` and interact strictly with the `GrowthOS` namespace (`GrowthOS.init()`, `GrowthOS.track()`, `GrowthOS.identify()`, `GrowthOS.page()`).
- **Underlying Engine:** PostHog-JS and PostHog ingestion (ClickHouse + Kafka + Redis).
- **Signal Extraction Bridge:** Asynchronous consumer that reads processed events from ClickHouse / PostHog Webhooks and reduces high-volume raw events into high-value **Derived Behavioral Signals** (`behavior.rage_click`, `behavior.exit_intent`, `behavior.checkout.abandoned`, `behavior.high_intent`).

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                 Merchant Web Application                    │
                    │   GrowthOS.init(...) • GrowthOS.track(...)                  │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │
                               ┌───────────────────┴───────────────────┐
                               │     GrowthOS SDK Facade Layer         │
                               │  - Schema & Idempotency Validation    │
                               │  - PII Masking & Privacy Sanitization │
                               │  - Heuristics: Rage/Dead/Exit Intent  │
                               │  - Multi-tenant Context Injection     │
                               └───────────────────┬───────────────────┘
                                                   │
                   ┌───────────────────────────────┴───────────────────────────────┐
                   ▼ (Batching Transport)                                          ▼ (Direct HTTP Fallback)
        ┌──────────────────────────────────────┐                       ┌──────────────────────────────────────┐
        │        PostHog-JS Adapter            │                       │          HTTP Ingestion API          │
        │   (Autocapture, Replays, Buffer)     │                       │     (Server-to-Server Webhooks)      │
        └──────────────────┬───────────────────┘                       └──────────────────┬───────────────────┘
                           │                                                              │
                           ▼                                                              ▼
        ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
        │                                 Ingestion Pipeline (FastAPI / Kafka)                                │
        └──────────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                           │
                                           ┌───────────────┴───────────────┐
                                           ▼                               ▼
                             ┌───────────────────────────┐   ┌───────────────────────────┐
                             │   ClickHouse Analytics    │   │  Derived Signal Processor │
                             │  (Funnels, Aggregations)  │   │  (Rage clusters, Abandon) │
                             └─────────────┬─────────────┘   └─────────────┬─────────────┘
                                           │                               │
                                           └───────────────┬───────────────┘
                                                           ▼
                                            ┌─────────────────────────────┐
                                            │ Module 4: AI Growth Brain   │
                                            │ - Neo4j Customer Graph      │
                                            │ - Churn / LTV / Propensity  │
                                            │ - Autonomous Action Policy  │
                                            └─────────────────────────────┘
```

---

## 3. Benefits of this Architecture

1. **Zero Vendor Lock-in:** The merchant code never mentions `posthog`. If GrowthOS migrates to an in-house Kafka cluster or custom data lake later, not a single merchant needs to touch their frontend.
2. **Reliability & Edge Case Resilience:** PostHog-JS handles tricky browser behaviors (Safari ITP, mobile background tab throttling, network offline queueing, beacon API limits, session replay DOM diffing).
3. **Multi-Tier Data Reduction:** Raw DOM interaction volume ($10^7-10^9$ events/mo) stays in ClickHouse/S3, while only synthesized behavioral signals and graph nodes reach PostgreSQL and Neo4j.
4. **Instant Multi-Platform Support:** Ready for web, Node.js, Python, and mobile clients with identical schema validation.

---

## 4. Security, Privacy & CSP Rules

- **Zero-Leak PII Sanitization:** Credit card numbers (Luhn check), passwords, CVVs, SSNs, and elements marked `data-growthos-mask` are automatically sanitized client-side before transmission.
- **CSP Directives Required:**
  - `script-src: 'self' https://cdn.growthos.io https://us-assets.i.posthog.com;`
  - `connect-src: 'self' https://api.growthos.io https://us.i.posthog.com;`
  - `worker-src: 'self' blob:;`
