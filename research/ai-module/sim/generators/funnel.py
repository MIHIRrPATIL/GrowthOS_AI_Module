"""
E-Commerce Funnel and Session Simulator
GrowthOS Randomized Scenario Test Environment

Simulates user browsing sessions, per-step conversion drop-offs,
cart building, delivery fee evaluation, and loyalty interactions.

Strictly NO emojis in code, docstrings, or logs.
"""

import uuid
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.scenario import TenantSpec, TrafficSpec
from .loyalty import LoyaltyGenerator


class SimulatedSession(BaseModel):
    """End-to-end simulated session trace in ground-truth ledger."""
    model_config = ConfigDict(extra="forbid")

    session_id: str
    tenant_id: str
    customer_id: str
    device: str
    channel: str
    timestamp: float
    steps: List[str]  # e.g. ["view", "cart", "checkout", "payment", "order"]
    cart_total_paise: int = 0
    delivery_fee_paise: int = 0
    fee_waived: bool = False
    order_completed: bool = False
    order_id: Optional[str] = None
    final_amount_paid_paise: int = 0
    points_earned: int = 0


class FunnelGenerator:
    """
    Simulates traffic sessions through the e-commerce purchase funnel.
    """

    DEFAULT_CONVERSIONS = {
        "view_to_cart": 0.28,
        "cart_to_checkout": 0.65,
        "checkout_to_payment": 0.85,
        "payment_to_order": 0.92,
    }

    def __init__(
        self,
        tenant: TenantSpec,
        traffic: TrafficSpec,
        loyalty_generator: LoyaltyGenerator,
        rng: np.random.Generator,
    ):
        self.tenant = tenant
        self.traffic = traffic
        self.loyalty_gen = loyalty_generator
        self.rng = rng
        self.sessions: List[SimulatedSession] = []

    def generate_sessions(self, session_count: int, base_timestamp: float = 1776000000.0) -> List[SimulatedSession]:
        """Simulates session_count sessions through the funnel."""
        cust_ids = list(self.loyalty_gen.customers.keys())
        channels = list(self.traffic.channel_mix.keys())
        channel_weights = [self.traffic.channel_mix[c] for c in channels]
        norm_channel_weights = [w / sum(channel_weights) for w in channel_weights]

        self.sessions = []
        for i in range(session_count):
            sess_id = f"sess_{i+1:06d}"
            cust_id = cust_ids[int(self.rng.integers(0, len(cust_ids)))]
            device = "mobile" if self.rng.uniform() < self.traffic.mobile_share else "desktop"
            channel = self.rng.choice(channels, p=norm_channel_weights)
            sess_time = base_timestamp + float(i * 5)  # 5-second increments

            steps = ["view"]
            cart_total = 0
            del_fee = 0
            fee_waived = False
            order_completed = False
            order_id = None
            final_paid = 0
            points_earned = 0

            # Step 1 -> 2 (Cart)
            if self.rng.uniform() < self.DEFAULT_CONVERSIONS["view_to_cart"]:
                steps.append("cart")
                # Cart total drawn around tenant AOV with log-normal shape
                cart_factor = float(self.rng.lognormal(mean=0.0, sigma=0.35))
                cart_total = max(1000, int(round(self.tenant.aov_paise * cart_factor)))

                # Delivery fee
                if cart_total < self.tenant.free_delivery_threshold_paise:
                    del_fee = self.tenant.delivery_fee_paise
                else:
                    del_fee = 0

                # Step 2 -> 3 (Checkout)
                if self.rng.uniform() < self.DEFAULT_CONVERSIONS["cart_to_checkout"]:
                    steps.append("checkout")

                    # Opportunity for Delivery Fee Waiver via Loyalty Module
                    if del_fee > 0:
                        cust = self.loyalty_gen.get_customer(cust_id)
                        if cust and cust.consent_retention:
                            success, record, reason = self.loyalty_gen.apply_delivery_fee_waiver(
                                customer_id=cust_id,
                                fee_amount_paise=del_fee,
                                timestamp=sess_time,
                            )
                            if success:
                                fee_waived = True

                    # Step 3 -> 4 (Payment)
                    if self.rng.uniform() < self.DEFAULT_CONVERSIONS["checkout_to_payment"]:
                        steps.append("payment")

                        # Step 4 -> 5 (Order Completed)
                        if self.rng.uniform() < self.DEFAULT_CONVERSIONS["payment_to_order"]:
                            steps.append("order")
                            order_completed = True
                            order_id = f"ord_{uuid.uuid4().hex[:10]}"
                            final_del_fee = 0 if fee_waived else del_fee
                            final_paid = cart_total + final_del_fee

                            # Loyalty Points Earn on Order
                            earn_record = self.loyalty_gen.earn_points_on_order(
                                customer_id=cust_id,
                                order_subtotal_paise=cart_total,
                                timestamp=sess_time,
                                order_id=order_id,
                            )
                            if earn_record:
                                points_earned = earn_record.points

            session = SimulatedSession(
                session_id=sess_id,
                tenant_id=self.tenant.tenant_id,
                customer_id=cust_id,
                device=device,
                channel=channel,
                timestamp=sess_time,
                steps=steps,
                cart_total_paise=cart_total,
                delivery_fee_paise=del_fee,
                fee_waived=fee_waived,
                order_completed=order_completed,
                order_id=order_id,
                final_amount_paid_paise=final_paid,
                points_earned=points_earned,
            )
            self.sessions.append(session)

        return self.sessions
