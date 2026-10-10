# GrowthOS AI Module (AI Growth Brain): Architecture, Components, and Technical Specification

This document provides a comprehensive technical breakdown of every component in the GrowthOS AI Module (Module 4, AI Growth Brain). Each component is analyzed across three dimensions:
- **WHAT**: Definition, system role, inputs, outputs, and contracts.
- **HOW**: Implementation details, algorithms, data structures, and state transitions.
- **WHY**: Architectural rationale, platform constraints, mathematical invariants, anti-hallucination guarantees, and design trade-offs.

---

## Table of Contents
1. [Architectural Overview & Core Invariants](#1-architectural-overview--core-invariants)
2. [Domain Layer (`domain/`)](#2-domain-layer-domain)
   - [2.1 Telemetry & Event Envelopes (`domain/events.py`, `domain/telemetry.py`)](#21-telemetry--event-envelopes-domaineventspy-domaintelemetrypy)
   - [2.2 Metrics & Digest Contracts (`domain/metrics.py`)](#22-metrics--digest-contracts-domainmetricspy)
   - [2.3 Natural Language Processing Contracts (`domain/nlp.py`)](#23-natural-language-processing-contracts-domainnlppy)
   - [2.4 Actions, Policies & Audit Models (`domain/actions.py`)](#24-actions-policies--audit-models-domainactionspy)
   - [2.5 Reversible Identity Graph (`domain/identity.py`)](#25-reversible-identity-graph-domainidentitypy)
3. [Analytical & Decision Engines (`engines/`)](#3-analytical--decision-engines-engines)
   - [3.1 Grounded Deterministic Metrics Engine (`engines/metrics_engine.py`)](#31-grounded-deterministic-metrics-engine-enginesmetrics_enginepy)
   - [3.2 Deterministic Digest & Anomaly Engine (`engines/digest_engine.py`)](#32-deterministic-digest--anomaly-engine-enginesdigest_enginepy)
   - [3.3 Anti-Hallucination Evidence Linker (`engines/evidence_linker.py`)](#33-anti-hallucination-evidence-linker-enginesevidence_linkerpy)
   - [3.4 Natural Language Query Engine (`engines/nl_query_engine.py`)](#34-natural-language-query-engine-enginesnl_query_enginepy)
   - [3.5 Deterministic Policy Engine (`engines/policy_engine.py`)](#35-deterministic-policy-engine-enginespolicy_enginepy)
   - [3.6 Digest Explanation Engine (`engines/digest_explanation_engine.py`)](#36-digest-explanation-engine-enginesdigest_explanation_enginepy)
   - [3.7 Heuristic Scoring Engine (`engines/heuristic_scoring.py`)](#37-heuristic-scoring-engine-enginesheuristic_scoringpy)
   - [3.8 Vertical Industry Templates (`engines/vertical_templates.py`)](#38-vertical-industry-templates-enginesvertical_templatespy)
4. [Application Services (`services/`)](#4-application-services-services)
   - [4.1 Action Orchestrator Service (`services/action_orchestrator.py`)](#41-action-orchestrator-service-servicesaction_orchestratorpy)
   - [4.2 24-Hour Attribution Closing Worker (`services/attribution_closing_worker.py`)](#42-24-hour-attribution-closing-worker-servicesattribution_closing_workerpy)
   - [4.3 Idle Cart Sweep Worker (`services/idle_cart_sweep_worker.py`)](#43-idle-cart-sweep-worker-servicesidle_cart_sweep_workerpy)
   - [4.4 Action Proposer Service (`services/action_proposer.py`)](#44-action-proposer-service-servicesaction_proposerpy)
   - [4.5 Approval & Decision Services (`services/approval_service.py`, `services/decision_manager.py`)](#45-approval--decision-services-servicesapproval_servicepy-servicesdecision_managerpy)
   - [4.6 Merchant Query Service (`services/merchant_query_service.py`)](#46-merchant-query-service-servicesmerchant_query_servicepy)
5. [Ports & Adapters (Hexagonal Architecture) (`ports/`, `adapters/`)](#5-ports--adapters-hexagonal-architecture-ports-adapters)
   - [5.1 Google Gemini Live Decision Provider (`adapters/gemini_decision_provider.py`)](#51-google-gemini-live-decision-provider-adaptersgemini_decision_providerpy)
   - [5.2 Multi-Model OpenRouter Adapter (`adapters/openrouter_decision_provider.py`)](#52-multi-model-openrouter-adapter-adaptersopenrouter_decision_providerpy)
   - [5.3 Rule Decision Provider / Degraded Mode (`engines/rule_decision_provider.py`)](#53-rule-decision-provider--degraded-mode-enginesrule_decision_providerpy)
   - [5.4 Relational Identity Resolver (`adapters/sql_identity_resolver.py`)](#54-relational-identity-resolver-adapterssql_identity_resolverpy)
   - [5.5 Tamper-Evident Cryptographic Audit Ledger (`adapters/sql_audit_ledger.py`)](#55-tamper-evident-cryptographic-audit-ledger-adapterssql_audit_ledgerpy)
   - [5.6 Outbound Adapters: Ads, Loyalty, Notifications (`adapters/http_ads_adapter.py`, etc.)](#56-outbound-adapters-ads-loyalty-notifications-adaptershttp_ads_adapterpy-etc)
6. [Evaluation & Benchmark Suite (`evaluation/`)](#6-evaluation--benchmark-suite-evaluation)
   - [6.1 Provider Evaluator (`evaluation/evaluator.py`)](#61-provider-evaluator-evaluationevaluatorpy)

---

## 1. Architectural Overview & Core Invariants

The AI Module (Module 4) is the analytical brain of GrowthOS. It serves as an autonomous intelligence, natural language interface, and policy-governed intervention engine. It bridges raw storefront telemetry, mathematical anomaly detection, LLM reasoning, and downstream ad/retention execution.

```
+----------------------------------------------------------------------------------------------------+
|                                      GROWTHOS AI GROWTH BRAIN                                      |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    [ Raw Storefront Telemetry ]                          [ Merchant Natural Language Queries ]     |
|                 │                                                          │                       |
|                 ▼                                                          ▼                       |
|       +-------------------+                                      +--------------------+            |
|       | SqlEventStorage   |                                      | NLQueryEngine      |            |
|       +---------┬---------+                                      +---------┬----------+            |
|                 │                                                          │                       |
|                 ▼                                                          ▼                       |
|       +-------------------+                                      +--------------------+            |
|       | MetricsEngine     |<-------------------------------------| Intent Classifier  |            |
|       +---------┬---------+                                      +--------------------+            |
|                 │                                                          │                       |
|                 ▼                                                          ▼                       |
|       +-------------------+                                      +--------------------+            |
|       | DigestEngine      |                                      | Ground-Truth Facts |            |
|       +---------┬---------+                                      +---------┬----------+            |
|                 │                                                          │                       |
|                 ▼                                                          ▼                       |
|       +-------------------+       +-----------------------+      +--------------------+            |
|       | Anomaly Detection |------>| GeminiDecisionProvider|----->| EvidenceLinker     |            |
|       +-------------------+       +-----------┬-----------+      +---------┬----------+            |
|                                               │                            │                       |
|                                               ▼                            ▼                       |
|                                   +-----------------------+      +--------------------+            |
|                                   | PolicyEngine (Gates)  |      | 3-Tier Answer      |            |
|                                   +-----------┬-----------+      +--------------------+            |
|                                               │                                                    |
|                                               ▼                                                    |
|                                   +-----------------------+                                        |
|                                   | ActionOrchestrator    |                                        |
|                                   +-----┬-----------┬-----+                                        |
|                                         │           │                                              |
|                                         ▼           ▼                                              |
|                     +-----------------------+   +-----------------------+                          |
|                     | SqlAuditLedger        |   | Outbound Adapters     |                          |
|                     | (Cryptographic Chain) |   | (Ads, WhatsApp, Fee)  |                          |
|                     +-----------------------+   +-----------------------+                          |
+----------------------------------------------------------------------------------------------------+
```

### Core Invariants of the AI Module
1. **Zero Generative Math**: All metrics, rates, conversion funnels, and deltas are calculated in pure Python and SQL code. LLMs are strictly forbidden from performing mathematical calculations.
2. **0.5% EvidenceLinker Anti-Hallucination Bound**: Every numerical claim generated by an LLM is cross-checked against deterministic database values; any deviation beyond $\pm 0.5\%$ is pruned or rejected.
3. **No Text-to-SQL Execution**: User queries are classified into curated vertical metric templates. The engine never generates arbitrary raw SQL from natural language, preventing prompt injection attacks and query errors.
4. **Integer-Paise Financial Boundaries**: All fee waivers, credit allocations, and budgets are represented as 64-bit integer paise (1 INR = 100 paise). Float values are rejected.
5. **Fail-Closed Policy Enforcement**: Actions cannot execute without passing deterministic policy evaluation (quiet hours, contact cooldowns, DPDP purpose consent, budget limits). If consent cannot be verified, the action fails closed.
6. **Cryptographic Write-Ahead Audit Trail**: Every proposed, approved, or executed action is hashed and recorded in an append-only ledger with trigger-enforced `BLOCK_UPDATE_DELETE` constraints.
7. **10% Randomized Holdout Controls**: Interventions allocate a randomized 10% un-messaged control group to measure true incremental conversion lift.

---

## 2. Domain Layer (`domain/`)

The domain layer establishes the foundational data contracts, domain events, and state representations across the AI system.

### 2.1 Telemetry & Event Envelopes ([domain/events.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/events.py), [domain/telemetry.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/telemetry.py))
- **WHAT**: Immutable envelopes for all storefront actions: pageviews, cart updates, checkout progression, payments, and rage clicks.
- **HOW**: `EventEnvelope` defines:
  - `event_id`: Unique identifier (`evt_...`).
  - `tenant_id`: Multi-tenant workspace identifier.
  - `event_name`: Canonical action name (`cart.item_added`, `checkout.step_passed`, `order_completed`).
  - `anonymous_id`: First-party cookie tracking device sessions.
  - `user_id`: Authenticated customer identifier (phone, email).
  - `timestamp`: Event creation time in UTC.
  - `received_at`: Ingestion watermark timestamp.
- **WHY**: Watermarking on `received_at` ensures queries are 100% reproducible over historical data, preventing backfill events from skewing retrospective anomaly detection.

### 2.2 Metrics & Digest Contracts ([domain/metrics.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/metrics.py))
- **WHAT**: Strict output models for deterministic metric evaluations.
- **HOW**: `MetricResult` encapsulates:
  - `metric_name`: Canonical key (e.g. `cart_abandonment_rate`, `checkout_step_2_drop_off_rate`).
  - `value`: Computed float or integer (or `None` if undefined).
  - `numerator`, `denominator`: Exact integer counts.
  - `status`: `MetricStatus.OK`, `ZERO_DENOMINATOR`, `INSUFFICIENT_SAMPLE`.
  - `window`: Evaluated `TimeWindow` (start to end).
  - `as_of`: Query watermark timestamp.
- **WHY**: Preserving explicit numerator and denominator counts enables the two-proportion Z-test and ensures $0/0$ is properly classified as `ZERO_DENOMINATOR` rather than misrepresented as $0.0\%$.

### 2.3 Natural Language Processing Contracts ([domain/nlp.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/nlp.py))
- **WHAT**: Type definitions for natural language classification and grounded narrative output.
- **HOW**:
  - `QueryIntent`: Enum covering `FUNNEL_DROP_OFF`, `ANOMALY_DIAGNOSIS`, `REVENUE_IMPACT`, `CAMPAIGN_RECOMMENDATION`, `WHAT_IF_SIMULATION`.
  - `StructuredAnswer`: 3-tier response model:
    - Tier 1: `executive_summary` (concise narrative).
    - Tier 2: `analytical_detail` (dimensional breakdowns, step transitions).
    - Tier 3: `technical_telemetry` (sample sizes, watermarks, SQL query identifiers).
  - `EvidenceCitation`: Explicit binding between a claimed sentence and verified `MetricResult` facts.
- **WHY**: Segmenting answers into 3 tiers allows the same engine to serve both busy founders (Tier 1) and data engineers (Tier 3), while citations prove factual verification.

### 2.4 Actions, Policies & Audit Models ([domain/actions.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/actions.py))
- **WHAT**: Specifications for autonomous growth interventions.
- **HOW**:
  - `ActionPlan`: Encapsulates `plan_id`, `action_type` (`WAIVE_DELIVERY_FEE`, `SEND_RECOVERY_WHATSAPP`, `FLAG_UI_FRICTION_BUG`, `SHIFT_BUDGET`), `execution_mode` (`MANUAL`, `APPROVAL`, `AUTONOMOUS`), `parameters`, and `holdout_assigned` (boolean).
  - `PolicyRule`: Defines hard constraints (max discount paise, cooldown hours, allowed hours).
  - `AuditRecord`: Immutable record with cryptographic hash, previous hash, timestamp, and action diff.
- **WHY**: Prevents accidental actions. Every proposed intervention must have an explicit execution mode and adhere to policy limits before reaching dispatch adapters.

### 2.5 Reversible Identity Graph ([domain/identity.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/identity.py))
- **WHAT**: Models for linking fragmented customer touchpoints (anonymous device cookies, phones, emails).
- **HOW**: `IdentityLink` captures `source_id`, `target_id`, `link_reason`, `confidence_score`, `status` (`active`, `reversed`), and `evidence_event_id`.
- **WHY**: Avoids permanent schema merges. When multiple users share a device, links can be reversed without corrupting historical event data.

---

## 3. Analytical & Decision Engines (`engines/`)

### 3.1 Grounded Deterministic Metrics Engine ([engines/metrics_engine.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/metrics_engine.py))

- **WHAT**: Core computation engine that calculates exact e-commerce metrics from raw events with zero LLM involvement.
- **HOW**: Implements 9 mathematical invariants:
  1. Exact Ratios:
     $$\text{Cart Abandonment Rate} = 1.0 - \frac{\text{Sessions with Completed Checkout}}{\text{Sessions with Cart Additions}}$$
     $$\text{Step } k \text{ Drop-Off} = \frac{\text{Sessions at Step } k - \text{Sessions Reaching Step } k+1}{\text{Sessions at Step } k}$$
  2. Session Maturity Guard: Excludes sessions opened in the last 15 minutes that have not had time to convert.
  3. Strict Watermarking: Filters all queries on `received_at <= as_of`.
  4. Explicit Entity Grouping: Counts unique sessions or customers rather than raw event clicks.
  5. Set-Difference Bound: Guarantees $0 \le \text{numerator} \le \text{denominator}$.
  6. Zero Denominator Safety: Returns `value = None` with status `zero_denominator` (never $0.0$).
  7. Dimension Allowlisting: Rejects arbitrary SQL group-bys to prevent unindexed table scans.
- **WHY**: LLMs often hallucinate arithmetic. Computing metrics deterministically guarantees accuracy and reproducibility.

---

### 3.2 Deterministic Digest & Anomaly Engine ([engines/digest_engine.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/digest_engine.py))

- **WHAT**: Period-over-period comparison engine that identifies statistical anomalies, conversion bottlenecks, and idle carts.
- **HOW**:
  1. Rolling Multi-Period Baselines: Compares the active window against the median of 4 prior matching weekday periods (e.g. comparing Friday evening against the prior 4 Friday evenings).
  2. Two-Proportion Hypothesis Testing:
     Computes pooled standard error and Z-score:
     $$p_{\text{pool}} = \frac{x_1 + x_2}{n_1 + n_2}$$
     $$Z = \frac{p_1 - p_2}{\sqrt{p_{\text{pool}}(1 - p_{\text{pool}})\left(\frac{1}{n_1} + \frac{1}{n_2}\right)}}$$
     Flags an anomaly when $|Z| \ge 2.5$ ($p < 0.01$) and relative change exceeds threshold.
  3. Financial Impact Ranking:
     Estimates revenue impact using Average Order Value (AOV):
     $$\text{Revenue Impact} = (\text{Expected Conversions} - \text{Actual Conversions}) \times \text{AOV}$$
  4. Funnel Bottleneck Isolation: Correlates funnel drops to isolate the root-cause stage (e.g. payment gateway failure vs address entry friction).
- **WHY**: Percentage changes can be misleading with small sample sizes (e.g. 1 out of 2 is a 50% drop, but not statistically significant). The two-proportion test filters out random noise and surfaces true anomalies.

---

### 3.3 Anti-Hallucination Evidence Linker ([engines/evidence_linker.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/evidence_linker.py))

- **WHAT**: Post-generation verification gate that audits LLM-generated summaries against computed metrics.
- **HOW**:
  1. Numeric Claim Extraction: Regex-extracts all numbers, percentages, and currencies from generated sentences.
  2. Metric Semantic Mapping: Maps sentence phrases (*"cart abandonment"*, *"step 2 friction"*) to canonical metric keys.
  3. Numerical Tolerance Check:
     Reconciles LLM numbers against database ground truth:
     $$\frac{|\text{Claimed Value} - \text{Ground Truth Value}|}{\text{Ground Truth Value}} \le 0.005 \quad (0.5\%)$$
  4. Directional Polarity Verification: Ensures directional terms (*"increased"*, *"rose"*, *"spiked"*) match positive deltas, while (*"dropped"*, *"fell"*) match negative deltas.
  5. Hyperbole Pruning: Removes ungrounded qualitative terms (*"alarming"*, *"catastrophic"*, *"massive"*) lacking statistical support.
- **WHY**: Keeps generative outputs grounded. Even when LLMs hallucinate during edge cases, the EvidenceLinker catches discrepancies before they reach the user.

---

### 3.4 Natural Language Query Engine ([engines/nl_query_engine.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/nl_query_engine.py))

- **WHAT**: Natural language question-answering system over business metrics.
- **HOW**:
  - Classifies user intent into predefined vertical metrics catalogs.
  - Calls `MetricsEngine` to compute current and baseline values.
  - Constructs grounded prompts containing exact metric values for the LLM.
  - Receives structured responses and verifies them through `EvidenceLinker`.
  - Produces structured 3-tier answers.
- **WHY**: **Replaces Text-to-SQL**. Text-to-SQL often invents non-existent columns, struggles with session logic, and exposes databases to SQL injection. Classifying intent to structured metric APIs provides safety and reliability.

---

### 3.5 Deterministic Policy Engine ([engines/policy_engine.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/policy_engine.py))

- **WHAT**: Deterministic gatekeeper that evaluates proposed growth actions against legal, financial, and platform rules.
- **HOW**:
  - Financial Limits: Asserts delivery fee waivers do not exceed max allowed paise (`fee_amount_paise <= max_discount_paise`).
  - Contact Cooldown: Verifies customer has not received promotional messages in the prior 48 hours.
  - Quiet Hours Enforcement: Uses recipient timezones (IST UTC+5:30) to block marketing messages between 9:00 PM and 9:00 AM (TRAI and DPDP compliance).
  - Purpose-Specific Consent: Checks consent records for `marketing_notification` permission.
  - Budget Shift Caps: Caps ad spend shifts at $\le 15\%$ per 24 hours.
- **WHY**: LLMs should not have direct execution authority over financial disbursements or customer communications. Pure deterministic code enforces non-negotiable legal and financial boundaries.

---

### 3.6 Digest Explanation Engine ([engines/digest_explanation_engine.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/digest_explanation_engine.py))
- **WHAT**: Translates statistical anomaly flags into natural language operational digests.
- **HOW**: Combines anomaly metrics, Z-scores, and dimensional breakdowns into prompt contexts for the LLM, producing actionable executive summaries.
- **WHY**: Converts statistical flags into plain language summaries for merchant operators.

---

### 3.7 Heuristic Scoring Engine ([engines/heuristic_scoring.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/heuristic_scoring.py))
- **WHAT**: Computes customer purchase propensity and Customer Lifetime Value (CLTV) scores without heavy machine learning training dependencies.
- **HOW**: 
  - Propensity score: Evaluates cart value, items viewed, session duration, and prior orders.
  - Propensity gating:
    - High propensity ($\ge 0.85$): Suppresses discounts to protect margins.
    - Low propensity ($\le 0.15$): Suppresses outreach to save messaging costs.
    - Medium propensity ($0.15 < p < 0.85$): Qualifies for intervention.
- **WHY**: Protects profit margins by avoiding discounts for customers who intended to purchase anyway.

---

### 3.8 Vertical Industry Templates ([engines/vertical_templates.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/vertical_templates.py))
- **WHAT**: Configuration registry defining metric calculation formulas and entities across industry verticals (`ecommerce_d2c`, `fintech`, `saas`).
- **HOW**: Maps metrics to required events, filter criteria, and denominator entities.
- **WHY**: Enables the system to support new verticals (e.g., loan applications or SaaS onboarding) by adding template definitions without modifying engine code.

---

## 4. Application Services (`services/`)

### 4.1 Action Orchestrator Service ([services/action_orchestrator.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/action_orchestrator.py))

- **WHAT**: Central orchestrator that handles policy evaluation, execution mode routing, and action dispatch.
- **HOW**:
  1. Re-verifies policies immediately prior to dispatch to prevent race conditions.
  2. Routes by execution mode:
     - `MANUAL`: Records draft for human review.
     - `APPROVAL`: Notifies merchant and pauses execution pending approval.
     - `AUTONOMOUS`: Evaluates randomized holdout (10% un-messaged control), records audit trail, and dispatches to outbound adapters.
  3. Claims an idempotency lock on `(tenant_id, plan_id)` to prevent duplicate dispatches.
- **WHY**: Manages the critical handoff between analytical reasoning and external action execution.

---

### 4.2 24-Hour Attribution Closing Worker ([services/attribution_closing_worker.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/attribution_closing_worker.py))

- **WHAT**: Background worker that measures incremental conversion lift between treated and control groups after 24 hours.
- **HOW**:
  - Scans ActionPlans that have passed their 24-hour window.
  - Queries event storage for subsequent `order_completed` events.
  - Calculates true incremental lift:
    $$\text{Incremental Lift} = \text{Treated CVR} - \text{Holdout CVR}$$
  - Logs results to the immutable audit ledger.
- **WHY**: Proves whether interventions drove incremental revenue or simply offered unnecessary discounts.

---

### 4.3 Idle Cart Sweep Worker ([services/idle_cart_sweep_worker.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/idle_cart_sweep_worker.py))
- **WHAT**: Periodic background daemon sweeping for abandoned carts.
- **HOW**: Filters carts idle for $\ge 15$ minutes, resolves user identities, scores propensity, generates `ActionPlan` candidates, and routes through `ActionOrchestrator`.
- **WHY**: Automates cart recovery within the high-intent window while enforcing governance policies.

---

### 4.4 Action Proposer Service ([services/action_proposer.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/action_proposer.py))
- **WHAT**: Bridges anomaly detection and candidate action synthesis.
- **HOW**: Maps detected metric shifts (e.g. checkout step 2 drop-off) to action types (`WAIVE_DELIVERY_FEE`, `FLAG_UI_FRICTION_BUG`).
- **WHY**: Generates candidate actions directly from detected bottlenecks.

---

### 4.5 Approval & Decision Services ([services/approval_service.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/approval_service.py), [services/decision_manager.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/decision_manager.py))
- **WHAT**: Manages merchant approval workflows.
- **HOW**: Provides `approve_plan(plan_id)` and `reject_plan(plan_id)` endpoints that update statuses and resume the `ActionOrchestrator` execution pipeline.
- **WHY**: Enables merchant oversight for high-impact actions.

---

### 4.6 Merchant Query Service ([services/merchant_query_service.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/services/merchant_query_service.py))
- **WHAT**: Application facade for the natural language query pipeline.
- **HOW**: Dispatches queries to `NLQueryEngine` and returns formatted answers to the CLI and frontend dashboard.
- **WHY**: Simplifies client integration with a single query entry point.

---

## 5. Ports & Adapters (Hexagonal Architecture) (`ports/`, `adapters/`)

### 5.1 Google Gemini Live Decision Provider ([adapters/gemini_decision_provider.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/adapters/gemini_decision_provider.py))
- **WHAT**: Production LLM adapter integrating Google Gemini (`gemini-2.5-flash`).
- **HOW**: Uses `GeminiClient` to make API calls with system instructions, structured JSON schemas, temperature 0.1, and execution tracing (latency, tokens).
- **WHY**: Fast execution (~1.8s) and structured outputs make it well-suited for interactive growth diagnostics.

---

### 5.2 Multi-Model OpenRouter Adapter ([adapters/openrouter_decision_provider.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/adapters/openrouter_decision_provider.py))
- **WHAT**: Multi-model evaluation client connecting to Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o, and DeepSeek R1.
- **HOW**: Formats standard OpenAI-compatible completions to evaluate reasoning quality, latency, and cost across providers.
- **WHY**: Prevents vendor lock-in and allows continuous benchmarking across LLM providers.

---

### 5.3 Rule Decision Provider / Degraded Mode ([engines/rule_decision_provider.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/rule_decision_provider.py))
- **WHAT**: Deterministic fallback engine for offline execution and circuit breaking.
- **HOW**: Evaluates signal conditions through hardcoded if-else trees to generate candidate plans when LLM APIs are unavailable.
- **WHY**: Keeps the system operational during network outages or API rate limiting.

---

### 5.4 Relational Identity Resolver ([adapters/sql_identity_resolver.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/adapters/sql_identity_resolver.py))
- **WHAT**: Relational customer identity resolution engine.
- **HOW**: Stores bidirectional linkages in `identity_links`. Resolves canonical customer IDs via recursive path queries without modifying historical telemetry.
- **WHY**: Avoids the operational overhead of a graph database while maintaining full link reversibility.

---

### 5.5 Tamper-Evident Cryptographic Audit Ledger ([adapters/sql_audit_ledger.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/adapters/sql_audit_ledger.py))
- **WHAT**: Append-only audit logger using SQLite triggers.
- **HOW**: 
  - SQLite triggers fail on any `UPDATE` or `DELETE` attempt.
  - Chains records cryptographically:
    $$\text{record\_hash} = \text{SHA256}(\text{prev\_hash} + \text{plan\_id} + \text{action\_diff} + \text{timestamp})$$
  - Redacts PII (emails, phone numbers) before persistence.
- **WHY**: Provides an immutable, verifiable audit log required for enterprise compliance.

---

### 5.6 Outbound Adapters: Ads, Loyalty, Notifications ([adapters/http_ads_adapter.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/adapters/http_ads_adapter.py), etc.)
- **WHAT**: Outbound integration adapters that communicate with external systems.
- **HOW**:
  - `http_ads_adapter`: Calls Module 3 to create campaigns or shift budgets.
  - `loyalty_waivers_adapter`: Applies fee waivers to storefront carts.
  - `notification_gateway_adapter`: Sends recovery WhatsApp messages via transactional gateways.
- **WHY**: Follows hexagonal architecture principles by isolating core logic from third-party API dependencies.

---

## 6. Evaluation & Benchmark Suite (`evaluation/`)

### 6.1 Provider Evaluator ([evaluation/evaluator.py](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/evaluation/evaluator.py))

- **WHAT**: Automated evaluation harness measuring decision accuracy, hallucination rates, and latency.
- **HOW**: Evaluates decision providers against ground-truth benchmark cases across 4 metrics:
  1. Ground-Truth Action Precision (correct action selected).
  2. Parameter Accuracy (integer paise and limits preserved).
  3. Evidence Grounding Precision (zero hallucinations).
  4. Response Latency ($p_{50}$, $p_{95}$).
- **WHY**: Continuous automated evaluation prevents prompt regressions and guarantees model reliability across releases.
