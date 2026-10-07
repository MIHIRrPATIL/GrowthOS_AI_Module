# GrowthOS Module 4: Grounded Metrics Engine Specification

## 1. Executive Summary & Mathematical Grounding Mandate

The **Metrics Engine** is Component 1 of the GrowthOS AI Growth Brain (Module 4). It is the deterministic foundation upon which all downstream automated analysis, anomaly digests, graph inferences, and merchant action plans rely.

### The Zero-Hallucination Invariant
Large Language Models (LLMs) are probabilistic token generators; they cannot be trusted to perform arithmetic, sample size evaluations, or period-over-period percentage comparisons. Prompting an LLM to calculate or estimate a metric inevitably introduces hallucinations, floating-point drift, and non-reproducible outputs.

The GrowthOS Metrics Engine enforces strict architectural separation:
1. **100% Deterministic Code Execution**: All conversion rates, step drop-offs, abandonments, and ratios are calculated via pure deterministic Python functions executed directly over immutable event storage.
2. **Explicit Sample Sizes**: Every calculated metric strictly outputs its underlying `numerator`, `denominator`, and `sample_size`. A percentage is never emitted in isolation.
3. **Dual-Window Significance Gating (`min_sample_met`)**: Metrics enforce minimum-sample threshold rules across both current and prior windows. Low-sample movements (e.g. 60% to 50% at n=20) are treated as noise.
4. **Reproducible Time Watermarks (`as_of`)**: Event queries filter on both `occurred_at` (window boundaries) and `received_at <= as_of` (data watermark). Late-arriving events never retroactively alter historical results.
5. **Entity-Aware Funnel Evaluation**: Fast storefront funnels evaluate by `session`, while slow multi-day conversion funnels (SaaS trials, credit applications, travel bookings) evaluate by `customer` or `application` with fixed cohort windows (`cohort_window_days`).
6. **Session Maturity Guard**: Uncompleted sessions active within `maturity_window_minutes` before the window end are excluded from abandonment denominators, preventing active shoppers from falsely counting as drop-offs.
7. **Set-Difference Ratio Safety**: Ratios are derived via set difference rather than count subtraction, strictly enforcing mathematical bounds: `0 <= numerator <= denominator`.
8. **Nullable Undefined Values**: A zero denominator returns `value = None` and `status = "zero_denominator"`, never misleading dashboards or downstream LLMs with `0.0`.
9. **Event Taxonomy Mapping Layer**: Vertical templates maintain an explicit alias mapping layer (`event_mapping`) that normalizes vendor and SDK event names into canonical names before calculation.
10. **Immutable Query Evidence Trails (`evidence_ref`)**: Rather than a fragile event ID range that late events would invalidate, `evidence_ref` stores the exact deterministic query specification: `query:tenant=...:metric=...:window=...:as_of=...:ver=...:filters=...`.

---

## 2. System Architecture & Hexagonal Placement

The Metrics Engine adheres to Hexagonal Architecture (Ports and Adapters), operating purely against the [`EventStoragePort`](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/ports/storage.py) abstraction with injected clocks and dimension allowlisting.

```
+---------------------------------------------------------------------------------------+
|                                    Inbound Triggers                                   |
|       (Digest Engine / Merchant NL Query / Periodic Cron / Benchmark Evaluator)       |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                      MetricsEngine                                    |
|  - Validates tenant_id & vertical_template_id (fail-loud, no defaults)                 |
|  - Loads MetricDefinition from VerticalTemplate Registry                              |
|  - Resolves vendor event aliases via template.resolve_event_name                      |
|  - Enforces dimension allowlist per tenant (ALLOWED_DIMENSIONS)                       |
|  - Injects pure clock (datetime) without calling datetime.now()                       |
|  - Queries storage: occurred_at in [start, end) AND received_at <= as_of              |
|  - Filters out test, bot, and QA traffic (exclude_test_traffic=True)                  |
|  - Entity Dispatch:                                                                   |
|      * session: Attributes by session start time; applies maturity_window_minutes     |
|      * customer / application: Evaluates cohort_window_days from start event           |
|  - Computes exact numerator and denominator via set differences (0 <= num <= denom)  |
|  - Sets value = num / denom (unrounded float) or None if denom == 0                   |
|  - Evaluates min_sample_met = (denominator >= min_sample_threshold)                   |
|  - Generates immutable query spec evidence_ref                                        |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                             EventStoragePort (Outbound)                               |
|                  (SqlEventStorageAdapter: PostgreSQL / SQLite)                        |
|                                                                                       |
|  - Strict tenant scoping:   WHERE tenant_id = :tenant_id                              |
|  - UTC window filter:       AND occurred_at >= :start AND occurred_at < :end          |
|  - Watermark filter:        AND received_at <= :as_of                                 |
|  - Bot & Test exclusion:    AND device_type != 'bot' AND is_test != true              |
|  - Allowlisted dimensions:  device_type, browser, os, channel, campaign, properties   |
+---------------------------------------------------------------------------------------+
```

---

## 3. Data Contracts and Schema Definitions

The Metrics Engine outputs instances of `MetricResult` defined in [`domain/metrics.py`](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/domain/metrics.py).

### Schema Contract
```python
class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimeWindow(_Strict):
    start: datetime  # inclusive, UTC
    end: datetime    # exclusive, UTC


class MetricResult(_Strict):
    tenant_id: str                        # Mandatory tenant isolation key
    vertical_template_id: str             # e.g., 'ecommerce', 'qsr_delivery', 'saas_subscription'
    metric_name: str                      # Must exist in the vertical template catalog
    definition_version: str               # Semantic version of the formula (e.g., 'v1.1.0')
    window: TimeWindow                    # Explicit start and end in UTC
    as_of: datetime                       # Data watermark used for this run
    calculated_at: datetime               # Exact timestamp of computation
    dimensions: dict[str, str]            # Slicing dimensions (e.g. {'device_type': 'mobile'})
    numerator: Optional[int]              # Exact count of qualifying positive cases (None if denom == 0)
    denominator: Optional[int]            # Exact count of base population (None if denom == 0)
    value: Optional[float]                # Ratio between 0.0 and 1.0 (None when undefined)
    status: MetricStatus                  # 'valid' or 'zero_denominator'
    unit: Unit                            # 'ratio', 'count', 'currency_inr', 'ms'
    sample_size: int                      # Denominator underlying count (0 if denom is None)
    min_sample_threshold: int             # Threshold required for statistical significance
    min_sample_met: bool                  # True if denominator >= min_sample_threshold
    evidence_ref: str                     # Immutable stored query specification
```

### Mathematical Consistency Validator
`MetricResult` includes an automated Pydantic model validator that rejects mathematical inconsistencies:
```python
@model_validator(mode="after")
def _validate_mathematical_consistency(self) -> "MetricResult":
    if self.status == "zero_denominator":
        if self.denominator is not None and self.denominator != 0:
            raise ValueError("status 'zero_denominator' requires denominator to be None or 0")
        if self.value is not None:
            raise ValueError("value must be None when denominator is zero")
        if self.sample_size != 0:
            raise ValueError("sample_size must be 0 when denominator is zero")
        if self.min_sample_met is not False:
            raise ValueError("min_sample_met must be False when denominator is zero")
    elif self.status == "valid":
        if self.denominator is None or self.denominator <= 0:
            raise ValueError("Valid MetricResult requires positive integer denominator")
        if self.numerator is None or self.numerator < 0:
            raise ValueError("Valid MetricResult requires non-negative integer numerator")
        if self.numerator > self.denominator:
            raise ValueError("Numerator cannot exceed denominator in ratio metrics")
        if self.value is None:
            raise ValueError("Valid MetricResult requires a non-null float value")
        expected_ratio = self.numerator / self.denominator
        if abs(self.value - expected_ratio) > 1e-4:
            raise ValueError(f"Value {self.value} does not equal numerator/denominator ({expected_ratio})")
        if self.sample_size != self.denominator:
            raise ValueError("sample_size must equal denominator")
        expected_min_met = self.denominator >= self.min_sample_threshold
        if self.min_sample_met != expected_min_met:
            raise ValueError(f"min_sample_met ({self.min_sample_met}) contradicts sample size")
    return self
```

---

## 4. Vertical Template Catalog

Different business verticals exhibit distinct behavioral funnels. The engine uses declarative vertical templates configured in [`engines/vertical_templates.py`](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/engines/vertical_templates.py).

### Template Summary Matrix

| Template ID | Name | Target Business Model | Primary Entity | Default Min Sample | Canonical Funnel Steps |
|---|---|---|---|---|---|
| `ecommerce` | E-Commerce & D2C Storefront | Retail, Fashion, Electronics | `session` | 30 | browse -> cart_add -> checkout_start -> step_1_address -> step_2_charges -> purchase_complete |
| `qsr_delivery` | Quick Service Restaurant | Pizza Delivery, Cloud Kitchens | `session` | 25 | menu_view -> product_customize -> cart_add -> checkout_start -> delivery_charges -> purchase_complete |
| `saas_subscription` | B2B & PLG SaaS | Software Subscriptions, Cloud Tools | `customer` | 20 | landing_visit -> signup_start -> signup_complete -> workspace_created -> onboarding_complete -> trial_started -> paid_subscribed |
| `travel_hospitality` | Travel & Hotel Bookings | Flights, Hotels, Vacation Rentals | `session` / `customer` | 25 | search_performed -> listing_viewed -> dates_selected -> guest_details_entered -> payment_initiated -> booking_confirmed |
| `fintech_lending` | Fintech & Digital Credit | Personal Loans, Credit Cards, BNPL | `application` | 20 | offer_view -> application_start -> kyc_submitted -> bank_linked -> agreement_signed -> loan_disbursed |
| `subscription_box` | D2C Subscription Boxes | Recurring Auto-Ship, Memberships | `customer` | 25 | box_browse -> plan_selected -> customization_done -> checkout_start -> subscription_activated -> cycle_renewed |

---

## 5. Comprehensive Metric Formulas & Behavioral Definitions

Every metric is defined by strict set logic over canonical event telemetry.

### 5.1 E-Commerce & D2C Storefront (`ecommerce`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample | Formula |
|---|---|---|---|---|---|---|---|
| `cart_abandonment_rate` | `session` | 30m maturity | Cart sessions without purchase | Mature sessions with `cart.item_added` | `lower_is_better` | 20 | `mature_carts \ purchases` |
| `checkout_drop_off_rate` | `session` | 30m maturity | Checkout sessions without purchase | Mature sessions with `checkout.started` | `lower_is_better` | 15 | `mature_checkouts \ purchases` |
| `checkout_step_1_drop_off_rate` | `session` | Immediate | Checkout starts without Step 1 | Sessions with `checkout.started` | `lower_is_better` | 10 | `checkouts \ step_1_completions` |
| `checkout_step_2_drop_off_rate` | `session` | Immediate | Step 1 completions without Step 2 | Sessions completing Step 1 (address) | `lower_is_better` | 10 | `step_1_completions \ step_2_completions` |
| `overall_conversion_rate` | `session` | Immediate | Sessions with `purchase.completed` | Visiting sessions (`page.viewed`) | `higher_is_better` | 30 | `purchases / visits` |
| `add_to_cart_rate` | `session` | Immediate | Sessions with `cart.item_added` | Sessions with `product.viewed` | `higher_is_better` | 30 | `cart_adds / product_views` |
| `cart_to_checkout_rate` | `session` | Immediate | Sessions with `checkout.started` | Sessions with `cart.item_added` | `higher_is_better` | 20 | `checkouts / cart_adds` |
| `rage_click_session_rate` | `session` | Immediate | Sessions with `user.rage_click` | Total active sessions | `lower_is_better` | 25 | `rage_sessions / total_sessions` |
| `exit_intent_rate` | `session` | Immediate | Sessions with `user.exit_intent` | Total active sessions | `lower_is_better` | 20 | `exit_sessions / total_sessions` |

### 5.2 QSR & Food Delivery (`qsr_delivery`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample | Special Notes |
|---|---|---|---|---|---|---|---|
| `customization_drop_off_rate` | `session` | Immediate | Product customizers without cart add | Sessions with `product.customized` | `lower_is_better` | 15 | Identifies topping / crust surcharge barriers |
| `checkout_step_2_drop_off_rate` | `session` | Immediate | Step 1 address completions failing at Step 2 charges | Sessions completing Step 1 | `lower_is_better` | 10 | Captures delivery surcharge friction |
| `checkout_drop_off_rate` | `session` | 30m maturity | Food checkout sessions without order | Mature sessions with `checkout.started` | `lower_is_better` | 15 | Overall checkout funnel abandonment |
| `cart_to_checkout_rate` | `session` | Immediate | Sessions reaching checkout | Sessions with `cart.item_added` | `higher_is_better` | 20 | Measures cart review friction |
| `cart_abandonment_rate` | `session` | 20m maturity | Food cart sessions without order | Mature sessions with `cart.item_added` | `lower_is_better` | 20 | Fast QSR delivery recovery window |
| `add_to_cart_rate` | `session` | Immediate | Sessions with `cart.item_added` | Sessions with `product.viewed` | `higher_is_better` | 25 | Menu item interest to cart conversion |
| `overall_conversion_rate` | `session` | Immediate | Sessions with `purchase.completed` | Total menu browsing sessions | `higher_is_better` | 25 | End-to-end storefront conversion |
| `rage_click_session_rate` | `session` | Immediate | Sessions with `ui.rage_clicked` | Total active sessions | `lower_is_better` | 20 | Identifies UI / payment gateway unresponsive friction |
| `exit_intent_rate` | `session` | Immediate | Sessions with `user.exit_intent` | Total active sessions | `lower_is_better` | 20 | Desktop cursor viewport departures |

### 5.3 B2B SaaS & Product-Led Growth (`saas_subscription`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample | Special Notes |
|---|---|---|---|---|---|---|---|
| `signup_completion_rate` | `session` | Immediate | Sessions with `user.signed_up` | Sessions with `user.signup_started` | `higher_is_better` | 15 | Form completion efficiency |
| `onboarding_drop_off_rate` | `customer` | 7-day cohort | Workspaces failing `onboarding.completed` | Workspaces created in window | `lower_is_better` | 10 | Setup activation drop-off |
| `trial_to_paid_conversion_rate` | `customer` | 14-day cohort | Trials converted to `subscription.activated` within 14 days | Customers starting trial in window | `higher_is_better` | 10 | Cross-session slow funnel cohort |
| `visitor_to_signup_rate` | `session` | Immediate | Sessions with `user.signed_up` | Visiting sessions (`page.viewed`) | `higher_is_better` | 30 | Landing page conversion |

### 5.4 Travel, Flights & Hospitality Bookings (`travel_hospitality`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample |
|---|---|---|---|---|---|---|---|
| `search_to_detail_rate` | `session` | Immediate | Sessions with `listing.viewed` | Sessions with `search.performed` | `higher_is_better` | 25 |
| `booking_drop_off_rate` | `session` | 45m maturity | Sessions with `dates.selected` without booking | Mature sessions with `dates.selected` | `lower_is_better` | 15 |
| `payment_failure_rate` | `session` | Immediate | Sessions with `payment.failed` | Sessions with `payment.initiated` | `lower_is_better` | 10 |
| `overall_booking_conversion_rate` | `session` | Immediate | Sessions with `booking.confirmed` | Total search sessions | `higher_is_better` | 30 |

### 5.5 Fintech, Credit & Digital Lending (`fintech_lending`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample |
|---|---|---|---|---|---|---|---|
| `application_completion_rate` | `application` | 7-day cohort | Applications reaching `agreement.signed` | Applications started in window | `higher_is_better` | 15 |
| `kyc_drop_off_rate` | `application` | 3-day cohort | Applications started failing `kyc.submitted` | Applications started in window | `lower_is_better` | 10 |
| `bank_linking_drop_off_rate` | `application` | 3-day cohort | KYC completed failing `bank.account_linked` | KYC completed in window | `lower_is_better` | 10 |
| `disbursement_conversion_rate` | `application` | 14-day cohort | Applications reaching `loan.disbursed` | Applications started in window | `higher_is_better` | 15 |

### 5.6 D2C Subscription Boxes & Memberships (`subscription_box`)

| Metric Name | Entity | Maturity / Cohort | Numerator Definition | Denominator Definition | Polarity | Min Sample |
|---|---|---|---|---|---|---|---|
| `plan_selection_rate` | `session` | Immediate | Sessions with `plan.selected` | Total browsing sessions | `higher_is_better` | 20 |
| `checkout_drop_off_rate` | `session` | 30m maturity | Checkout started without subscription | Mature checkouts started | `lower_is_better` | 15 |
| `subscription_conversion_rate` | `session` | Immediate | Sessions with `subscription.activated` | Total browsing sessions | `higher_is_better` | 25 |
| `cart_abandonment_rate` | `session` | 30m maturity | Configured boxes without checkout completion | Mature configured box sessions | `lower_is_better` | 20 |
| `renewal_success_rate` | `customer` | 30-day cohort | Subscriptions with `cycle.renewed` | Active subscriptions due for renewal | `higher_is_better` | 20 |

---

## 6. Statistical Rules & Architectural Invariants

### 6.1 Dual-Window Statistical Significance
A move from 60% to 50% at n=20 is within sampling noise. The engine combines three rigorous protections:
1. **Dual-Window `min_sample_met`**: Both the current window AND the prior window must satisfy `sample_size >= min_sample_threshold`. If either fails, the shift is demoted to `low` severity to suppress noise.
2. **Two-Proportion Z-Test**: Computes the pooled standard error $SE = \sqrt{\hat{p}(1-\hat{p})(1/n_1 + 1/n_2)}$ and $z = |p_1 - p_2| / SE$. Flags require $z \ge 1.96$ ($p < 0.05$) to be declared statistically significant (`is_statistically_significant = True`).
3. **Percentage-Point Tracking (`delta_pp`)**: Digest flags report both relative change (`delta_pct`) and absolute percentage-point change (`delta_pp`). A shift from 2.0% to 2.2% (+10% relative, +0.2pp) is prevented from creating false high-severity panics.

### 6.2 Zero-Denominator Safety
When an evaluation window contains zero base events:
- `numerator = None`
- `denominator = None`
- `value = None`
- `status = "zero_denominator"`
- `sample_size = 0`
- `min_sample_met = False`
Execution completes gracefully without raising `ZeroDivisionError` and without emitting misleading `0.0` values.

### 6.3 Dimensional Slicing & Injection Protection
To prevent unindexed full-table scans and query injection, dimensions are checked against an allowlist:
```python
ALLOWED_DIMENSIONS = {"device_type", "browser", "os", "channel", "campaign"}
```
Unknown or un-allowlisted dimensions raise `ValueError` fail-loud errors.

### 6.4 Traffic Hygiene: Test, QA, and Bot Filtering
By default, `exclude_test_traffic=True` automatically excludes:
- Automated web crawlers: `device_type = 'bot'`
- QA and automated test sessions: `is_test = true` or `environment = 'test'`
- Internal employees: `traffic_type = 'internal'`

---

## 7. Verification & Benchmark Ground Truth

All calculations are tested against hand-calculated ground-truth populations in [`tests/test_metrics_engine.py`](file:///home/mihir/Codes/internship/GrowthOS/research/ai-module/tests/test_metrics_engine.py).

### Controlled Test Population (50 Sessions)
- 50 Total Visiting Sessions (`page.viewed`)
- 40 Product Views (`product.viewed`, sessions 0-39)
- 20 Cart Additions (`cart.item_added`, sessions 0-19)
- 10 Checkout Starts (`checkout.started`, sessions 0-9)
- 8 Step 1 Address Completions (sessions 0-7, sessions 8-9 drop off)
- 4 Step 2 Delivery Charges Completions (sessions 0-3, sessions 4-7 drop off)
- 4 Purchases Completed (sessions 0-3)
- 5 Rage Click Sessions (sessions 45-49)

### Hand-Calculated Verification Results
```
[Cart Abandonment Rate]
  Formula:        (20 mature carts \ 4 purchases) / 20 carts
  Calculation:    16 / 20 = 0.800000 (80.0%)
  min_sample_met: True (20 >= 20 threshold)
  Test Status:    PASSED

[Checkout Drop-Off Rate]
  Formula:        (10 mature checkouts \ 4 purchases) / 10 checkouts
  Calculation:    6 / 10 = 0.600000 (60.0%)
  min_sample_met: False (10 < 15 threshold)
  Test Status:    PASSED

[Checkout Step 1 Drop-Off Rate]
  Formula:        (10 checkouts \ 8 step 1 completions) / 10 checkouts
  Calculation:    2 / 10 = 0.200000 (20.0%)
  min_sample_met: True (10 >= 10 threshold)
  Test Status:    PASSED (Non-zero ground truth verified)

[Checkout Step 2 Drop-Off Rate]
  Formula:        (8 step 1 completions \ 4 step 2 completions) / 8 step 1 completions
  Calculation:    4 / 8 = 0.500000 (50.0%)
  min_sample_met: False (8 < 10 threshold)
  Test Status:    PASSED

[Add to Cart Rate]
  Formula:        20 cart additions / 40 product views
  Calculation:    20 / 40 = 0.500000 (50.0%)
  min_sample_met: True (40 >= 30 threshold)
  Test Status:    PASSED

[Cart to Checkout Rate]
  Formula:        10 checkout starts / 20 cart additions
  Calculation:    10 / 20 = 0.500000 (50.0%)
  min_sample_met: True (20 >= 20 threshold)
  Test Status:    PASSED

[Overall Conversion Rate]
  Formula:        4 purchases / 50 visits
  Calculation:    4 / 50 = 0.080000 (8.0%)
  min_sample_met: True (50 >= 30 threshold)
  Test Status:    PASSED

[Rage Click Session Rate]
  Formula:        5 rage click sessions / 50 total sessions
  Calculation:    5 / 50 = 0.100000 (10.0%)
  min_sample_met: True (50 >= 25 threshold)
  Test Status:    PASSED
```

---

## 8. Integration with Downstream Module 4 Components

```
+-------------------+
|   Raw Telemetry   |
+---------+---------+
          |
          v
+-------------------+
|   MetricsEngine   | -----> Generates strict MetricResult (pure code, explicit N/D, Optional value)
+---------+---------+
          |
          +---------------------------------------+
          |                                       |
          v                                       v
+-----------------------+               +-----------------------+
|  Component 2: Digest  |               |  Component 5: Linker  |
|     Rule Engine       |               |     Audit Engine      |
|                       |               |                       |
| Period-over-period    |               | Resolves evidence_ref |
| comparison via delta: |               | back to stored query  |
| (curr - prior)/prior  |               | spec for verification |
+-----------+-----------+               +-----------+-----------+
            |                                       |
            +-------------------+-------------------+
                                |
                                v
                    +-----------------------+
                    |  Component 7: Policy  |
                    |     Safety Gate       |
                    |                       |
                    | Checks ActionPlan     |
                    | limits against metric |
                    | polarity & thresholds |
                    +-----------------------+
```

1. **Component 2 (Anomaly Digest Engine)**: Compares current window `MetricResult` against prior window `MetricResult`, deriving `@computed_field delta_pct`, `@computed_field delta_pp`, and raising `DigestFlag` with dual-window `min_sample_met` gating and two-proportion z-tests.
2. **Component 5 (Evidence Linker)**: Embeds immutable `evidence_ref` stored query specs into the merchant audit ledger, guaranteeing that every AI-generated recommendation can reproduce its exact event counts.
3. **Component 7 (Policy Safety Gate)**: Evaluates merchant guardrails (e.g. maximum coupon discount percentages, budget shift ceilings) based on verified funnel drop-off severity before any action is approved or dispatched.
