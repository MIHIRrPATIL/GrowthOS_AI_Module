# GrowthOS Research & Prototyping Directory

This directory contains research, architectural prototypes, specifications, and automated test suites for **GrowthOS Module 2 (Behavior Intelligence SDK & Pipeline)** and its interface with **Module 4 (AI Growth Brain)**.

---

## Directory Structure

```
research/
├── docs/
│   ├── GROWTHOS_MODULE2_SYSTEM_ARCHITECTURE.md # Comprehensive System Architecture & Operational Guide
│   ├── module2_architecture_decision.md        # ADR: PostHog Engine + GrowthOS Facade Wrapper & Signal Extraction
│   └── event_taxonomy_spec.md                  # Complete Canonical Event & Signal Taxonomy Specification
├── frontend/                                   # Production Next.js 16 E-Commerce Storefront (Domino's Experience)
│   ├── src/app/                                # App Router: Home, Checkout, Order Tracking
│   ├── src/components/                         # PizzaCard, PizzaCustomizerModal, CartDrawer, QAOverlay
│   ├── src/context/                            # CartContext, GrowthOSProvider
│   └── src/data/                               # Domino's Pizza India official menu & pricing
├── sdk/
│   ├── src/                                    # Full TypeScript SDK Source Code
│   │   ├── growthos.ts                         # Public GrowthOS facade & singleton
│   │   ├── validator.ts                        # PII sanitization (Luhn check, password redaction, data-growthos-mask)
│   │   ├── session.ts                          # Inactivity sessionization, device, and UTM attribution
│   │   ├── transport.ts                        # Queueing, batching, exponential backoff, sendBeacon on unload
│   │   ├── capture/                            # Exhaustive capture modules
│   │   │   ├── pageview.ts                     # Pageviews & SPA history transitions (pushState/replaceState/popstate)
│   │   │   ├── autocapture.ts                  # Click, element hierarchy, text content, data-growthos-* attributes
│   │   │   ├── forms.ts                        # Form lifecycle (started, field focus/blur, changed, submit, abandon)
│   │   │   ├── scroll.ts                       # Scroll depth milestones (25%, 50%, 75%, 90%, 100%) & direction
│   │   │   ├── ux_signals.ts                   # Rage clicks, dead clicks, error clicks, mouse thrashing, exit intent
│   │   │   ├── keystrokes.ts                   # Typing cadence, CPM speed, flight times, backspaces, excessive corrections
│   │   │   ├── visibility.ts                   # Tab focus/blur, document visibility, active dwell time
│   │   │   ├── clipboard.ts                    # Copy & paste interaction tracking
│   │   │   ├── media.ts                        # HTML5 video/audio playback, pause, and progress milestones
│   │   │   └── performance.ts                  # Core Web Vitals (LCP, CLS, FID/INP approximation) & Nav timing
│   │   └── adapters/
│   │       ├── posthog_adapter.ts              # Battle-tested PostHog engine integration
│   │       └── http_adapter.ts                 # Direct HTTP fallback adapter
│   └── dist/
│       ├── growthos.min.js                     # Standalone browser UMD bundle (<script src="...">)
│       ├── index.esm.js                        # ES Module bundle
│       └── index.cjs.js                        # CommonJS bundle
├── backend-bridge/
│   ├── main.py                                 # FastAPI Ingestion & Webhook Bridge
│   ├── schemas.py                              # Pydantic schemas for events & derived signals
│   ├── signal_processor.py                     # Derived behavioral signal reduction (for Module 4)
│   ├── mock_customer_graph.py                  # Graph node & relationship mapper for Customer Intelligence
│   └── test_bridge.py                          # Pytest suite for bridge & signal calculation
├── qa-debugger/
│   ├── manifest.json                           # Chrome Extension Manifest V3 configuration
│   ├── devtools.html                           # DevTools bootstrap
│   └── panel.html / panel.css / panel.js       # Real-time event QA & inspection panel with JSON export
└── tests/
    ├── playwright.config.ts                    # Playwright configuration
    ├── test-harness.html                       # Interactive test harness with SDK loaded
    └── e2e/
        ├── canonical_events.spec.ts            # E-commerce sequence & custom events
        ├── autocapture_and_ux.spec.ts          # Forms, scroll, rage clicks, exit intent
        ├── identity_resolution.spec.ts         # Anonymous to identified user mapping
        ├── keystrokes_and_masking.spec.ts      # Typing dynamics & sensitive input suppression
        ├── nextjs_storefront.spec.ts           # Full Next.js e-commerce storefront flow
        └── privacy_and_consent.spec.ts         # PII masking & opt-out compliance
```

---

## Quick Start & Verification

### 1. Launch Next.js Storefront
```bash
cd research/frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

### 2. Run Playwright E2E Accuracy Tests (11/11 Passed)
```bash
cd research/tests
npx playwright test
```

### 3. Run Backend Bridge Pytest Suite (3/3 Passed)
```bash
cd research/backend-bridge
source .venv/bin/activate
pytest test_bridge.py
```

### 4. Run Backend Bridge Pytest Suite
```bash
cd research/backend-bridge
uv run --with pytest --with fastapi --with uvicorn --with pydantic --with httpx pytest test_bridge.py
```
*Tests verify batch event ingestion, idempotency deduplication, high intent signal calculation, checkout abandonment friction detection, and Customer Graph node linking.*
