# GrowthOS Canonical Event Taxonomy Specification

**Version:** 1.0.0  
**Scope:** GrowthOS Module 2 (Behavior Intelligence SDK) & Module 4 (AI Growth Brain)  
**Location:** `research/docs/event_taxonomy_spec.md`

---

## 1. Universal Envelope Schema

Every event emitted by GrowthOS (whether auto-captured or custom) conforms to the following canonical envelope:

```json
{
  "event_id": "evt_01J7ABCDEFGH1234567890",
  "event_name": "product.viewed",
  "timestamp": "2026-08-24T21:30:00.123Z",
  "workspace_id": "ws_dominos_in",
  "project_id": "proj_growth_01",
  "anonymous_id": "anon_98f12a34-b2c1-4d3e-9012-34567890abcd",
  "customer_id": "cust_48291",
  "session_id": "sess_87a12b-34cd-56ef-78gh",
  "idempotency_key": "idemp_a1b2c3d4e5f6g7h8",
  "page": {
    "url": "https://dominos.co.in/menu/farmhouse-pizza",
    "path": "/menu/farmhouse-pizza",
    "title": "Farmhouse Pizza - Domino's",
    "referrer": "https://www.google.com/search?q=dominos+pizza",
    "search": "?utm_source=meta&utm_medium=cpc&utm_campaign=weekend_pizza"
  },
  "utm": {
    "source": "meta",
    "medium": "cpc",
    "campaign": "weekend_pizza",
    "term": null,
    "content": "creative_a"
  },
  "device": {
    "screen_width": 390,
    "screen_height": 844,
    "viewport_width": 390,
    "viewport_height": 664,
    "pixel_ratio": 3,
    "orientation": "portrait",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)...",
    "browser": "Safari",
    "browser_version": "17.0",
    "os": "iOS",
    "os_version": "17.0",
    "device_type": "mobile",
    "language": "en-IN",
    "timezone": "Asia/Kolkata",
    "timezone_offset": -330
  },
  "network": {
    "effective_type": "4g",
    "downlink": 10.0,
    "rtt": 50,
    "save_data": false
  },
  "properties": {},
  "metadata": {
    "sdk_version": "1.0.0",
    "sdk_name": "growthos-js",
    "source": "client",
    "environment": "production"
  }
}
```

---

## 2. Category 1: Auto-Captured Lifecycle & DOM Events

### 2.1 Navigation & Lifecycle
| Event Name | Trigger Condition | Key Properties |
| :--- | :--- | :--- |
| `page.viewed` | Initial page load or SPA route change (`pushState`, `popstate`, `hashchange`) | `initial_referrer`, `is_spa_transition`, `previous_url`, `page_title` |
| `session.started` | New visitor or return after 30+ min of inactivity | `entry_url`, `entry_referrer`, `utm_*`, `is_returning` |
| `session.ended` | User idle $>30\text{min}$ or page unload after session expiry | `session_duration_seconds`, `page_count`, `event_count`, `exit_url` |
| `tab.visibility_changed` | Document visibility changes (`document.hidden`) | `visibility_state` (`visible` / `hidden`), `dwell_time_seconds` |

### 2.2 DOM & Interaction
| Event Name | Trigger Condition | Key Properties |
| :--- | :--- | :--- |
| `element.clicked` | Click on button, link, or element with `data-growthos-track` | `tag_name`, `element_id`, `class_name`, `text_content`, `href`, `css_path`, `data_attributes` |
| `scroll.milestone` | User reaches 25%, 50%, 75%, 90%, or 100% of document height | `milestone_percentage`, `max_scroll_depth`, `scroll_direction`, `time_to_milestone_ms` |
| `clipboard.copied` | User copies text on the page | `selected_length`, `tag_name`, `is_masked` |
| `clipboard.pasted` | User pastes text into an input | `input_id`, `input_name`, `pasted_length` (PII masked) |

### 2.3 Form Intelligence
| Event Name | Trigger Condition | Key Properties |
| :--- | :--- | :--- |
| `form.started` | First focus or input in any form field | `form_id`, `form_name`, `form_action`, `first_field_name` |
| `form.field_focused` | Focus on input, select, textarea | `form_id`, `field_name`, `field_type`, `field_index` |
| `form.field_blurred` | Blur from form field | `form_id`, `field_name`, `dwell_time_ms`, `has_value` |
| `form.field_changed` | Value change in form field | `form_id`, `field_name`, `field_type`, `value_length` (values masked) |
| `form.submitted` | Form submit event triggered | `form_id`, `form_name`, `time_to_complete_seconds`, `fields_completed_count` |
| `form.abandoned` | Page navigation after form started without submit | `form_id`, `last_focused_field`, `fields_filled_ratio`, `time_spent_seconds` |

### 2.4 Media Interactions
| Event Name | Trigger Condition | Key Properties |
| :--- | :--- | :--- |
| `media.played` | HTML5 `<video>` or `<audio>` starts playing | `media_src`, `media_type`, `current_time`, `duration` |
| `media.paused` | Media paused by user | `media_src`, `current_time`, `duration`, `watch_percentage` |
| `media.milestone` | Media playback crosses 25%, 50%, 75%, 100% | `media_src`, `milestone_percentage`, `duration` |

### 2.5 Web Vitals & Performance
| Event Name | Trigger Condition | Key Properties |
| :--- | :--- | :--- |
| `performance.web_vitals` | Page metrics available via PerformanceObserver | `lcp_ms`, `cls_score`, `inp_ms`, `fcp_ms`, `ttfb_ms`, `dom_complete_ms` |

---

## 3. Category 2: UX Friction & Behavioral Heuristics

| Event Name | Detection Heuristic | Value to AI Growth Brain |
| :--- | :--- | :--- |
| `user.rage_click` | $\ge 3$ clicks within 500ms within a 30px radius on the same element | Identifies broken buttons, unclickable links, or sluggish UI responsiveness. |
| `user.dead_click` | Click on an element that yields no DOM mutation, navigation, or network call within 1000ms | Surfaces missed user affordances (e.g. non-clickable images users expect to open). |
| `user.error_click` | Click followed within 1000ms by an uncaught JS error (`window.onerror`) or failed HTTP request | Pinpoints critical bugs blocking user workflows directly in customer sessions. |
| `user.mouse_thrashing` | Erratic cursor acceleration $>1800\text{px/s}^2$ with high directional variance | Detects user confusion, missing information, or layout visual disorientation. |
| `user.exit_intent` | Mouse trajectory moving rapidly towards top browser viewport ($v_y < -400\text{px/s}$) on desktop | Triggers real-time retention offers or cart abandonment recovery prompts. |
| `user.typing_dynamics` | Keystroke cadence, CPM speed, and inter-key flight time on non-sensitive fields | Analyzes form completion friction, user engagement, and typing speed. |
| `user.excessive_corrections` | User hits Backspace/Delete $\ge 5$ times or $>35\%$ of total keystrokes on a field | Detects field formatting ambiguity (e.g. phone numbers, promo codes, addresses). |
| `user.form_hesitation` | User pauses $>1500\text{ms}$ between keystrokes $\ge 2$ times or spends $>15\text{s}$ on a field | Identifies hesitation, uncertainty, or confusion in conversion funnels. |

---

## 3.1 Strict Privacy & Zero-Leak Sensitive Field Avoidance

1. **Automatic Sensitive Field Detection**:
   - Input types: `type="password"`, `type="hidden"`.
   - Autocomplete: `cc-number`, `cc-csc`, `cc-exp`, `current-password`, `new-password`, `one-time-code`, `transaction-amount`, `bday`.
   - Attribute & Identifier regex: `pass|pwd|secret|token|auth|cvv|cvc|card|ssn|pin|otp|security|account_number|routing|bank|tax|national_id|aadhaar|pan`.
   - Explicit markers: `data-growthos-mask`, `data-private`, `data-mask`, class `.growthos-mask`, `.sensitive`.
2. **Masking Rules**:
   - In form lifecycle events (`form.field_focused`, `form.field_blurred`, `form.field_changed`), field names are masked to `[SENSITIVE_FIELD]`, values are completely omitted, and `value_length` is 0.
   - Keystroke dynamics and timing tracking are **strictly disabled on sensitive fields** to eliminate keylogger or timing attack risks.
   - Plain text property values are filtered via Luhn algorithm for credit card masking (`[CARD_ENDED_XXXX]`) and SSN redaction (`[SSN_REDACTED]`).

---

## 4. Category 3: Custom Business & E-Commerce Events

### 4.1 Product & Catalog
```typescript
GrowthOS.track('product.viewed', {
  product_id: 'PRD-PIZZA-FARMHOUSE',
  sku: 'PIZZA-FARM-REG',
  name: 'Farmhouse Pizza',
  category: 'Veg Pizza',
  subcategory: 'Cheese Burst',
  brand: "Domino's",
  price: 459.00,
  currency: 'INR',
  in_stock: true,
  variant: 'Regular Crust'
});
```

### 4.2 Cart & Basket
```typescript
GrowthOS.track('cart.item_added', {
  cart_id: 'cart_9921',
  product_id: 'PRD-PIZZA-FARMHOUSE',
  name: 'Farmhouse Pizza',
  price: 459.00,
  quantity: 2,
  item_total: 918.00,
  cart_total: 1248.00,
  currency: 'INR'
});
```

### 4.3 Checkout Progression & Abandonment
```typescript
GrowthOS.track('checkout.started', {
  checkout_id: 'chk_10293',
  cart_id: 'cart_9921',
  item_count: 3,
  cart_value: 1248.00,
  currency: 'INR',
  coupon_code: 'WEEKEND50'
});

GrowthOS.track('checkout.step_completed', {
  checkout_id: 'chk_10293',
  step_number: 2,
  step_name: 'delivery_address',
  delivery_fee: 60.00,
  estimated_delivery_minutes: 30
});

GrowthOS.track('checkout.abandoned', {
  checkout_id: 'chk_10293',
  step_abandoned_at: 2,
  step_name: 'delivery_address',
  cart_value: 1248.00,
  last_interaction_element: 'delivery_fee_tooltip',
  time_in_checkout_seconds: 45
});
```

### 4.4 Transactional & Purchases (Client or Server-Side)
```typescript
GrowthOS.track('purchase.completed', {
  order_id: 'ORD-2026-9481',
  checkout_id: 'chk_10293',
  subtotal: 1248.00,
  tax: 62.40,
  shipping: 60.00,
  discount: 100.00,
  total: 1270.40,
  currency: 'INR',
  payment_method: 'UPI',
  items: [
    { product_id: 'PRD-PIZZA-FARMHOUSE', name: 'Farmhouse Pizza', price: 459.00, quantity: 2 },
    { product_id: 'PRD-GARLIC-BREAD', name: 'Garlic Breadsticks', price: 165.00, quantity: 2 }
  ]
});
```

### 4.5 Loyalty & Customer Actions
```typescript
GrowthOS.track('reward.redeemed', {
  reward_id: 'RWD-FREE-GARLIC-BREAD',
  reward_name: 'Free Garlic Breadsticks',
  points_spent: 200,
  remaining_points_balance: 450,
  tier: 'Gold'
});
```

---

## 5. Category 4: Derived Behavioral Signals (Module 4 Consumables)

These signals are generated by the Stream Processor and published to the AI Growth Brain:

| Derived Signal Name | Input Events & Trigger Rule | AI Action Recommendation |
| :--- | :--- | :--- |
| `behavior.high_intent.detected` | $\ge 3$ views of same product across $\ge 2$ sessions within 48h without purchase | Recommends personalized ads or flash discount. |
| `behavior.checkout_friction.detected` | Cluster of rage clicks on payment/delivery step or $>50\%$ drop-off at Step 2 | Recommends UX fix or waiver of delivery fee for high LTV segment. |
| `behavior.churn_risk.detected` | Recency $>35$ days + session duration down $60\%$ + cart abandoned | Recommends loyalty re-engagement bonus points. |
