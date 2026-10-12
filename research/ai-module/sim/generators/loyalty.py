"""
Module 1 Loyalty & Rewards Synthetic Generator
GrowthOS Randomized Scenario Test Environment

Maintains true generator ledgers for customer points, tiers, fee waivers, and cooldowns.

Strictly NO emojis in code, docstrings, or logs.
"""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.scenario import TenantSpec, LoyaltyTier, TenantLoyaltyProfile


class SimulatedCustomer(BaseModel):
    """Customer loyalty state in simulation ledger."""
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    name: str
    tier: LoyaltyTier
    opening_points: int = Field(ge=0)
    closing_points: int = Field(ge=0)
    lifetime_points_earned: int = Field(default=0, ge=0)
    lifetime_points_redeemed: int = Field(default=0, ge=0)
    waiver_count: int = Field(default=0, ge=0)
    total_waiver_savings_paise: int = Field(default=0, ge=0)
    waiver_timestamps: List[float] = Field(default_factory=list)
    consent_retention: bool = True


class LoyaltyEventRecord(BaseModel):
    """Immutable ledger record of a loyalty state mutation."""
    model_config = ConfigDict(extra="forbid")

    event_id: str
    tenant_id: str
    customer_id: str
    event_type: str  # loyalty.points_earned, loyalty.points_redeemed, loyalty.waiver_applied, etc.
    points: int = 0
    fee_waived_paise: int = 0
    timestamp: float
    idempotency_key: str
    details: Dict[str, Any] = Field(default_factory=dict)


class LoyaltyGenerator:
    """
    Generates customer loyalty cohorts, tracks true points ledgers, and applies fee waivers.
    """

    INDIAN_NAMES = [
        "Aarav Sharma", "Ananya Iyer", "Rohan Mehta", "Priya Patel",
        "Vikram Singh", "Sneha Rao", "Aditya Verma", "Kavya Nair",
        "Rahul Gupta", "Neha Kulkarni", "Arjun Reddy", "Pooja Joshi",
        "Kunal Deshmukh", "Riya Sen", "Amitabh Roy", "Tanvi Bhat",
    ]

    def __init__(self, tenant: TenantSpec, rng: np.random.Generator, pool_size: int = 100):
        self.tenant = tenant
        self.loyalty_profile = tenant.loyalty
        self.rng = rng
        self.customers: Dict[str, SimulatedCustomer] = {}
        self.ledger: List[LoyaltyEventRecord] = []
        self.total_waivers_spent_paise = 0

        self._initialize_customer_pool(pool_size)

    def _determine_tier(self, points: int) -> LoyaltyTier:
        thresholds = self.loyalty_profile.tier_thresholds
        if points >= thresholds.get("Platinum", 5000):
            return LoyaltyTier.PLATINUM
        elif points >= thresholds.get("Gold", 1500):
            return LoyaltyTier.GOLD
        elif points >= thresholds.get("Silver", 500):
            return LoyaltyTier.SILVER
        return LoyaltyTier.BRONZE

    def _initialize_customer_pool(self, pool_size: int):
        """Draws opening points using Gamma distribution for realistic long tail."""
        gamma_draws = self.rng.gamma(shape=2.0, scale=180.0, size=pool_size)
        for i in range(pool_size):
            cust_id = f"CUST-{1000 + i}"
            name = self.INDIAN_NAMES[i % len(self.INDIAN_NAMES)]
            opening_pts = int(round(gamma_draws[i]))
            tier = self._determine_tier(opening_pts)
            consent = bool(self.rng.uniform() > 0.05)  # 95% consent rate

            self.customers[cust_id] = SimulatedCustomer(
                customer_id=cust_id,
                name=name,
                tier=tier,
                opening_points=opening_pts,
                closing_points=opening_pts,
                lifetime_points_earned=opening_pts,
                lifetime_points_redeemed=0,
                waiver_count=0,
                total_waiver_savings_paise=0,
                waiver_timestamps=[],
                consent_retention=consent,
            )

    def earn_points_on_order(
        self,
        customer_id: str,
        order_subtotal_paise: int,
        timestamp: float,
        order_id: Optional[str] = None
    ) -> Optional[LoyaltyEventRecord]:
        """Calculates and credits points earned from an order checkout."""
        cust = self.customers.get(customer_id)
        if not cust or order_subtotal_paise <= 0:
            return None

        subtotal_inr = order_subtotal_paise / 100.0
        points_earned = int(subtotal_inr * self.loyalty_profile.points_earn_ratio)
        if points_earned <= 0:
            return None

        cust.closing_points += points_earned
        cust.lifetime_points_earned += points_earned
        cust.tier = self._determine_tier(cust.closing_points)

        record = LoyaltyEventRecord(
            event_id=f"loy_{uuid.uuid4().hex[:12]}",
            tenant_id=self.tenant.tenant_id,
            customer_id=customer_id,
            event_type="loyalty.points_earned",
            points=points_earned,
            fee_waived_paise=0,
            timestamp=timestamp,
            idempotency_key=f"earn_{order_id or uuid.uuid4().hex[:8]}",
            details={
                "order_subtotal_paise": order_subtotal_paise,
                "closing_points": cust.closing_points,
                "tier": cust.tier.value,
            },
        )
        self.ledger.append(record)
        return record

    def apply_delivery_fee_waiver(
        self,
        customer_id: str,
        fee_amount_paise: int,
        timestamp: float,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, Optional[LoyaltyEventRecord], str]:
        """
        Executes delivery fee waiver action against true customer ledger.
        Enforces point balance, cooldown, and merchant daily spend caps.
        """
        cust = self.customers.get(customer_id)
        if not cust:
            return False, None, "CUSTOMER_NOT_FOUND"

        waiver_cost_pts = self.loyalty_profile.delivery_fee_waiver_cost_points
        cooldown_sec = self.loyalty_profile.waiver_cooldown_hours * 3600

        # Check points balance
        if cust.closing_points < waiver_cost_pts:
            return False, None, "INSUFFICIENT_POINTS"

        # Check cooldown
        if cust.waiver_timestamps:
            last_waiver_ts = cust.waiver_timestamps[-1]
            if (timestamp - last_waiver_ts) < cooldown_sec:
                return False, None, "COOLDOWN_ACTIVE"

        # Check merchant daily spend cap
        if (self.total_waivers_spent_paise + fee_amount_paise) > self.loyalty_profile.daily_waiver_budget_paise:
            return False, None, "MERCHANT_DAILY_BUDGET_EXCEEDED"

        # Execute waiver
        cust.closing_points -= waiver_cost_pts
        cust.lifetime_points_redeemed += waiver_cost_pts
        cust.waiver_count += 1
        cust.total_waiver_savings_paise += fee_amount_paise
        cust.waiver_timestamps.append(timestamp)
        self.total_waivers_spent_paise += fee_amount_paise

        idem_key = idempotency_key or f"waiver_{uuid.uuid4().hex[:12]}"
        record = LoyaltyEventRecord(
            event_id=f"loy_{uuid.uuid4().hex[:12]}",
            tenant_id=self.tenant.tenant_id,
            customer_id=customer_id,
            event_type="loyalty.waiver_applied",
            points=waiver_cost_pts,
            fee_waived_paise=fee_amount_paise,
            timestamp=timestamp,
            idempotency_key=idem_key,
            details={
                "points_deducted": waiver_cost_pts,
                "closing_points": cust.closing_points,
                "fee_amount_paise": fee_amount_paise,
            },
        )
        self.ledger.append(record)
        return True, record, "SUCCESS"

    def get_customer(self, customer_id: str) -> Optional[SimulatedCustomer]:
        return self.customers.get(customer_id)

    def get_ledger(self) -> List[LoyaltyEventRecord]:
        return list(self.ledger)
