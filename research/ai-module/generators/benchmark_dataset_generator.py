"""
Evaluation Benchmark Dataset Generator (200 Ground Truth Cases)
GrowthOS Module 4: AI Growth Brain

Generates 200 non-circular benchmark cases for cart abandonment and intervention decisions:
- 50 Gray-zone edge cases (cart near waiver threshold, moderate deliberation)
- 50 Habitual converters (high cart, frequent orders -> suppress incentive to prevent cannibalization)
- 50 Payment friction drop-offs (payment failure / gateway error within 15m -> rescue trigger)
- 50 High-consideration long browse sessions (viewed 8+ items over 30m without cart add -> NOOP)

Output format: JSON Lines (JSONL) with allowed options:
["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"]

Strictly NO emojis in code, docstrings, or logs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def generate_gray_zone_cases() -> List[Dict[str, Any]]:
    """
    50 Gray-zone edge cases.
    Carts near threshold (INR 450 to 550), moderate deliberation (view ratio 1.5 - 4.0),
    idle 20 to 45 mins.
    - If customer identified AND cart >= INR 500 (50,000 paise) -> PROPOSE_WAIVER (30 cases)
    - If cart < INR 500 (e.g. INR 460 - 495) -> NOOP (12 cases)
    - If anonymous visitor -> NOOP (8 cases)
    """
    cases = []
    
    # 30 cases: Identified customer, subtotal >= 50,000 paise (INR 500), moderate deliberation -> PROPOSE_WAIVER
    for i in range(1, 31):
        case_id = f"gz_{i:03d}"
        cart_paise = 50000 + (i * 1500) # INR 515 to 545
        idle_m = 25.0 + (i % 15)
        views = 3 + (i % 4)
        adds = 1 + (i % 2)
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "gray_zone_edge_case",
            "description": f"Gray-zone cart with moderate deliberation and subtotal INR {cart_paise / 100:.2f} meeting threshold.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": f"cust_gz_{i:03d}",
                "anonymous_id": f"anon_gz_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 65000,
                "idle_minutes": idle_m,
                "product_views_count": views,
                "cart_adds_count": adds,
                "funnel_stage": "cart_drawer",
                "lifetime_orders_count": 2 + (i % 4),
                "has_payment_failure": False,
                "friction_events_count": 0
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "PROPOSE_WAIVER",
            "converted_without_intervention": False,
            "converted_with_intervention": True,
            "margin_impact_paise": int(round(cart_paise * 0.25)) - 5000,
            "rationale": f"Identified customer with cart INR {cart_paise / 100:.2f} (exceeds INR 500 threshold), idle for {idle_m}m, deliberated {views} views for {adds} adds. Qualifies for fee waiver."
        })

    # 12 cases: Identified customer, subtotal < 50,000 paise (INR 450 - 495) -> NOOP
    for i in range(31, 43):
        case_id = f"gz_{i:03d}"
        cart_paise = 45000 + ((i - 30) * 350) # INR 453.50 to 492
        idle_m = 22.0 + (i % 10)
        views = 4 + (i % 3)
        adds = 1
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "gray_zone_edge_case",
            "description": f"Near-threshold cart with subtotal INR {cart_paise / 100:.2f} strictly below the INR 500 policy threshold.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": f"cust_gz_{i:03d}",
                "anonymous_id": f"anon_gz_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 65000,
                "idle_minutes": idle_m,
                "product_views_count": views,
                "cart_adds_count": adds,
                "funnel_stage": "cart_drawer",
                "lifetime_orders_count": 3,
                "has_payment_failure": False,
                "friction_events_count": 0
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "NOOP",
            "converted_without_intervention": False,
            "converted_with_intervention": False,
            "margin_impact_paise": 0,
            "rationale": f"Cart subtotal INR {cart_paise / 100:.2f} is below the merchant policy threshold of INR 500.00. Proposing a waiver is strictly prohibited."
        })

    # 8 cases: Anonymous visitor with cart >= INR 500 -> NOOP (cannot message unauthenticated visitor)
    for i in range(43, 51):
        case_id = f"gz_{i:03d}"
        cart_paise = 52000 + ((i - 42) * 1000)
        idle_m = 35.0
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "gray_zone_edge_case",
            "description": f"Anonymous visitor cart with subtotal INR {cart_paise / 100:.2f} lacking authenticated customer_id.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": None,
                "anonymous_id": f"anon_gz_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 65000,
                "idle_minutes": idle_m,
                "product_views_count": 4,
                "cart_adds_count": 2,
                "funnel_stage": "cart",
                "lifetime_orders_count": 0,
                "has_payment_failure": False,
                "friction_events_count": 0
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "NOOP",
            "converted_without_intervention": False,
            "converted_with_intervention": False,
            "margin_impact_paise": 0,
            "rationale": "Anonymous guest with no linked customer_id. Outbound communication and fee waivers are prohibited under invariant 14."
        })

    return cases


def generate_habitual_converter_cases() -> List[Dict[str, Any]]:
    """
    50 Habitual Converters (hc_001 to hc_050).
    High cart value (INR 800 - 3500), frequent past orders (5 to 25 orders),
    short deliberation (1-2 views per add), high purchase propensity (>= 0.85).
    Ground truth: SUPPRESS_INCENTIVE (avoids fee waiver margin cannibalization).
    """
    cases = []
    for i in range(1, 51):
        case_id = f"hc_{i:03d}"
        cart_paise = 85000 + (i * 5000) # INR 900 to INR 3350
        past_orders = 5 + (i % 18)
        views = 2 + (i % 3)
        adds = 2 + (i % 2)
        idle_m = 16.0 + (i % 12)
        stage = "checkout_address_step_1" if (i % 2 == 0) else "checkout_review_step_2"
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "habitual_converter",
            "description": f"Frequent buyer ({past_orders} prior orders) with high-value cart INR {cart_paise / 100:.2f} at {stage}.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": f"cust_hc_{i:03d}",
                "anonymous_id": f"anon_hc_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 60000,
                "idle_minutes": idle_m,
                "product_views_count": views,
                "cart_adds_count": adds,
                "funnel_stage": stage,
                "lifetime_orders_count": past_orders,
                "has_payment_failure": False,
                "friction_events_count": 0
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "SUPPRESS_INCENTIVE",
            "converted_without_intervention": True,
            "converted_with_intervention": True,
            "margin_impact_paise": int(round(cart_paise * 0.25)),
            "rationale": f"Habitual customer with {past_orders} lifetime orders, high cart value (INR {cart_paise / 100:.2f}), and organic purchase propensity >= 0.85. Proposing an incentive causes unnecessary margin cannibalization."
        })
    return cases


def generate_payment_friction_cases() -> List[Dict[str, Any]]:
    """
    50 Payment Friction Drop-offs (pf_001 to pf_050).
    Checkout step 2 or payment gateway errors, card decline, or rage clicks within 15m.
    High intent customer blocked by system failure.
    Ground truth: RESCUE_FRICTION (trigger proactive support / payment link rescue).
    """
    cases = []
    error_types = ["GATEWAY_TIMEOUT", "UPI_DECLINE_RETRYABLE", "PAYMENT_AUTH_FAILED", "CARD_3DS_FAILURE"]
    for i in range(1, 51):
        case_id = f"pf_{i:03d}"
        cart_paise = 45000 + (i * 3000)
        err = error_types[i % len(error_types)]
        idle_m = 4.0 + (i % 10) # Fresh failure within 15 mins
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "payment_friction_dropoff",
            "description": f"Payment failure ({err}) encountered at checkout payment step {idle_m} minutes ago.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": f"cust_pf_{i:03d}",
                "anonymous_id": f"anon_pf_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 60000,
                "idle_minutes": idle_m,
                "product_views_count": 4,
                "cart_adds_count": 2,
                "funnel_stage": "checkout_payment_step_2",
                "lifetime_orders_count": 2 + (i % 6),
                "has_payment_failure": True,
                "friction_events_count": 1 + (i % 3),
                "last_error_code": err
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "RESCUE_FRICTION",
            "converted_without_intervention": False,
            "converted_with_intervention": True,
            "margin_impact_paise": int(round(cart_paise * 0.25)),
            "rationale": f"High intent buyer halted by technical error {err} at payment gateway. Immediate rescue outreach or alternate payment link required, not standard discount."
        })
    return cases


def generate_long_browse_cases() -> List[Dict[str, Any]]:
    """
    50 High-Consideration Long Browse Sessions (lb_001 to lb_050).
    Viewed 8+ items over 30-90m, 0 cart adds or low conviction cart with idle > 120m.
    Propensity <= 0.15.
    Ground truth: NOOP (preserves budget, avoids bothering browsing users).
    """
    cases = []
    for i in range(1, 51):
        case_id = f"lb_{i:03d}"
        views = 8 + (i % 15) # 8 to 22 views
        adds = 0 if (i % 3 != 0) else 1
        cart_paise = 0 if adds == 0 else 18000 # Small cart if any
        idle_m = 35.0 + (i * 2.0)
        cases.append({
            "case_id": case_id,
            "task_type": "cart_abandonment_decision",
            "category": "long_browse_low_intent",
            "description": f"Window shopping browse session ({views} views, {adds} adds) with {idle_m}m idle time.",
            "input_context": {
                "tenant_id": "tenant_benchmark_01",
                "customer_id": f"cust_lb_{i:03d}" if (i % 2 == 0) else None,
                "anonymous_id": f"anon_lb_{i:03d}",
                "cart_subtotal_paise": cart_paise,
                "tenant_aov_paise": 60000,
                "idle_minutes": idle_m,
                "product_views_count": views,
                "cart_adds_count": adds,
                "funnel_stage": "product_detail_page" if adds == 0 else "cart",
                "lifetime_orders_count": 0 if (i % 2 != 0) else 1,
                "has_payment_failure": False,
                "friction_events_count": 0
            },
            "allowed_options": ["PROPOSE_WAIVER", "SUPPRESS_INCENTIVE", "RESCUE_FRICTION", "NOOP"],
            "ground_truth": "NOOP",
            "converted_without_intervention": False,
            "converted_with_intervention": False,
            "margin_impact_paise": 0,
            "rationale": f"High browse ratio ({views} views to {adds} adds) indicates window shopping or low purchase conviction (propensity <= 0.15). Do not spend notification budget or offer discounts."
        })
    return cases


def generate_and_save_dataset(output_path: Path):
    """
    Builds the complete 200-case dataset and writes to JSONL.
    """
    gz = generate_gray_zone_cases()
    hc = generate_habitual_converter_cases()
    pf = generate_payment_friction_cases()
    lb = generate_long_browse_cases()

    assert len(gz) == 50, f"Expected 50 gray-zone cases, got {len(gz)}"
    assert len(hc) == 50, f"Expected 50 habitual converter cases, got {len(hc)}"
    assert len(pf) == 50, f"Expected 50 payment friction cases, got {len(pf)}"
    assert len(lb) == 50, f"Expected 50 long browse cases, got {len(lb)}"

    all_cases = gz + hc + pf + lb
    assert len(all_cases) == 200, f"Expected 200 total cases, got {len(all_cases)}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for c in all_cases:
            f.write(json.dumps(c) + "\n")

    print(f"Successfully generated {len(all_cases)} benchmark cases to {output_path}")


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "ground_truth_decisions.jsonl"
    generate_and_save_dataset(out_file)
