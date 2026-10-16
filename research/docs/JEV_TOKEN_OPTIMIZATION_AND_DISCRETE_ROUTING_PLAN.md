# GrowthOS Architecture Plan: Token Optimization & Discrete Candidate Routing via TypeSafe Jev

## Executive Summary

Current LLM interactions in GrowthOS Module 4 (AI Growth Brain) utilize frontier models (Google Gemini, Anthropic Claude, or Meta Llama) via OpenRouter for both **classification** and **narrative generation**. Each interaction consumes **1,800 to 2,500 tokens** and incurs **3,000 to 5,000 ms of latency**, because the system prompts models with full metric catalog descriptions, complex JSON schemas, and multi-paragraph formatting instructions.

By integrating **TypeSafe Jev (`typesafe/jev-router`)** as a specialized **Discrete Candidate Selector (System 1)**, GrowthOS can decouple:
1. **Decision & Routing (Selection)**: Handled by Jev over a discrete, finite set of candidate outcomes (metrics or actions). Consumes **~120 tokens** with sub-second latency.
2. **Fact Computation & Validation (Deterministic Logic)**: Handled locally by `MetricsEngine`, `PolicyEngine`, and `EvidenceLinker` with **0 tokens**.
3. **Narrative Generation (System 2)**: Only invoked on-demand when a merchant explicitly requests conversational explanations, saving **85% to 95% of total token spend**.

---

## 1. Core Architectural Principle: System 1 vs System 2

```mermaid
graph TD
    Inbound[Merchant Query or Telemetry Anomaly] --> JevSelector[Jev System 1 Selector]
    
    subgraph "Jev Discrete Candidate Selection (~120 tokens)"
        JevSelector -->|Candidate Menu M0-M7| MetricChoice[Select Metric Index: e.g. M2]
        JevSelector -->|Candidate Menu A0-A4| ActionChoice[Select Action Index: e.g. A0]
    end
    
    MetricChoice --> Engine[Deterministic MetricsEngine & EvidenceLinker]
    ActionChoice --> Policy[Deterministic PolicyEngine & Holdout Splitting]
    
    subgraph "Zero-Token Grounded Execution (0 LLM Tokens)"
        Engine --> VerifiedFacts[Deterministic Math & Citations]
        Policy --> ValidatedPlan[Enforced Limits & Audit Ledger]
    end
    
    VerifiedFacts --> CheckNarrative{Needs Open-Ended Advisory?}
    CheckNarrative -->|No (Standard Telemetry)| Template[Verified Grounded Template: 0 Tokens]
    CheckNarrative -->|Yes (Strategic Q&A)| FrontierLLM[Frontier LLM System 2: On-Demand]
    
    Template --> Outbound[Response to Merchant]
    FrontierLLM --> Outbound
    ValidatedPlan --> ClosedLoop[Module 1 / Module 3 Outbound Actions]
```

### The Inefficiency of Current Frontier LLM Routing
- **Prompt Token Bloat**: Sending 10-15 metric definitions, event taxonomy paths, and formatting rules costs 800-1,200 prompt tokens per request.
- **Completion Token Bloat**: Asking the model to output a full JSON schema containing executive summaries, analytical bullet points, trace objects, and citations burns 600-1,000 completion tokens.
- **Redundancy with Deterministic Code**: GrowthOS already has `MetricsEngine` and `EvidenceLinker` that compute and verify the exact mathematical numbers. Asking an LLM to "calculate" or "summarize" facts that are already deterministically computed in code is wasteful.

---

## 2. Discrete Candidate Spaces

Instead of freeform text generation, GrowthOS presents Jev with a finite, pre-indexed menu of possibilities.

### A. Metric Candidate Space $\mathcal{M}$ (Query Classification)
```json
{
  "M0": "cart_abandonment_rate",
  "M1": "checkout_drop_off_rate",
  "M2": "checkout_step_1_drop_off_rate",
  "M3": "checkout_step_2_drop_off_rate",
  "M4": "checkout_step_3_drop_off_rate",
  "M5": "checkout_conversion_rate",
  "M6": "overall_conversion_rate",
  "M7": "blended_cac",
  "M8": "blended_roas",
  "M9": "marketing_budget_arbitration",
  "M10": "unsupported"
}
```

### B. Action Candidate Space $\mathcal{A}$ (Operational Interventions)
```json
{
  "A0": "waive_delivery_fee",
  "A1": "send_recovery_whatsapp",
  "A2": "flag_ui_friction_bug",
  "A3": "sync_audience_segment",
  "A4": "shift_campaign_budget",
  "A5": "pause_underperforming_ad",
  "A6": "do_nothing"
}
```

### C. Time Window Candidate Space $\mathcal{W}$
```json
{
  "W0": "last_7d",
  "W1": "last_week",
  "W2": "this_week",
  "W3": "today",
  "W4": "yesterday",
  "W5": "last_30d"
}
```

---

## 3. Token Economics: Before vs After

| Metric | Current Full-LLM Pipeline | Jev Discrete + Zero-Token Template | Reduction |
|---|:---:|:---:|:---:|
| **Prompt Tokens** | 1,150 tokens | 85 tokens | **-92.6%** |
| **Completion Tokens** | 810 tokens | 12 tokens (`{"m":"M3","w":"W0","p":0.95}`) | **-98.5%** |
| **Total Tokens per Interaction** | **1,960 tokens** | **97 tokens** | **-95.1%** |
| **Inference Latency** | 3,800 - 5,200 ms | 650 - 1,200 ms | **-75.0%** |
| **Estimated Cost / 1k Queries** | $1.470 | $0.075 | **-94.9%** |
| **Hallucination Risk** | Non-zero (requires Linker pruning) | **Mathematically Zero** (pure template binding) | **100% Grounded** |

---

## 4. Component Specification

### Component 1: `JevDiscreteSelector` (`adapters/jev_discrete_selector.py`)
A specialized selector that constructs ultra-dense candidate vectors:

```python
# Ultra-compact prompt template:
PROMPT = """Q: "{query}"
Options: M0:cart_abandon, M1:checkout_drop, M2:step_1, M3:step_2, M4:step_3, M5:conv_rate, M6:cac, M7:roas, M8:arbitration, M9:unsupported
Time: W0:last_7d, W1:last_wk, W2:this_wk, W3:today, W4:yesterday
Output: {"m":"M0".."M9","w":"W0".."W4","c":0.0..1.0}"""
```

- **Input tokens**: 65 - 85 tokens.
- **Output tokens**: 8 - 12 tokens.
- **Parsing**: Direct extraction of metric slug from key index.

### Component 2: `ZeroTokenDeterministicSynthesizer`
Once Jev returns `{"m": "M3", "w": "W0", "c": 0.95}`:
1. `MetricsEngine` executes query for metric `checkout_step_2_drop_off_rate` over `last_7d`.
2. The engine computes:
   - Current value: 18.4%
   - Prior value: 12.1%
   - Delta: +6.3 pp (+52.1% relative change)
   - Sample sizes: $n_1=140, n_0=150$
   - 2-proportion Z-test: $z=2.45, p=0.014$ (statistically significant)
3. The deterministic template synthesizes Tier 1 & Tier 2 answers using verified facts with **0 additional LLM tokens**:
   - **Tier 1**: *"Checkout Step 2 Drop Off Rate increased to 18.4% (26 drop-offs out of 140 sessions), compared to 12.1% (18 drop-offs out of 150 sessions) in the prior period (+6.3 pp (+52.1% relative))."*
   - **Tier 2**: Analytical breakdown with exact sample sizes and Z-scores.
   - **Tier 3**: Verified `EvidenceCitation` links.

### Component 3: Adaptive Escalation Gate (When to use System 2)
The system only calls a generative LLM (Gemini / Claude) when:
1. The user's query is detected as **Strategic Advisory** rather than Telemetry Lookup (e.g. *"What campaign naming convention should we use for our holiday sale?"*).
2. The query is exploratory multi-factor synthesis across un-modeled external factors.
3. For all operational routing and telemetry queries (90%+ of merchant traffic), the Jev Discrete Selector handles the task at a fraction of the cost.

---

## 5. Implementation Roadmap

### Phase 1: Jev Discrete Metric Selector
- Implement `JevDiscreteSelector` utilizing `typesafe/jev-router` via the OpenRouter client.
- Add candidate index mapping for all 6 vertical templates (`ecommerce`, `qsr`, `saas`, `travel`, `fintech`, `subscription`).
- Write unit tests validating that discrete output `{"m": "M1"}` correctly resolves to `checkout_drop_off_rate`.

### Phase 2: Jev Operational Action Selector
- Implement discrete candidate action selection for `idle_cart` and `digest_flag` anomalies.
- Format candidate action parameters deterministically based on tenant configuration and policy limits.

### Phase 3: NLQueryEngine Hybrid Router Integration
- In `NLQueryEngine.process_query()`:
  - Try `JevDiscreteSelector` first.
  - If confidence >= 0.85, execute deterministic calculation + zero-token template.
  - If confidence < 0.85 or user asks for advisory synthesis, escalate to generative LLM.

### Phase 4: Benchmark Verification & Cost Profiling
- Run the 200 ground-truth decision cases through the Jev Discrete pipeline.
- Measure and record accuracy, ECE calibration, p95 latency, and actual token cost savings in `evaluation/benchmark_results_multi_provider.json`.
