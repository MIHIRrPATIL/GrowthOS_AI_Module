# GrowthOS: AI Growth Brain (Module 4)

GrowthOS Module 4 is an autonomous e-commerce growth intelligence engine that bridges raw behavioural telemetry with verified, fact-grounded decisions, metric digests, and natural language query capabilities.

---

## Key Architecture & Capabilities

1. **Zero-Hallucination Natural Language Query Engine**:
   - Classifies merchant questions into deterministic analytical intents (`FUNNEL_DROP_OFF`, `PERIOD_COMPARISON`, `METRIC_LOOKUP`, `UNSUPPORTED`).
   - Translates questions into structured metrics catalog lookups—eliminating free-form unconstrained SQL generation.
   - Multi-tier response contract:
     - **Tier 1**: Executive Summary (merchant-facing natural language digest).
     - **Tier 2**: Analytical Breakdown (exact ratios, dual percentage points & relative changes, excess lost drop-off volume, and two-proportion pooled z-tests).
     - **Tier 3**: Technical Trace & Audit Envelope (provenance window, metric status, model, provider, degraded flag, and cryptographically verifiable evidence references).

2. **Statistical Metric Digest & Fact-Grounded Narration**:
   - Automated period-over-period anomaly detection across 11 core e-commerce metrics.
   - Empirical ranking by **excess lost sessions / orders** ($+23.1$ sessions for Step 2 vs $+18.0$ for Step 1).
   - Strict anti-hallucination gate auditing all claims against computed numbers and directional deltas before display.

3. **Multi-Provider Decision Engine Behind `DecisionPort`**:
   - Supports Google Gemini direct API (`gemini-3.5-flash`, `gemini-2.5-flash-lite`), OpenRouter (`google/gemini-2.5-flash`), and deterministic rule fallback.
   - Automated circuit breaker cooldowns with intelligent free-tier model rotation pool.
   - Pre-filtering of ineligible carts (sub-INR 300, anonymous sessions, under-idle threshold) to consume zero external API calls.

4. **Closed-Loop Action Governance & Orchestration**:
   - All proposed actions traverse [ActionOrchestrator](research/ai-module/services/action_orchestrator.py), [PolicyEngine](research/ai-module/services/policy_engine.py), [AuditLedger](research/ai-module/services/audit_ledger.py), and [ApprovalWorkflow](research/ai-module/services/approval_workflow.py).
   - Enforces randomized holdout controls (10% control group) and frequency limits (max 1 waiver per customer per 7 days).

---

## Directory Structure

```
research/ai-module/
├── adapters/          # Direct HTTP clients for Google Gemini & OpenRouter, SQL storages, consent stores
├── domain/            # Core business models (metrics, events, actions, evaluation, NLP)
├── engines/           # Metrics calculation, digest explanation, policy rules, evidence linking
├── ports/             # Clean hexagonal ports (decision, LLM, storage, consent, identity)
├── services/          # Orchestrators, approval workflows, audit ledgers, query processors
├── evaluation/        # Ground-truth datasets & multi-provider benchmark harness
├── tests/             # Comprehensive pytest test suite (141 tests, 100% pass rate)
├── demo_gemini_live.py       # Live demonstration runner with failover & circuit breaker protection
└── demo_openrouter_live.py   # Live OpenRouter demonstration runner
```

---

## Quick Start & Verification

### 1. Environment Setup
```bash
cd research/ai-module
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configure your GEMINI_API_KEY or OPENROUTER_API_KEY in .env
```

### 2. Run Test Suite
```bash
pytest tests/
```

### 3. Run Live Demonstrations
```bash
# Run with direct Google Gemini integration
python3 demo_gemini_live.py --require-live

# Run with OpenRouter integration
python3 demo_openrouter_live.py --require-live
```
