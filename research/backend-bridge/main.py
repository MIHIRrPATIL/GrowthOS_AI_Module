"""
GrowthOS Module 2 Backend Bridge & Ingestion Service
Supports:
- Event Ingestion & Deduplication
- Heuristic Derived Signal Processing (Module 4)
- Funnel Analytics (Macro E-Commerce & Granular 5-Step Checkout Sub-steps)
- Dormant Cart Absence Signal Cohort Management & Retention Triggers
- Vertical Template Library & Custom Event Schema Registry
"""

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from schemas import BatchEventRequest, EventEnvelope, DerivedBehavioralSignal
from signal_processor import SignalProcessor
from mock_customer_graph import CustomerGraphBridge
from metrics_engine import MetricsEngine
from digest_engine import DigestEngine

app = FastAPI(
    title="GrowthOS Module 2 Ingestion & Behavior Bridge",
    description="High-throughput ingestion bridge, derived signal processor, and Customer Graph builder for Module 4.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

signal_processor = SignalProcessor()
customer_graph = CustomerGraphBridge()
metrics_engine = MetricsEngine()
digest_engine = DigestEngine(metrics_engine=metrics_engine)

# In-memory storage & caches
seen_idempotency_keys = set()
ingested_events_log: List[EventEnvelope] = []
custom_merchant_events: List[Dict[str, Any]] = []

# Mock Seed Data for Funnels & Dormant Carts
dormant_carts_db = [
    {
        "cohort_id": "COHORT-DORMANT-01",
        "customer_id": "CUST-48291",
        "customer_name": "Rahul Sharma",
        "email": "rahul.sharma@example.in",
        "phone": "+91 98765 43210",
        "tier": "Gold",
        "loyalty_points": 250,
        "cart_total": 588,
        "cart_items": [
            {"name": "Farmhouse Pizza (Medium, Cheese Burst)", "price": 433, "quantity": 1},
            {"name": "Garlic Breadsticks", "price": 109, "quantity": 1},
            {"name": "Pepsi 500ml", "price": 60, "quantity": 1}
        ],
        "dormant_duration_minutes": 142,
        "abandoned_step": "Step 2: Delivery Slot (₹60 Delivery Fee Friction)",
        "recommended_action": "Waive ₹60 Delivery Fee using 60 Gold Points",
        "action_status": "pending"
    },
    {
        "cohort_id": "COHORT-DORMANT-02",
        "customer_id": "CUST-10492",
        "customer_name": "Priya Patel",
        "email": "priya.p@example.com",
        "phone": "+91 91234 56780",
        "tier": "Silver",
        "loyalty_points": 80,
        "cart_total": 359,
        "cart_items": [
            {"name": "Chicken Dominator Pizza", "price": 359, "quantity": 1}
        ],
        "dormant_duration_minutes": 85,
        "abandoned_step": "Step 1: Address Entry",
        "recommended_action": "Send 1-Click WhatsApp Recovery link with DOMINOS50 Coupon",
        "action_status": "pending"
    }
]


class RetentionActionRequest(BaseModel):
    customer_id: str
    action_type: str  # e.g. "loyalty_delivery_waiver", "whatsapp_cart_link", "discount_push"
    coupon_code: Optional[str] = None
    custom_message: Optional[str] = None


class CustomEventSchemaRequest(BaseModel):
    event_name: str
    description: str
    vertical: str
    properties: List[Dict[str, str]]  # [{"name": "vehicle_model", "type": "string"}]


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "growthos-behavior-bridge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_events_ingested": len(ingested_events_log),
        "total_signals_derived": len(signal_processor.get_all_signals()),
        "total_graph_nodes": len(customer_graph.nodes)
    }


@app.post("/api/v1/events/batch")
def ingest_event_batch(
    batch: BatchEventRequest,
    x_growthos_project_id: Optional[str] = Header(None),
    x_growthos_workspace_id: Optional[str] = Header(None)
):
    processed = 0
    duplicates = 0
    signals_count = 0

    for event in batch.events:
        if event.idempotency_key in seen_idempotency_keys:
            duplicates += 1
            continue

        seen_idempotency_keys.add(event.idempotency_key)
        ingested_events_log.append(event)
        processed += 1

        # 1. Update Graph
        customer_graph.ingest_event_to_graph(event)

        # 2. Derive Signals
        new_signals = signal_processor.process_event(event)
        for sig in new_signals:
            customer_graph.attach_signal_to_graph(sig)
            signals_count += 1

    return {
        "status": "success",
        "received": len(batch.events),
        "processed": processed,
        "duplicates_skipped": duplicates,
        "new_signals_generated": signals_count
    }


@app.get("/api/v1/funnels/ecommerce")
def get_ecommerce_funnel():
    """
    Macro E-Commerce Funnel: Browse -> Cart -> Checkout -> Purchase
    """
    return {
        "funnel_name": "E-Commerce Macro Conversion Funnel",
        "timeframe": "Last 7 Days",
        "conversion_window": "24 hours",
        "overall_conversion_rate": 10.97,
        "steps": [
            {
                "step_index": 1,
                "step_name": "Browse / Product Viewed",
                "event": "product.viewed",
                "sessions_count": 1240,
                "conversion_from_previous": 100.0,
                "drop_off_percentage": 0.0,
                "drop_off_count": 0
            },
            {
                "step_index": 2,
                "step_name": "Added to Cart",
                "event": "cart.item_added",
                "sessions_count": 422,
                "conversion_from_previous": 34.03,
                "drop_off_percentage": 65.97,
                "drop_off_count": 818
            },
            {
                "step_index": 3,
                "step_name": "Started Checkout",
                "event": "checkout.started",
                "sessions_count": 223,
                "conversion_from_previous": 52.84,
                "drop_off_percentage": 47.16,
                "drop_off_count": 199
            },
            {
                "step_index": 4,
                "step_name": "Purchase Completed",
                "event": "purchase.completed",
                "sessions_count": 136,
                "conversion_from_previous": 60.98,
                "drop_off_percentage": 39.02,
                "drop_off_count": 87
            }
        ]
    }


@app.get("/api/v1/funnels/checkout-steps")
def get_granular_checkout_funnel():
    """
    Granular 5-Step Checkout Funnel:
    Identifies exact sub-step drop-offs (e.g. shipping fee vs payment error).
    """
    return {
        "funnel_name": "Granular Multi-Step Checkout Funnel",
        "timeframe": "Last 7 Days",
        "total_checkout_starters": 223,
        "total_purchasers": 78,
        "funnel_conversion_rate": 34.98,
        "steps": [
            {
                "step_number": 1,
                "name": "Step 1: Checkout Started",
                "event": "checkout.started",
                "count": 223,
                "conversion_pct": 100.0,
                "drop_off_pct": 0.0,
                "friction_signals": {"hesitation_pauses": 12, "rage_clicks": 2}
            },
            {
                "step_number": 2,
                "name": "Step 2: Shipping & Address Entered",
                "event": "checkout.step_completed (step 1)",
                "count": 183,
                "conversion_pct": 82.06,
                "drop_off_pct": 17.94,
                "friction_signals": {"excessive_backspaces": 28, "address_hesitation": 19}
            },
            {
                "step_number": 3,
                "name": "Step 3: Delivery Slot & Charges Reviewed",
                "event": "checkout.step_completed (step 2)",
                "count": 102,
                "conversion_pct": 55.73,
                "drop_off_pct": 44.27,  # Primary Bottleneck!
                "bottleneck": True,
                "friction_reason": "₹60 Delivery Fee hesitation on orders under ₹800",
                "friction_signals": {"exit_intent_triggers": 41, "hesitation_pauses": 64}
            },
            {
                "step_number": 4,
                "name": "Step 4: Payment Method Selected",
                "event": "checkout.step_completed (step 3)",
                "count": 85,
                "conversion_pct": 83.33,
                "drop_off_pct": 16.67,
                "friction_signals": {"card_validation_errors": 4, "upi_intent_timeouts": 7}
            },
            {
                "step_number": 5,
                "name": "Step 5: Purchase Completed",
                "event": "purchase.completed",
                "count": 78,
                "conversion_pct": 91.76,
                "drop_off_pct": 8.24,
                "friction_signals": {}
            }
        ]
    }


@app.get("/api/v1/cohorts/dormant-carts")
def get_dormant_carts():
    """
    Absence Signal Cohort: Customers who added items to cart >1 hour ago with no purchase.
    """
    return {
        "cohort_name": "Dormant / Abandoned Carts (>1 Hour)",
        "total_at_risk_customers": len(dormant_carts_db),
        "total_at_risk_revenue": sum(c["cart_total"] for c in dormant_carts_db),
        "customers": dormant_carts_db
    }


@app.post("/api/v1/actions/trigger-retention")
def trigger_retention_action(request: RetentionActionRequest):
    """
    Executes Module 1 / Module 4 retention triggers (Loyalty point waivers, WhatsApp recovery).
    """
    target = next((c for c in dormant_carts_db if c["customer_id"] == request.customer_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Customer not found in dormant cart cohort.")

    target["action_status"] = f"executed ({request.action_type})"
    target["action_timestamp"] = datetime.now(timezone.utc).isoformat()

    return {
        "status": "success",
        "message": f"Retention action '{request.action_type}' dispatched to {target['customer_name']}.",
        "customer_id": request.customer_id,
        "action_details": {
            "type": request.action_type,
            "coupon_code": request.coupon_code or "AUTO-APPLIED",
            "dispatched_at": target["action_timestamp"]
        }
    }


@app.get("/api/v1/templates")
def get_vertical_templates():
    """
    Pre-configured Vertical Templates & Modular Event Switchboard
    """
    return {
        "verticals": [
            {
                "id": "ecommerce",
                "name": "E-Commerce & Food Delivery",
                "description": "Standard catalog, cart lifecycle, multi-step checkout, and delivery tracking.",
                "icon": "ShoppingCart",
                "default_funnel": ["product.viewed", "cart.item_added", "checkout.started", "purchase.completed"],
                "granular_steps": [
                    "checkout.started",
                    "checkout.shipping_entered",
                    "checkout.delivery_slot_selected",
                    "checkout.payment_entered",
                    "purchase.completed"
                ],
                "modular_events": [
                    {"event": "product.viewed", "category": "catalog", "enabled": True, "description": "User views product detail card"},
                    {"event": "product.customized", "category": "catalog", "enabled": True, "description": "User customizes crust/toppings/size"},
                    {"event": "cart.item_added", "category": "cart", "enabled": True, "description": "Item added to cart"},
                    {"event": "cart.item_removed", "category": "cart", "enabled": True, "description": "Item removed from cart"},
                    {"event": "cart.coupon_applied", "category": "cart", "enabled": True, "description": "Promo coupon applied"},
                    {"event": "checkout.started", "category": "checkout", "enabled": True, "description": "User initiates checkout flow"},
                    {"event": "checkout.step_completed", "category": "checkout", "enabled": True, "description": "Sub-step completed in checkout"},
                    {"event": "checkout.abandoned", "category": "checkout", "enabled": True, "description": "Checkout abandoned at friction point"},
                    {"event": "purchase.completed", "category": "conversion", "enabled": True, "description": "Order confirmed and paid"}
                ]
            },
            {
                "id": "saas",
                "name": "B2B / B2C SaaS Platform",
                "description": "User signups, free trials, feature activation, and subscription upgrades.",
                "icon": "Laptop",
                "default_funnel": ["user.signup", "trial.started", "feature.activated", "subscription.upgraded"],
                "granular_steps": [
                    "user.signup",
                    "workspace.created",
                    "invite.sent",
                    "core_feature.used",
                    "subscription.upgraded"
                ],
                "modular_events": [
                    {"event": "user.signup", "category": "onboarding", "enabled": True, "description": "User creates account"},
                    {"event": "trial.started", "category": "onboarding", "enabled": True, "description": "14-day free trial started"},
                    {"event": "feature.activated", "category": "engagement", "enabled": True, "description": "Core feature first usage"},
                    {"event": "subscription.upgraded", "category": "conversion", "enabled": True, "description": "Paid tier upgrade"}
                ]
            },
            {
                "id": "bookings",
                "name": "Services & Bookings",
                "description": "Service browsing, calendar slot selection, booking form, and confirmation.",
                "icon": "Calendar",
                "default_funnel": ["service.viewed", "slot.selected", "booking.started", "booking.confirmed"],
                "granular_steps": [
                    "service.viewed",
                    "calendar.slot_selected",
                    "client_details.entered",
                    "deposit.paid",
                    "booking.confirmed"
                ],
                "modular_events": [
                    {"event": "service.viewed", "category": "catalog", "enabled": True, "description": "Consultation or service viewed"},
                    {"event": "slot.selected", "category": "booking", "enabled": True, "description": "Date & time slot chosen"},
                    {"event": "booking.started", "category": "booking", "enabled": True, "description": "Contact details form opened"},
                    {"event": "booking.confirmed", "category": "conversion", "enabled": True, "description": "Appointment booked"}
                ]
            },
            {
                "id": "media",
                "name": "Media & Publishing",
                "description": "Article reading, video plays, paywall prompts, and digital subscriptions.",
                "icon": "BookOpen",
                "default_funnel": ["article.read", "paywall.prompted", "checkout.started", "subscription.started"],
                "granular_steps": [
                    "article.read",
                    "scroll.50_percent",
                    "paywall.viewed",
                    "plan.selected",
                    "subscription.started"
                ],
                "modular_events": [
                    {"event": "article.read", "category": "content", "enabled": True, "description": "Article opened"},
                    {"event": "paywall.prompted", "category": "paywall", "enabled": True, "description": "Metered limit reached"},
                    {"event": "subscription.started", "category": "conversion", "enabled": True, "description": "Subscription started"}
                ]
            }
        ],
        "custom_events": custom_merchant_events
    }


@app.post("/api/v1/templates/custom-event")
def create_custom_event(schema: CustomEventSchemaRequest):
    """
    Self-serve custom event registration.
    """
    new_event = {
        "event": schema.event_name,
        "description": schema.description,
        "vertical": schema.vertical,
        "category": "custom",
        "enabled": True,
        "properties": schema.properties,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    custom_merchant_events.append(new_event)
    return {
        "status": "success",
        "message": f"Custom event '{schema.event_name}' registered successfully.",
        "event": new_event
    }


@app.get("/api/v1/behavior/signals")
def get_behavioral_signals(
    user_id: Optional[str] = Query(None, description="Filter by customer_id or anonymous_id")
):
    if user_id:
        signals = signal_processor.get_signals_for_user(user_id)
    else:
        signals = signal_processor.get_all_signals()

    return {
        "count": len(signals),
        "signals": signals
    }


@app.get("/api/v1/customer-graph/{customer_id}")
def get_customer_graph(customer_id: str):
    graph = customer_graph.get_graph_for_customer(customer_id)
    if graph["total_nodes"] == 0:
        raise HTTPException(status_code=404, detail="Customer not found in graph.")
    return graph


@app.get("/api/v1/events")
def get_recent_events(limit: int = 50):
    return {
        "total": len(ingested_events_log),
        "events": ingested_events_log[-limit:]
    }


# ============================================================================
# GrowthOS Module 4: Grounded Cognitive Engines (Component 1 & 2)
# ============================================================================

@app.get("/api/v1/module4/metrics")
def get_module4_metrics(vertical: str = "ecommerce", timeframe: str = "7d", prior: bool = False):
    """
    Component 1: Deterministic metrics calculated for a merchant vertical template.
    Returns plain numbers with exact sample sizes and timestamps.
    """
    metrics = metrics_engine.query_all_metrics(vertical_template_id=vertical, timeframe=timeframe, prior=prior)
    return {
        "vertical_template_id": vertical,
        "timeframe": timeframe,
        "is_prior_period": prior,
        "count": len(metrics),
        "metrics": metrics
    }


@app.get("/api/v1/module4/metrics/{metric_name}")
def get_module4_single_metric(metric_name: str, vertical: str = "ecommerce", timeframe: str = "7d", prior: bool = False):
    """
    Component 1: Returns a single deterministic metric result by name.
    """
    metric = metrics_engine.query_metric(vertical_template_id=vertical, metric_name=metric_name, timeframe=timeframe, prior=prior)
    if not metric:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found for vertical '{vertical}'.")
    return metric


@app.get("/api/v1/module4/digest")
def get_module4_digest(vertical: str = "ecommerce", threshold_pct: float = 10.0, timeframe: str = "7d", period: str = "week_over_week"):
    """
    Component 2: Scheduled / threshold-based Digest Engine comparison.
    Compares current period against prior period and flags metrics moving beyond threshold.
    """
    report = digest_engine.run_digest(
        vertical_template_id=vertical,
        timeframe=timeframe,
        period=period,
        threshold_pct=threshold_pct
    )
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
