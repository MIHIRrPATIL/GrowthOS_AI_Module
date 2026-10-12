"""
Verified Multi-Channel Order Feed Synthetic Generator
GrowthOS Randomized Scenario Test Environment

Simulates backend-verified orders, including ad-blocked sessions,
offline store POS orders, refunds, and cancellations.

Strictly NO emojis in code, docstrings, or logs.
"""

import uuid
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.scenario import TenantSpec


class VerifiedOrder(BaseModel):
    """Verified order record from backend transaction store."""
    model_config = ConfigDict(extra="forbid")

    order_id: str
    tenant_id: str
    customer_id: str
    channel: str  # online_web, mobile_app, offline_pos
    subtotal_paise: int = Field(gt=0)
    delivery_fee_paise: int = Field(ge=0)
    discount_paise: int = Field(ge=0, default=0)
    net_paid_paise: int = Field(gt=0)
    status: str = "completed"  # completed, refunded, cancelled
    timestamp: float
    items_count: int = Field(gt=0, default=1)
    is_ad_blocked: bool = False


class OrderFeedGenerator:
    """
    Generates verified order feed independent of client browser telemetry.
    """

    def __init__(self, tenant: TenantSpec, rng: np.random.Generator):
        self.tenant = tenant
        self.rng = rng
        self.orders: List[VerifiedOrder] = []

    def generate_orders(
        self,
        customer_ids: List[str],
        order_count: int,
        base_timestamp: float = 1776000000.0,
        refund_rate: float = 0.02,
        cancellation_rate: float = 0.01,
        ad_block_rate: float = 0.08,
    ) -> List[VerifiedOrder]:
        """Generates independent verified order stream."""
        self.orders = []
        channels = ["online_web", "mobile_app", "offline_pos"]
        channel_weights = [0.65, 0.25, 0.10]

        for i in range(order_count):
            oid = f"v_ord_{i+1:06d}"
            cid = customer_ids[int(self.rng.integers(0, len(customer_ids)))]
            channel = self.rng.choice(channels, p=channel_weights)
            ts = base_timestamp + float(i * 30)

            # AOV drawn with log-normal distribution around tenant AOV
            factor = float(self.rng.lognormal(mean=0.0, sigma=0.30))
            subtotal = max(2000, int(round(self.tenant.aov_paise * factor)))

            # Delivery fee
            if channel == "offline_pos" or subtotal >= self.tenant.free_delivery_threshold_paise:
                del_fee = 0
            else:
                del_fee = self.tenant.delivery_fee_paise

            net_paid = subtotal + del_fee

            # Status determination
            rand_status = self.rng.uniform()
            if rand_status < cancellation_rate:
                status = "cancelled"
            elif rand_status < (cancellation_rate + refund_rate):
                status = "refunded"
            else:
                status = "completed"

            is_ad_block = bool(self.rng.uniform() < ad_block_rate)

            order = VerifiedOrder(
                order_id=oid,
                tenant_id=self.tenant.tenant_id,
                customer_id=cid,
                channel=channel,
                subtotal_paise=subtotal,
                delivery_fee_paise=del_fee,
                discount_paise=0,
                net_paid_paise=net_paid,
                status=status,
                timestamp=ts,
                items_count=int(self.rng.integers(1, 6)),
                is_ad_blocked=is_ad_block,
            )
            self.orders.append(order)

        return self.orders
