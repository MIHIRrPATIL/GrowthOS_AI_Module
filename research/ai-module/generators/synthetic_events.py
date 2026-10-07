"""
Realistic Synthetic Event Generator for GrowthOS
Generates complete customer behavior streams for Domino's Pizza India reference store.
Enables offline development, testing, and calibration from day one.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone, timedelta
import random
import uuid

from domain.events import (
    EventEnvelope,
    PageMetadata,
    UTMMetadata,
    DeviceMetadata,
    NetworkMetadata,
    ConsentState,
)

DOMINOS_MENU = [
    {"product_id": "PRD-PIZZA-FARMHOUSE", "name": "Farmhouse Pizza", "category": "veg_pizza", "base_price": 459.00},
    {"product_id": "PRD-PIZZA-PEP-PANEER", "name": "Peppy Paneer Pizza", "category": "veg_pizza", "base_price": 459.00},
    {"product_id": "PRD-PIZZA-CHK-DOM", "name": "Chicken Dominator Pizza", "category": "non_veg_pizza", "base_price": 599.00},
    {"product_id": "PRD-PIZZA-MARGHERITA", "name": "Margherita Classic", "category": "veg_pizza", "base_price": 239.00},
    {"product_id": "PRD-SIDE-GARLIC-BREAD", "name": "Garlic Breadsticks", "category": "sides", "base_price": 109.00},
    {"product_id": "PRD-BEV-PEPSI-500", "name": "Pepsi 500ml", "category": "beverages", "base_price": 60.00},
]

KNOWN_CUSTOMERS = [
    {"customer_id": "CUST-48291", "name": "Rahul Sharma", "tier": "Gold", "loyalty_points": 250, "phone": "+919876543210"},
    {"customer_id": "CUST-10492", "name": "Priya Patel", "tier": "Silver", "loyalty_points": 80, "phone": "+919123456780"},
    {"customer_id": "CUST-99214", "name": "Amit Verma", "tier": "Platinum", "loyalty_points": 720, "phone": "+919988776655"},
]


class SyntheticEventGenerator:
    """
    Generates synthetic but mathematically consistent event streams.
    """
    def __init__(self, tenant_id: str = "ws_dominos_in", seed: Optional[int] = 42):
        self.tenant_id = tenant_id
        if seed is not None:
            random.seed(seed)
        self.rng = random.Random(seed)

    def generate_session(
        self,
        scenario: Literal["converting", "fee_friction", "rage_click", "dormant"] = "converting",
        customer: Optional[Dict[str, Any]] = None,
        base_time: Optional[datetime] = None,
        tenant_id: Optional[str] = None
    ) -> List[EventEnvelope]:
        """
        Generates an entire coherent behavioral session.
        """
        tid = tenant_id or self.tenant_id
        now = base_time or datetime.now(timezone.utc)
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        anonymous_id = f"anon_{uuid.uuid4().hex[:12]}"
        customer_id = customer["customer_id"] if customer else None

        # Device & UTM
        device = DeviceMetadata(
            device_type=self.rng.choice(["mobile", "desktop", "mobile"]),
            browser=self.rng.choice(["Chrome", "Safari"]),
            os=self.rng.choice(["Android", "iOS", "Windows"])
        )
        utm = UTMMetadata(
            source=self.rng.choice(["meta", "google", "organic", "whatsapp"]),
            medium="cpc" if self.rng.random() > 0.3 else "referral",
            campaign="weekend_mumbai_students"
        )

        events: List[EventEnvelope] = []
        t = now

        # 1. Pageview - Menu
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="page.viewed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            page=PageMetadata(url="https://dominos.co.in/menu", path="/menu", title="Domino's Pizza India"),
            utm=utm,
            device=device,
            properties={"initial_referrer": "https://www.google.com"}
        ))
        t += timedelta(seconds=self.rng.randint(3, 8))

        # 2. Product Views
        selected_product = self.rng.choice(DOMINOS_MENU[:3])
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="product.viewed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            page=PageMetadata(url=f"https://dominos.co.in/menu/{selected_product['product_id']}", path=f"/menu/{selected_product['product_id']}"),
            utm=utm,
            device=device,
            properties=selected_product
        ))
        t += timedelta(seconds=self.rng.randint(5, 15))

        # 3. Product Customized
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="product.customized",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={
                "product_id": selected_product["product_id"],
                "size": "Medium",
                "crust": "Cheese Burst",
                "extra_cheese": True,
                "added_cost": 99.00
            }
        ))
        t += timedelta(seconds=self.rng.randint(4, 10))

        # 4. Added to Cart
        cart_total = selected_product["base_price"] + 99.00 + 109.00  # pizza + garlic bread
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="cart.item_added",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={
                "product_id": selected_product["product_id"],
                "name": selected_product["name"],
                "unit_price": selected_product["base_price"] + 99.00,
                "cart_total": cart_total,
                "item_count": 2
            }
        ))
        t += timedelta(seconds=self.rng.randint(6, 12))

        # Scenario Branching
        if scenario == "dormant":
            # Session abandoned early after adding to cart
            return events

        # 5. Checkout Started
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="checkout.started",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={"cart_total": cart_total, "item_count": 2}
        ))
        t += timedelta(seconds=self.rng.randint(8, 16))

        # 6. Step 1: Address
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="checkout.step_completed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={"step_number": 1, "step_name": "delivery_address", "city": "Mumbai", "pincode": "400076"}
        ))
        t += timedelta(seconds=self.rng.randint(10, 20))

        if scenario == "fee_friction":
            # User hesitates on Step 2 delivery fee of ₹60
            events.append(EventEnvelope(
                tenant_id=tid,
                event_name="user.typing_dynamics",
                occurred_at=t.isoformat(),
                session_id=session_id,
                anonymous_id=anonymous_id,
                customer_id=customer_id,
                device=device,
                properties={"hesitation_pauses_count": 3, "avg_flight_time_ms": 340, "dwell_seconds": 18.5}
            ))
            t += timedelta(seconds=5)
            events.append(EventEnvelope(
                tenant_id=tid,
                event_name="user.exit_intent",
                occurred_at=t.isoformat(),
                session_id=session_id,
                anonymous_id=anonymous_id,
                customer_id=customer_id,
                device=device,
                properties={"velocity_y": -480, "viewport_boundary": "top"}
            ))
            t += timedelta(seconds=2)
            events.append(EventEnvelope(
                tenant_id=tid,
                event_name="checkout.abandoned",
                occurred_at=t.isoformat(),
                session_id=session_id,
                anonymous_id=anonymous_id,
                customer_id=customer_id,
                device=device,
                properties={
                    "step_abandoned_at": "Step 2: Delivery Slot & Charges",
                    "step_number": 2,
                    "cart_value": cart_total,
                    "reason": "delivery_charge_hesitation",
                    "delivery_fee": 60.00
                }
            ))
            return events

        if scenario == "rage_click":
            # User encounters unresponsive CTA button
            for _ in range(4):
                events.append(EventEnvelope(
                    tenant_id=tid,
                    event_name="user.rage_click",
                    occurred_at=t.isoformat(),
                    session_id=session_id,
                    anonymous_id=anonymous_id,
                    customer_id=customer_id,
                    device=device,
                    properties={
                        "tag_name": "BUTTON",
                        "element_id": "btnStartCheckout",
                        "clicks_in_window": 4,
                        "window_ms": 400
                    }
                ))
                t += timedelta(milliseconds=100)
            return events

        # Happy Path: Step 2 & Step 3 Completed
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="checkout.step_completed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={"step_number": 2, "step_name": "delivery_charges_and_slot", "delivery_fee": 60.00}
        ))
        t += timedelta(seconds=self.rng.randint(6, 12))

        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="checkout.step_completed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id,
            device=device,
            properties={"step_number": 3, "step_name": "payment_method", "payment_type": "UPI"}
        ))
        t += timedelta(seconds=self.rng.randint(8, 15))

        # 7. Purchase Completed
        order_id = f"DOM-ORD-{self.rng.randint(100000, 999999)}"
        events.append(EventEnvelope(
            tenant_id=tid,
            event_name="purchase.completed",
            occurred_at=t.isoformat(),
            session_id=session_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id or f"CUST-{self.rng.randint(10000, 99999)}",
            device=device,
            properties={
                "order_id": order_id,
                "subtotal": cart_total,
                "delivery_fee": 60.00,
                "total_amount": cart_total + 60.00,
                "payment_method": "UPI",
                "loyalty_points_earned": int(cart_total // 10)
            }
        ))

        return events

    def generate_batch(
        self,
        session_count: int = 25,
        fee_friction_ratio: float = 0.30,
        rage_click_ratio: float = 0.10,
        dormant_ratio: float = 0.15,
        base_time: Optional[datetime] = None,
        tenant_id: Optional[str] = None
    ) -> List[EventEnvelope]:
        """
        Generates a comprehensive multi-session batch with calibrated behavioral friction.
        """
        all_events: List[EventEnvelope] = []
        base = base_time or datetime.now(timezone.utc)
        tid = tenant_id or self.tenant_id

        for i in range(session_count):
            rand_val = self.rng.random()
            if rand_val < fee_friction_ratio:
                scenario = "fee_friction"
            elif rand_val < (fee_friction_ratio + rage_click_ratio):
                scenario = "rage_click"
            elif rand_val < (fee_friction_ratio + rage_click_ratio + dormant_ratio):
                scenario = "dormant"
            else:
                scenario = "converting"

            # Assign some sessions to identified customers
            cust = self.rng.choice(KNOWN_CUSTOMERS) if self.rng.random() < 0.4 else None
            # Jitter session start times over the last 6 hours
            session_start = base - timedelta(minutes=self.rng.randint(0, 360))
            session_events = self.generate_session(scenario=scenario, customer=cust, base_time=session_start, tenant_id=tid)
            all_events.extend(session_events)

        # Sort all events chronologically by occurred_at
        all_events.sort(key=lambda e: e.occurred_at)
        return all_events
