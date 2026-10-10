# GrowthOS: Autonomous E-Commerce Growth Operating System

GrowthOS is an end-to-end autonomous e-commerce growth platform uniting granular client-side behavior intelligence, deterministic metric analytics, closed-loop advertising orchestration, and policy-governed AI decision synthesis.

---

## Unified Architecture Overview

```
                               GROWTHOS ARCHITECTURE
                               
   +--------------------------------------------------------------------------+
   |                  MODULE 2: BEHAVIOR INTELLIGENCE & STOREFRONT            |
   |                                                                          |
   |   [Next.js Storefront]     [TypeScript SDK]        [Chrome QA Extension] |
   |   (research/frontend)      (research/sdk)          (research/qa-debugger)|
   |            |                      |                          |           |
   |            +----------------------+--------------------------+           |
   |                                   |                                      |
   |                       HTTP Batch / HMAC Telemetry                        |
   +-----------------------------------|--------------------------------------+
                                       v
   +--------------------------------------------------------------------------+
   |                        MODULE 4: AI GROWTH BRAIN                         |
   |                           (research/ai-module)                           |
   |                                                                          |
   |   [Telemetry Ingestion]   --> [MetricsEngine]    --> [DigestEngine]      |
   |   (HMAC drift verify)         (11 core metrics)      (anomaly detection) |
   |                                                              |           |
   |   [EvidenceLinker]        <-- [DecisionManager]  <-- [NLQueryEngine]     |
   |   (0.5% tolerance audit)      (Gemini / Rules)       (intent parser)     |
   |                                       |                                  |
   |                               Action Proposals                           |
   |                                       v                                  |
   |   [ActionOrchestrator]    --> [PolicyEngine]     --> [AuditLedger]       |
   |   (holdout assignment)        (financial limits)     (immutable trail)   |
   +---------------------------------------|----------------------------------+
                                           |
                       Outbound Action Contract / HTTP Port
                                           v
   +--------------------------------------------------------------------------+
   |                  MODULE 3: ADS LAYER & OPTIMIZATION                      |
   |                          (research/Ads-Module)                           |
   |                                                                          |
   |   [PlanningEngine]        --> [ValidationEngine] --> [DeploymentService] |
   |   (keyword cluster / RSA)     (editorial policy)     (Google Ads API)    |
   |                                                              |           |
   |   [Attribution Engine]    <-- [ClickTracker]     <-- [OptimizationEngine]|
   |   (GCLID 30d lookback)        (offline upload)       (<= 15% budget shift|
   |                                                       & rollback service)|
   +--------------------------------------------------------------------------+
```

---

## Modular Subsystems

### 1. Module 2: Behavior Intelligence SDK & Storefront
- **Directory**: `research/sdk`, `research/frontend`, `research/merchant-dashboard`, `research/backend-bridge`, `research/qa-debugger`, `research/tests`
- **Core Role**: Captures millisecond-level customer intent signals (rage clicks, mouse thrashing, typing cadence, scroll milestones, form field dwell) with zero PII leakage (Luhn validation, password redaction, DOM masking).
- **Storefront**: High-fidelity Domino's Pizza India e-commerce application built on Next.js 16 with integrated QA inspection overlays.

### 2. Module 3: Ads Layer & Autonomous Optimization
- **Directory**: `research/Ads-Module`
- **Core Role**: Autonomous campaign management and execution layer.
- **Key Engines**:
  - **CampaignPlanningEngine**: Synthesizes structured campaigns, keyword clusters, and Responsive Search Ads (RSA) adhering to strict character constraints (headlines <= 30 chars, descriptions <= 90 chars).
  - **CampaignValidationEngine**: Pre-flight validation gate checking budget minimums, target CPA safety bounds, and Google Ads editorial policies.
  - **Closed-Loop Attribution**: GCLID click tracking, 30-day conversion lookback, and offline conversion upload to Google Ads.
  - **Autonomous Optimization**: Identifies underperforming campaigns and reallocates budget under a strict invariant limiting daily shifts to <= 15%.
  - **Rollback Service**: Single-click atomic restoration of previous campaign budget allocations.

### 3. Module 4: AI Growth Brain
- **Directory**: `research/ai-module`
- **Core Role**: Analytical intelligence and decision engine.
- **Key Engines**:
  - **Deterministic MetricsEngine**: Calculates 11 core e-commerce metrics and funnel drop-offs with zero LLM hallucination risk.
  - **EvidenceLinker**: Enforces mathematical fact verification, ensuring all natural language claims fall within 0.5% relative tolerance of empirical data.
  - **DecisionManager & Multi-Provider Evaluation**: Integrates Google Gemini (`gemini-2.5-flash`), OpenRouter, and offline rule baselines with automated circuit breakers and Wilson Score confidence bounds.
  - **Governance Layer**: Enforces financial limits, purpose-specific consent, quiet hours, cooldowns, and immutable audit ledgers.

---

## Directory Layout

```
GrowthOS/
├── backend/                       # Legacy backend services
├── frontend/                      # Root frontend entrypoints
├── growthos_cli.sh                # Executable script for interactive presentation CLI
├── pyrightconfig.json             # Pyright static typing configuration
├── research/
│   ├── Ads-Module/                # Module 3: Ads Layer, Connectors, Attribution & Optimization
│   ├── ai-module/                 # Module 4: AI Growth Brain, Analytical Engines, Governance
│   ├── backend-bridge/            # Module 2: Telemetry Ingestion Bridge & Customer Graph
│   ├── docs/                      # Architectural specifications and taxonomy definitions
│   ├── frontend/                  # Module 2: Next.js 16 E-Commerce Storefront
│   ├── merchant-dashboard/        # Module 2: Next.js Merchant Analytics Dashboard
│   ├── qa-debugger/               # Module 2: Chrome DevTools Extension
│   ├── sdk/                       # Module 2: TypeScript Behavior Intelligence SDK
│   ├── tests/                     # Module 2: Playwright E2E Integration Suite
│   ├── GrowthOS_overview.md       # Comprehensive System Architecture Whitepaper
│   ├── README.md                  # Research Directory Documentation
│   ├── growthos_cli.py            # Unified Presentation CLI for Ads & AI Modules
│   └── run_full_system_test_suite.py # End-to-End System Test Harness
└── skills-lock.json               # IDE skills configuration
```

---

## Quick Start & Verification

### 1. Run Unified System Test Harness
Validates all subsystems end-to-end (Telemetry -> MetricsEngine -> Gemini LLM -> EvidenceLinker -> CampaignPlanning -> Validation -> Attribution -> Optimization):
```bash
./research/ai-module/.venv/bin/python research/run_full_system_test_suite.py
```

### 2. Launch Interactive GrowthOS Presentation CLI
Interactive terminal demonstrating live Gemini insights, campaign synthesis, validation gates, and budget rebalancing:
```bash
./growthos_cli.sh
# or
./research/ai-module/.venv/bin/python research/growthos_cli.py
```

### 3. Run Subsystem Unit Test Suites
```bash
# Module 4 AI Unit Tests (174 tests)
./research/ai-module/.venv/bin/pytest research/ai-module/tests/ -v

# Module 3 Ads Unit Tests (36 tests)
./research/ai-module/.venv/bin/pytest research/Ads-Module/tests/ -v
```

