# GrowthOS Module 2: Behavior Intelligence SDK & E-Commerce Integration
## Comprehensive Technical & Operational Documentation

---

## 1. Executive Summary & Module 2 Vision

**GrowthOS** is an omnichannel growth operating system consisting of 4 core modules:
1. **Module 1: Loyalty & Rewards Platform** (Customer Retention & Gamification)
2. **Module 2: Behavior Intelligence SDK** (High-Frequency Autocapture & Telemetry Engine)
3. **Module 3: Ads Layer Manager** (Acquisition & Multi-Channel Campaigns)
4. **Module 4: AI Growth Brain & Customer Intelligence** (Semantic Reasoning, Prediction, and Policy Orchestration)

**Module 2** serves as the sensory nervous system for GrowthOS. It tracks customer micro-behaviors across web storefronts—spanning page navigation, clicks, keystroke flight times, form hesitations, rage clicks, scroll depth, and e-commerce conversions—and compresses this high-frequency operational firehose into structured behavioral signals for the **Module 4 AI Growth Brain**.

```
┌────────────────────────────────────────────────────────────────────────┐
│               Storefront User Interactions (Browser / Next.js)         │
│  Clicks • Keystroke Cadence • Scroll Milestones • Rage Clicks • Forms  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   GrowthOS Client SDK (@growthos/sdk)                  │
│   • Multi-Module Autocapture       • Zero-Leak PII & Card Masking      │
│   • Keystroke Friction Detection   • Batching Queue & Transport        │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
        (Direct Ingestion)              (Dual-Ingest Telemetry)
                    │                                │
                    ▼                                ▼
       ┌────────────────────────┐      ┌───────────────────────────────┐
       │   PostHog Engine       │      │   GrowthOS Backend Bridge     │
       │   (Raw Autocapture &   │      │   (FastAPI Microservice)      │
       │    Session Replays)    │      └──────────────┬────────────────┘
       └────────────────────────┘                     │
                                                      ▼
                                       ┌───────────────────────────────┐
                                       │   Heuristic Signal Processor  │
                                       │   • high_intent.detected      │
                                       │   • checkout_friction         │
                                       │   • ux_rage_cluster           │
                                       └──────────────┬────────────────┘
                                                      │
                                                      ▼
                                       ┌───────────────────────────────┐
                                       │   Module 4: AI Growth Brain   │
                                       │   (Neo4j Customer Graph &     │
                                       │    Semantic Reasoning Engine) │
                                       └───────────────────────────────┘
```

---

## 2. End-to-End Architectural Components

The system is organized into five tightly integrated sub-projects under [`research/`](file:///home/mihir/Codes/internship/GrowthOS/research):

| Sub-Project | Directory | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **GrowthOS TypeScript SDK** | [`research/sdk/`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk) | Browser SDK capturing autocapture, UX signals, forms, keystrokes, and e-commerce events. | TypeScript, Rollup, PostHog-js |
| **Next.js Storefront** | [`research/frontend/`](file:///home/mihir/Codes/internship/GrowthOS/research/frontend) | Production-ready Domino's Pizza e-commerce experience instrumented with GrowthOS. | Next.js 16 (App Router), React 19, TailwindCSS |
| **Backend Bridge & Signal Processor** | [`research/backend-bridge/`](file:///home/mihir/Codes/internship/GrowthOS/research/backend-bridge) | Ingests event batches, reduces raw telemetry to high-level signals, maps to Customer Graph. | Python 3.14, FastAPI, Pydantic, Pytest |
| **QA DevTools Extension** | [`research/qa-debugger/`](file:///home/mihir/Codes/internship/GrowthOS/research/qa-debugger) | Chrome Manifest V3 extension for inspecting SDK event payloads in browser DevTools. | Chrome Extension MV3, Vanilla JS/CSS |
| **Automated Test Suite** | [`research/tests/`](file:///home/mihir/Codes/internship/GrowthOS/research/tests) | Playwright E2E and unit test suite validating 100% of event schemas, masking, and UX signals. | Playwright, Chromium, TypeScript |

---

## 3. GrowthOS SDK Deep-Dive (`research/sdk/`)

### 3.1 SDK Core Pipeline & Class Structure

The SDK is structured around a centralized facade (`GrowthOSClient`) managing specialized sub-modules:

```
GrowthOSClient
 ├── ConfigManager (Options, endpoint URLs, consent state)
 ├── StorageManager (Local/SessionStorage, in-memory fallbacks)
 ├── SessionManager (30-min inactivity timeout, persistent anonymous_id)
 ├── Validator (Luhn card masking, PII regex, sensitive field avoidance)
 ├── TransportQueue (FIFO queue, batching, exponential retry, sendBeacon)
 └── Capture Modules:
      ├── PageviewCapture (SPA history & document title)
      ├── AutocaptureModule (DOM click hierarchy)
      ├── FormCaptureModule (Field focus, blur dwell time, submit, abandon)
      ├── ScrollCaptureModule (25%, 50%, 75%, 90%, 100% milestones)
      ├── UxSignalsModule (Rage click, dead click, error click, exit intent)
      ├── KeystrokeCaptureModule (CPM speed, flight times, backspaces, hesitation)
      ├── VisibilityCaptureModule (Active dwell time calculation)
      ├── ClipboardCaptureModule (Copy/Paste text events)
      ├── MediaCaptureModule (HTML5 video/audio playback milestones)
      └── PerformanceCaptureModule (Core Web Vitals LCP/CLS/FID)
```

---

### 3.2 Canonical Universal Event Envelope

Every event captured or tracked by GrowthOS is normalized into a strict, unified envelope:

```typescript
export interface EventEnvelope<T = Record<string, any>> {
  event_id: string;              // UUID v4
  event_name: string;            // e.g. "product.viewed", "user.rage_click"
  timestamp: string;             // ISO-8601 UTC string (e.g. "2026-08-25T04:22:00.000Z")
  workspace_id?: string;         // GrowthOS Tenant ID
  project_id: string;            // Project Identifier
  session_id: string;            // UUID v4, rotates after 30 min of inactivity
  anonymous_id: string;          // Persistent device identifier stored in cookie/localStorage
  customer_id?: string | null;   // Known customer identifier linked via identify()
  page: PageMetadata;            // URL, path, referrer, title, search params
  utm: UTMMetadata;              // source, medium, campaign, term, content
  device: DeviceMetadata;        // screen resolution, viewport, OS, browser, device_type
  network: NetworkMetadata;      // effective_type, downlink, rtt
  properties: T;                 // Custom event properties
}
```

---

### 3.3 Capture Modules Breakdown

#### 1. Pageview & SPA Transitions ([`capture/pageview.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/pageview.ts))
- Automatically monkey-patches `window.history.pushState` and `window.history.replaceState`, and listens to `popstate` events.
- Fires `page.viewed` with URL, title, document referrer, and active campaign UTM tags.

#### 2. DOM Autocapture ([`capture/autocapture.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/autocapture.ts))
- Listens to global click events on the window capture phase.
- Recursively constructs an element selector hierarchy (e.g. `button#btnAddToCart.bg-emerald-600 > span`).
- Extracts inner text (truncated to 100 characters), element bounding client rect, href, and data attributes.

#### 3. Form Intelligence ([`capture/forms.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/forms.ts))
- `form.started`: Fired when the user focuses on the first field of a form.
- `form.field_focused` & `form.field_blurred`: Records field dwell time (milliseconds spent on the field) and whether the field was filled.
- `form.field_changed`: Tracks input changes. For sensitive inputs, field name is masked to `[SENSITIVE_FIELD]` and `value_length` is forced to `0`.
- `form.submitted` & `form.abandoned`: Tracks form completion or abandonment before submit.

#### 4. Scroll Depth Tracking ([`capture/scroll.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/scroll.ts))
- Calculates percentage scroll depth (`scrollY / (scrollHeight - clientHeight)`).
- Emits `scroll.milestone` at **25%, 50%, 75%, 90%, and 100%** thresholds. Each milestone is deduplicated per page view.

#### 5. UX Friction Signals ([`capture/ux_signals.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/ux_signals.ts))
- `user.rage_click`: Emitted when $\ge 3$ clicks occur on the same element within $500\text{ms}$ in a 30px radius.
- `user.dead_click`: Emitted when an element is clicked but produces no DOM mutation, navigation, or network call within $1000\text{ms}$.
- `user.error_click`: Emitted when a click is followed within $1000\text{ms}$ by an uncaught JavaScript error (`window.onerror`).
- `user.mouse_thrashing`: Emitted when erratic mouse acceleration exceeds $1800\text{px/s}^2$ with high directional variance.
- `user.exit_intent`: Emitted on desktop when the cursor moves rapidly towards the top viewport boundary ($v_y < -400\text{px/s}$).

#### 6. Privacy-Safe Keystroke Dynamics ([`capture/keystrokes.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/capture/keystrokes.ts))
- Monitors typing dynamics on non-sensitive input fields without keylogging raw characters:
  - `user.typing_dynamics`: Captures `keystroke_count`, `backspace_count`, `avg_flight_time_ms`, `typing_speed_cpm` (characters per minute), and `hesitation_pauses_count` ($>1500\text{ms}$ delay between keystrokes).
  - `user.excessive_corrections`: Emitted when a user hits Backspace/Delete $\ge 5$ times or $>35\%$ of total keystrokes on a field (indicates formatting confusion such as phone numbers, promo codes, or addresses).
  - `user.form_hesitation`: Emitted when hesitation pauses $\ge 2$ or field time $>15\text{s}$.
- **Zero-Keylogging Guarantee on Sensitive Fields**: On any field detected as sensitive (passwords, cards, PINs, or `data-growthos-mask`), keystroke dynamics are **completely suppressed**.

---

## 4. Privacy, Compliance & Zero-Leak Masking Engine

GrowthOS enforces strict privacy safeguards inside [`research/sdk/src/validator.ts`](file:///home/mihir/Codes/internship/GrowthOS/research/sdk/src/validator.ts):

### 4.1 Automatic Sensitive Field Detection
An element is classified as sensitive if any of the following match:
1. **Input Types**: `type="password"`, `type="hidden"`.
2. **Autocomplete Attributes**: Matching `/cc-|current-password|new-password|one-time-code|transaction-amount|bday/i`.
3. **Identifier Patterns**: Element `name`, `id`, `placeholder`, `aria-label`, or `data-testid` matching:
   ```regex
   /(?:^|[_\W])(pass|passwd|password|pwd|secret|token|auth|cvv|cvc|card|ssn|pin|otp|security|account_number|routing|bank|tax|national_id|aadhaar|pan)(?:[_\W]|$)/i
   ```
4. **Explicit Privacy Attributes**: Elements or ancestors with `data-growthos-mask`, `data-private`, `data-mask`, class `.growthos-mask`, or `.sensitive`.

### 4.2 Luhn Algorithm Credit Card Masking
All payload string properties are recursively evaluated. Any 13–19 digit string matching Luhn credit card checksums is masked as `[CARD_ENDED_XXXX]`. Social Security Numbers are redacted as `[SSN_REDACTED]`.

### 4.3 Consent Compliance & Opt-Out
If consent is toggled off (`sdk.optOut()` or `consent.analytics === false`), the SDK immediately flushes any existing queue and suppresses all subsequent telemetry collection.

---

## 5. Backend Bridge & Derived Signal Processor (`research/backend-bridge/`)

Located in [`research/backend-bridge/`](file:///home/mihir/Codes/internship/GrowthOS/research/backend-bridge), this FastAPI microservice bridges raw telemetry into **Module 4 (AI Growth Brain)**.

### 5.1 Endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v1/events/batch` | Ingests batch of `EventEnvelope` objects, performs deduplication and routing. |
| `GET` | `/api/v1/behavior/signals` | Returns high-level derived signals generated by the heuristic engine. |
| `GET` | `/api/v1/customer-graph/{customer_id}` | Returns graph representation (`Customer` $\leftrightarrow$ `Session` $\leftrightarrow$ `Product` $\leftrightarrow$ `Signal`). |
| `GET` | `/api/v1/health` | Service health status and ingestion counters. |

### 5.2 Heuristic Signal Reduction (`signal_processor.py`)

Raw event streams are reduced into semantic intelligence signals:

1. **`behavior.high_intent.detected`**:
   - *Condition*: User views $\ge 3$ products in a session, spends $>45\text{s}$ active dwell time, and scrolls $>75\%$.
   - *Module 4 Action*: Triggers personalized promotional banner or fast-checkout push notification.
2. **`behavior.checkout_friction.detected`**:
   - *Condition*: User adds items to cart, reaches Step 2 of checkout, hesitates on the ₹60 delivery fee, and abandons checkout.
   - *Module 4 Action*: Recommends automatic loyalty point delivery-fee waiver to recover conversion.
3. **`behavior.ux_rage_cluster.detected`**:
   - *Condition*: Multiple rage click events occur on the same component (e.g. `#btnStartCheckout`).
   - *Module 4 Action*: Flags technical UI bug to engineering team.

---

## 6. Next.js E-Commerce Storefront (`research/frontend/`)

Located in [`research/frontend/`](file:///home/mihir/Codes/internship/GrowthOS/research/frontend), this application is a realistic, production-styled Domino's Pizza web store.

### 6.1 Storefront Architecture

```
research/frontend/src/
├── app/
│   ├── layout.tsx                # Root layout with GrowthOSProvider, CartProvider, Navbar, QAOverlay
│   ├── page.tsx                  # Home menu with promo hero, category filter, pizza cards grid
│   ├── checkout/page.tsx         # 3-step checkout funnel (Address -> Delivery Slot -> Payment)
│   ├── order/[id]/page.tsx       # Live baking & delivery tracker + Loyalty points credit
│   └── globals.css               # TailwindCSS theme, dark mode, custom scrollbars
├── components/
│   ├── Navbar.tsx                # Brand header with location, Gold member badge, live cart count
│   ├── HeroBanner.tsx            # Promotional carousel with UTM attribution & promo codes
│   ├── CategoryFilter.tsx        # Veg, Non-Veg, Cheese Volcano, Sides, Desserts, Beverages tabs
│   ├── PizzaCard.tsx             # Product card with size selector, crust dropdown, quick add
│   ├── PizzaCustomizerModal.tsx  # Pizza customizer (crust, size, extra cheese, toppings)
│   ├── CartDrawer.tsx            # Slide-over cart with coupon validator (DOMINOS50, WEEKEND20)
│   └── QAOverlay.tsx             # Floating real-time GrowthOS event telemetry inspector
├── context/
│   ├── CartContext.tsx           # Cart state, item math, coupons, loyalty points calculation
│   └── GrowthOSProvider.tsx      # SDK initialization, identify(), route transition observer
├── data/
│   └── dominos_menu.ts           # Authentic Domino's India menu items, prices & crust options
├── lib/
│   └── growthos.ts               # Client SDK singleton instance helper
└── types/
    └── store.ts                  # TypeScript interfaces for Menu, Cart, Crusts, Orders
```

### 6.2 E-Commerce Behavioral Events

The frontend triggers standard e-commerce events across user journeys:

```typescript
// 1. Product Viewed
getGrowthOS().track('product.viewed', { product_id, name, category, base_price, is_veg });

// 2. Product Customized
getGrowthOS().track('product.customized', { product_id, name, size, crust, extra_cheese, toppings });

// 3. Cart Item Added / Removed
getGrowthOS().track('cart.item_added', { product_id, name, size, crust, unit_price, quantity, cart_total });
getGrowthOS().track('cart.item_removed', { product_id, name, quantity, cart_total });

// 4. Coupon Applied
getGrowthOS().track('cart.coupon_applied', { coupon_code, discount_type, discount_value, cart_subtotal });

// 5. Checkout Funnel Progress & Abandonment
getGrowthOS().track('checkout.started', { cart_total, item_count, items });
getGrowthOS().track('checkout.step_completed', { step_number: 1, step_name: 'delivery_address' });
getGrowthOS().track('checkout.step_completed', { step_number: 2, step_name: 'delivery_charges_and_slot' });
getGrowthOS().track('checkout.abandoned', { abandoned_step: 2, reason: 'delivery_charge_hesitation' });

// 6. Purchase Completed
getGrowthOS().track('purchase.completed', { order_id, subtotal, discount, delivery_fee, tax, total_amount, payment_method });
```

---

## 7. Verification & Automated Test Coverage

The system contains automated tests across Playwright E2E and Backend Bridge Pytest.

### 7.1 Playwright E2E Test Suite (11/11 Passed)
Run via `npx playwright test` in [`research/tests/`](file:///home/mihir/Codes/internship/GrowthOS/research/tests):

1. **`canonical_events.spec.ts`**: Verifies full e-commerce event sequence (`product.viewed` $\rightarrow$ `cart.item_added` $\rightarrow$ `checkout.started` $\rightarrow$ `checkout.step_completed` $\rightarrow$ `purchase.completed`).
2. **`autocapture_and_ux.spec.ts`**: Verifies DOM autocapture, rapid rage click detection ($\ge 3$ clicks in 500ms), and scroll milestone thresholds (25%, 50%, 75%, 90%, 100%).
3. **`identity_resolution.spec.ts`**: Verifies persistent `anonymous_id` preservation across sessions and clean linking of `customer_id` upon `identify()`.
4. **`keystrokes_and_masking.spec.ts`**: Verifies typing dynamics tracking on standard inputs, excessive corrections friction when hitting Backspace $\ge 5$ times, and strict suppression of keystroke dynamics on sensitive fields.
5. **`nextjs_storefront.spec.ts`**: Tests the entire Next.js web application—visiting the store, searching items, opening the customizer, applying coupons (`DOMINOS50`), 3-step checkout, and live order tracking.
6. **`privacy_and_consent.spec.ts`**: Verifies Luhn algorithm credit card masking, password redaction, and instant tracking cessation upon user consent opt-out.

### 7.2 Backend Bridge Pytest Suite (3/3 Passed)
Run via `pytest` in [`research/backend-bridge/`](file:///home/mihir/Codes/internship/GrowthOS/research/backend-bridge):

1. **`test_health_endpoint`**: Verifies service health check and telemetry counter.
2. **`test_event_batch_ingestion_and_idempotency`**: Tests batch envelope validation and duplicate event deduplication.
3. **`test_high_intent_and_checkout_abandonment_signals`**: Validates heuristic signal reduction (`high_intent`, `checkout_friction`) and Customer Graph relationship node construction.

---

## 8. How to Run and Develop

### 1. Start the Next.js Storefront
```bash
cd research/frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 2. Start the Backend Bridge
```bash
cd research/backend-bridge
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### 3. Rebuild the SDK Bundle
```bash
cd research/sdk
npm run build
```

### 4. Run All Playwright Automated Tests
```bash
cd research/tests
npx playwright test
```
