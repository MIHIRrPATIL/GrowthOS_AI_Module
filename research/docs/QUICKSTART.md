# GrowthOS Quick Start & CLI Runner Guide

This guide details how to set up the unified environment, install dependencies, configure credentials, and run the Python presentation CLI.

---

## 1. Where to Create the Virtual Environment (`.venv`)

GrowthOS uses a **single unified virtual environment** at the repository root. All submodules (`research/ai-module`, `research/Ads-Module`, `research/backend-bridge`) are symlinked to this root environment.

From the repository root (`/home/mihir/Codes/internship/GrowthOS`):

```bash
# 1. Create the virtual environment at the repository root
python3 -m venv .venv

# (Alternative using uv if installed):
# uv venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate
```

> [!NOTE]
> Always activate from the root (`source .venv/bin/activate`). Do not create separate virtual environments inside `research/ai-module` or `research/backend-bridge`, as the symlinks automatically forward all execution to root `.venv`.

---

## 2. What Requirements File to Install (`requirements.txt`)

Install the master unified requirements document located at the repository root:

```bash
# With virtual environment activated:
pip install -r requirements.txt

# (Alternative ultra-fast install using uv):
# uv pip install -r requirements.txt
```

### What this installs:
- **Core Web & Async HTTP**: `fastapi`, `uvicorn`, `pydantic`, `httpx`, `python-dotenv`
- **Telemetry & Mathematics**: `numpy`, `networkx`, `pyyaml`
- **Testing & Quality Assurance**: `pytest`
- **Ad Platform Integration**: `google-ads`

> [!TIP]
> The requirements files in `research/ai-module/requirements.txt`, `research/Ads-Module/requirements.txt`, and `research/backend-bridge/requirements.txt` are symbolic links pointing directly to the root `requirements.txt`.

---

## 3. Where to Create the Configuration File (`.env`)

Create the single consolidated `.env` configuration file at the **repository root**:

```bash
# Copy the provided template to create your .env
cp .env.example .env
```

Edit `.env` to supply your API keys:

```env
# 1. AI Growth Brain & LLM API Configuration (Module 4)
OPENROUTER_API_KEY="sk-or-v1-your-key-here"
OPENROUTER_MODEL="google/gemini-2.5-flash"

GEMINI_API_KEY="AQ.your-google-ai-studio-gemini-key"
GEMINI_MODEL="gemini-2.5-flash"

# 2. Google Ads API Credentials (Module 3)
GOOGLE_ADS_CLIENT_ID="your_client_id.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET="your_client_secret"
GOOGLE_ADS_REFRESH_TOKEN="your_refresh_token"
GOOGLE_ADS_DEVELOPER_TOKEN="placeholder_token"
GOOGLE_ADS_LOGIN_CUSTOMER_ID="9868819237"
GOOGLE_ADS_CLIENT_CUSTOMER_ID="7428481017"
GOOGLE_ADS_USE_PROTO_PLUS="True"

# 3. PostHog Telemetry & Ingestion
NEXT_PUBLIC_POSTHOG_KEY="your_posthog_key"
NEXT_PUBLIC_POSTHOG_HOST="https://us.i.posthog.com"

# 4. GrowthOS Core System & Backend Bridge
NEXT_PUBLIC_GROWTHOS_PROJECT_ID="proj_dominos_01"
NEXT_PUBLIC_GROWTHOS_WORKSPACE_ID="ws_dominos_in"
NEXT_PUBLIC_GROWTHOS_API_HOST="http://localhost:8000"
GROWTHOS_API_HOST="http://localhost:8000"
```

> [!IMPORTANT]
> All submodules (`research/.env`, `research/ai-module/.env`, `research/Ads-Module/.env`, `research/backend-bridge/.env`, `research/frontend/.env.local`) link directly to root `.env`. Updating root `.env` updates all modules simultaneously.

---

## 4. How to Start the Python CLI Runner (Not the Shell Script)

Execute the Python script directly using Python 3 from the activated virtual environment. Do not invoke `growthos_cli.sh`.

### Method A: From the Repository Root (Recommended)

```bash
source .venv/bin/activate
python3 research/growthos_cli.py
```

### Method B: From the `research/` Subdirectory

```bash
source .venv/bin/activate
cd research
python3 growthos_cli.py
```

---

## 5. CLI Execution Modes & Flags

The Python runner supports command-line arguments for reproducible simulations and debugging:

| Command | Purpose |
|---|---|
| `python3 research/growthos_cli.py` | Interactive standard scenario runner with random seed |
| `python3 research/growthos_cli.py --seed 86631524` | Deterministic reproducible run using a specific seed |
| `python3 research/growthos_cli.py --reveal` | Reveals planted effects and hidden generator ground truth upfront |
| `python3 research/growthos_cli.py --sim-only --seed 86631524` | Non-interactive test: prints scenario card, saves artifacts, reveals ground truth, and exits |
| `python3 research/growthos_cli.py --size small` | Runs a lightweight scenario (~3,000 sessions/day) |
| `python3 research/growthos_cli.py --size stress` | Runs a high-load scenario (~50,000 sessions/day) |

---

## 6. Navigating the Interactive CLI

When launched, the CLI displays the scenario header card and the presentation menu:

```
================================================================================
                      GROWTHOS PRESENTATION CLI                      
             Autonomous Closed-Loop E-Commerce Growth Operating System        
================================================================================
1. Module 3: Ads Module (Interactive Campaign Planning & Deployment)
2. Module 4: AI Growth Brain (Natural Language Analytics & 3-Tier Q&A)
3. Combined Pipeline: End-to-End Autonomous Growth Closed Loop
4. Autonomous Budget Rebalancing & 1-Click Rollback Demo
5. Exit
--------------------------------------------------------------------------------
```

### Menu Options Overview:
1. **Option 1 (Module 3 Ads Planning)**:
   - Synthesizes keyword clusters, negative keywords, character-bounded RSA copy (headlines <= 30 chars, descriptions <= 90 chars), runs validation engine checks, and simulates deployment to Google Ads API.
2. **Option 2 (Module 4 AI Growth Brain Q&A)**:
   - Natural language business intelligence interface.
   - Choose provider mode:
     - `1`: Gemini Live API (`gemini-2.5-flash`)
     - `2`: OpenRouter Live API (`google/gemini-2.5-flash`)
     - `3`: Offline Deterministic Provider (instant, zero latency, zero network tokens needed)
   - Select preset questions or enter custom questions to receive 3-tier answers (Executive Summary, Analytical Breakdown, Technical Evidence Citations grounded within 0.5% tolerance).
3. **Option 3 (Combined Closed-Loop Pipeline)**:
   - Full autonomous feedback loop:
     Storefront Telemetry -> AI Brain Anomaly Detection -> Ad Action Synthesis -> Campaign Validation Gate -> Merchant Approval Gate -> Deployment -> Click Attribution (GCLID) -> Purchase Conversion -> Closed-Loop Attribution -> Autonomous Budget Rebalancing.
4. **Option 4 (Autonomous Budget Rebalancing & 1-Click Rollback)**:
   - Demonstrates bleeder detection (campaigns underperforming target CPA), automated <= 15% daily budget shifts into top-performing winner campaigns, and instant 1-click snapshot restoration.
5. **Option 5 (Exit)**:
   - Exits CLI and reveals the hidden ground truth generator ledger.

---

## 7. Quick Smoke Test

To verify your installation in under 10 seconds:

```bash
# 1. Run unit test suite (216 tests)
.venv/bin/pytest research/ai-module/tests -q

# 2. Run end-to-end integration test suite
.venv/bin/python3 research/run_full_system_test_suite.py

# 3. Run non-interactive CLI simulation
.venv/bin/python3 research/growthos_cli.py --sim-only --seed 86631524
```
