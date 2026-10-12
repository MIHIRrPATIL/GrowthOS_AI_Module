"""
Server Order Domain Models (Authoritative Financial & Transaction Ground Truth)
GrowthOS Module 4: AI Growth Brain

Captures server-verified purchase transactions from merchant OMS, ERP,
or payment gateway webhooks (e.g., Razorpay, Stripe, Shopify).
Prevents financial metrics from relying on unverified browser-side DOM events.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator
import uuid


class ServerOrder(BaseModel):
    """
    Authoritative financial order record ingested directly from backend systems.
    Monetary amounts strictly stored as 64-bit integer paise (1 INR = 100 paise).
    """
    model_config = ConfigDict(extra="allow")

    tenant_id: str = Field(..., description="Multi-tenant merchant workspace identifier")
    order_id: str = Field(..., description="Canonical merchant order ID (e.g. ORD_99812)")
    customer_id: Optional[str] = Field(default=None, description="Authenticated customer identifier")
    session_id: Optional[str] = Field(default=None, description="Linked client-side session identifier")
    anonymous_id: Optional[str] = Field(default=None, description="Linked client-side anonymous cookie ID")
    source: str = Field(default="server_webhook", description="Ingestion source (razorpay, stripe, shopify, oms)")
    currency: str = Field(default="INR", description="Three-letter ISO currency code")
    subtotal_paise: int = Field(..., ge=0, description="Order subtotal before discounts/taxes in integer paise")
    discount_paise: int = Field(default=0, ge=0, description="Applied discounts in integer paise")
    tax_paise: int = 0
    total_paid_paise: int = Field(..., ge=0, description="Final collected amount in integer paise")
    total_paid_inr: float = Field(..., ge=0.0, description="Collected amount in decimal INR")
    payment_status: str = Field(default="captured", description="Payment status: captured, refunded, failed")
    gateway_reference: Optional[str] = Field(default=None, description="Payment gateway transaction ID")
    occurred_at: str = Field(..., description="Timestamp when order was captured (ISO-8601)")
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Ingestion watermark timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def compute_inr_or_paise(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "total_paid_paise" in data and "total_paid_inr" not in data:
                data["total_paid_inr"] = round(data["total_paid_paise"] / 100.0, 2)
            elif "total_paid_inr" in data and "total_paid_paise" not in data:
                data["total_paid_paise"] = int(round(data["total_paid_inr"] * 100))
        return data
