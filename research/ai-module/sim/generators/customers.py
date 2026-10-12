"""
Customer Identity, Consent & Holdout Synthetic Generator
GrowthOS Randomized Scenario Test Environment

Simulates customer profiles, anonymous-to-login identity stitching,
DPDP consent states, and pre-policy Intent-To-Treat (ITT) holdout splits.

Strictly NO emojis in code, docstrings, or logs.
"""

import uuid
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.scenario import TenantSpec, LoyaltyTier


class CustomerProfile(BaseModel):
    """Rich customer profile with identity, consent, and holdout status."""
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    anonymous_id: str
    name: str
    phone: str
    email: str
    consent_purposes: List[str]  # e.g. ["analytics", "marketing", "retention"]
    is_control_arm: bool = False
    baseline_propensity: float = Field(ge=0.0, le=1.0)
    loyalty_tier: LoyaltyTier = LoyaltyTier.BRONZE
    is_logged_in: bool = False


class CustomerGenerator:
    """
    Generates customer cohorts with deterministic pre-policy ITT holdouts and DPDP consent.
    """

    INDIAN_FIRST_NAMES = [
        "Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Sneha",
        "Aditya", "Kavya", "Rahul", "Neha", "Arjun", "Pooja",
    ]
    INDIAN_LAST_NAMES = [
        "Sharma", "Iyer", "Mehta", "Patel", "Singh", "Rao",
        "Verma", "Nair", "Gupta", "Kulkarni", "Reddy", "Joshi",
    ]

    def __init__(self, tenant: TenantSpec, rng: np.random.Generator, pool_size: int = 100, holdout_rate: float = 0.10):
        self.tenant = tenant
        self.rng = rng
        self.holdout_rate = holdout_rate
        self.customers: Dict[str, CustomerProfile] = {}
        self.anonymous_to_customer: Dict[str, str] = {}

        self._generate_cohort(pool_size)

    def _generate_cohort(self, pool_size: int):
        for i in range(pool_size):
            cid = f"CUST-{2000 + i}"
            anon_id = f"anon_{uuid.uuid4().hex[:12]}"
            fn = self.INDIAN_FIRST_NAMES[i % len(self.INDIAN_FIRST_NAMES)]
            ln = self.INDIAN_LAST_NAMES[i % len(self.INDIAN_LAST_NAMES)]
            name = f"{fn} {ln}"
            phone = f"+9198{self.rng.integers(10000000, 99999999)}"
            email = f"{fn.lower()}.{ln.lower()}{i}@example.com"

            # Pre-policy Intent-To-Treat (ITT) holdout assignment via SHA-256 hash
            hash_int = int(hashlib.sha256(f"holdout:{self.tenant.tenant_id}:{cid}".encode("utf-8")).hexdigest()[:8], 16)
            is_control = (hash_int % 100) < int(self.holdout_rate * 100)

            # DPDP Consent purposes
            purposes = ["analytics"]
            if self.rng.uniform() < 0.90:
                purposes.append("marketing")
            if self.rng.uniform() < 0.85:
                purposes.append("retention")

            # True baseline purchase propensity (Beta distribution: mean ~ 0.20)
            propensity = float(self.rng.beta(a=2.0, b=8.0))

            profile = CustomerProfile(
                customer_id=cid,
                anonymous_id=anon_id,
                name=name,
                phone=phone,
                email=email,
                consent_purposes=purposes,
                is_control_arm=is_control,
                baseline_propensity=round(propensity, 4),
                loyalty_tier=LoyaltyTier.BRONZE,
                is_logged_in=bool(self.rng.uniform() < 0.40),
            )
            self.customers[cid] = profile
            self.anonymous_to_customer[anon_id] = cid

    def resolve_identity(self, anonymous_id: str) -> Optional[CustomerProfile]:
        """Resolves anonymous cookie ID to identified customer profile if stitched."""
        cid = self.anonymous_to_customer.get(anonymous_id)
        if cid:
            return self.customers.get(cid)
        return None

    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        return self.customers.get(customer_id)
