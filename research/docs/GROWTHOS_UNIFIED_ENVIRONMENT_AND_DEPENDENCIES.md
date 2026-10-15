# GrowthOS Unified Environment & Dependency Architecture

## 1. Overview & Consolidation Summary

GrowthOS previously maintained fragmented environment and configuration boundaries:
- Independent virtual environments across `research/ai-module/.venv` and `research/backend-bridge/.venv`, leading to missing dependency errors (e.g. `numpy` or `networkx` missing depending on which directory was activated).
- Split `requirements.txt` across `research/Ads-Module/`, `research/ai-module/`, and `research/backend-bridge/`.
- Isolated `.env` files across `research/ai-module/.env`, `research/Ads-Module/.env`, `research/backend-bridge/.env`, and `research/frontend/.env.local`.

All environments, dependency specifications, and environment configurations are now consolidated into a **single source of truth** at the repository root.

---

## 2. Unified Virtual Environment Architecture

The master virtual environment resides at:
```
/home/mihir/Codes/internship/GrowthOS/.venv
```

Subsystem directories maintain backward-compatible symbolic links pointing to this root virtual environment:
- `research/ai-module/.venv -> ../../.venv`
- `research/backend-bridge/.venv -> ../../.venv`

### Activation
Regardless of current working directory, activating via standard shell commands attaches to the unified environment:
```bash
# From workspace root
source .venv/bin/activate

# From subdirectories
source .venv/bin/activate
```

---

## 3. Consolidated Requirements Specification

The canonical requirements specification is located at:
```
/home/mihir/Codes/internship/GrowthOS/requirements.txt
```

Child modules point directly to this master specification via symlinks:
- `research/requirements.txt -> ../requirements.txt`
- `research/Ads-Module/requirements.txt -> ../../requirements.txt`
- `research/ai-module/requirements.txt -> ../../requirements.txt`
- `research/backend-bridge/requirements.txt -> ../../requirements.txt`

### Package Taxonomy
1. **Core Web Framework & Asynchronous HTTP**:
   - `fastapi>=0.115.0`
   - `uvicorn>=0.34.0`
   - `pydantic>=2.10.0`
   - `httpx>=0.28.0`
   - `python-dotenv>=1.0.0`
2. **Simulation & Graph Mathematics**:
   - `numpy>=1.24.0`
   - `networkx>=3.0.0`
   - `pyyaml>=6.0.0`
3. **Testing & Test Suites**:
   - `pytest>=8.0.0`
4. **Google Ads SDK (Module 3)**:
   - `google-ads>=24.0.0`

---

## 4. Unified Environment Configuration (`.env`)

The single master configuration file resides at:
```
/home/mihir/Codes/internship/GrowthOS/.env
```
Template with non-secret defaults:
```
/home/mihir/Codes/internship/GrowthOS/.env.example
```

Module configuration paths link directly to the unified root `.env`:
- `research/.env -> ../.env`
- `research/ai-module/.env -> ../../.env`
- `research/Ads-Module/.env -> ../../.env`
- `research/backend-bridge/.env -> ../../.env`
- `research/frontend/.env.local -> ../../.env`

### Variable Scope Across Modules
- **AI Growth Brain (Module 4)**:
  - `OPENROUTER_API_KEY`: OpenRouter gateway key
  - `OPENROUTER_MODEL`: Model slug (e.g. `google/gemini-2.5-flash`)
  - `GEMINI_API_KEY`: Direct Google AI Studio Gemini API key
  - `GEMINI_MODEL`: Model name (e.g. `gemini-2.5-flash`)
- **Google Ads Engine (Module 3)**:
  - `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`
  - `GOOGLE_ADS_DEVELOPER_TOKEN`
  - `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, `GOOGLE_ADS_CLIENT_CUSTOMER_ID`
  - `GOOGLE_ADS_USE_PROTO_PLUS`
- **Telemetry & Storefront Bridge**:
  - `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`
  - `NEXT_PUBLIC_GROWTHOS_PROJECT_ID`, `NEXT_PUBLIC_GROWTHOS_WORKSPACE_ID`
  - `NEXT_PUBLIC_GROWTHOS_API_HOST`, `GROWTHOS_API_HOST`

---

## 5. Verification & Health Check

All 216 test cases in the test suite and end-to-end integration runners execute against this single unified environment:
```bash
# 1. Run all AI Module unit and contract tests (216 tests)
.venv/bin/pytest research/ai-module/tests

# 2. Run full system test suite with live LLM verification
.venv/bin/python3 research/run_full_system_test_suite.py

# 3. Run presentation CLI simulator test
.venv/bin/python3 research/growthos_cli.py --sim-only --seed 86631524
```
All tests pass cleanly with zero regressions.
