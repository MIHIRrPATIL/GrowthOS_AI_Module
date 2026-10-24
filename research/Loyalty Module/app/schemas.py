from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Organizations ----------
class OrganizationCreate(BaseModel):
    name: str


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: str
    name: str
    created_at: datetime


class OrganizationCreated(OrganizationOut):
    # Shown exactly once; only a hash is stored server-side.
    api_key: str
    api_key_id: str


# ---------- Auth / API keys ----------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeOut(BaseModel):
    organization_id: str
    role: str
    key_id: str
    auth_method: str


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: Literal["VIEWER", "OPERATOR", "ADMIN"] = "OPERATOR"


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key_id: str
    name: str
    role: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    api_key: str  # shown exactly once


# ---------- Programs ----------
class ProgramCreate(BaseModel):
    # No organization_id: a program always belongs to the caller's own
    # organization (resolved from the credential). If an old client still
    # sends one it is ignored, never trusted.
    name: str
    currency: str = "INR"
    points_expiry_days: int | None = None
    referral_bonus_points: int | None = Field(default=None, gt=0)


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    program_id: str
    organization_id: str
    name: str
    status: str
    currency: str
    points_expiry_days: int | None
    referral_bonus_points: int | None
    created_at: datetime
    updated_at: datetime


# ---------- Rules ----------
class RuleCreate(BaseModel):
    program_id: str
    name: str
    min_spend: Decimal = Decimal("0")
    per_amount: Decimal = Decimal("100")
    points_per_unit: int = Field(gt=0)
    multiplier: int = Field(default=1, ge=1)
    priority: int = 0
    max_points_per_txn: int | None = None
    is_active: bool = True


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_id: str
    program_id: str
    name: str
    is_active: bool
    min_spend: Decimal
    per_amount: Decimal
    points_per_unit: int
    multiplier: int
    priority: int
    max_points_per_txn: int | None


# ---------- Rewards ----------
class RewardCreate(BaseModel):
    program_id: str
    name: str
    description: str | None = None
    point_cost: int = Field(gt=0)
    stock_remaining: int | None = None
    is_active: bool = True


class RewardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reward_id: str
    program_id: str
    name: str
    description: str | None
    point_cost: int
    is_active: bool
    stock_remaining: int | None


# ---------- Wallets ----------
class WalletCreate(BaseModel):
    program_id: str
    customer_id: str


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    wallet_id: str
    program_id: str
    customer_id: str
    organization_id: str
    available_points: int
    lifetime_points: int
    tier: str
    updated_at: datetime


# ---------- Earn / Redeem ----------
# IMPORTANT: neither of these accepts a point amount from the client.
# EarnRequest only carries the raw spend; the server-side rule engine decides
# how many points that's worth. RedeemRequest only carries a reward_id; the
# server looks up reward.point_cost. This is the enforcement point for
# requirement #2 (points are never client-supplied).
class EarnRequest(BaseModel):
    wallet_id: str
    spend_amount: Decimal = Field(gt=0)
    idempotency_key: str | None = None


class RedeemRequest(BaseModel):
    wallet_id: str
    reward_id: str
    idempotency_key: str | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    program_id: str
    wallet_id: str
    type: str
    points: int
    balance_after: int
    rule_id: str | None
    reward_id: str | None
    referral_id: str | None
    related_transaction_id: str | None
    spend_amount: Decimal | None
    note: str | None
    created_at: datetime


# ---------- Referrals ----------
class ReferralCreate(BaseModel):
    program_id: str
    referrer_wallet_id: str
    referee_customer_id: str


class ReferralCompleteRequest(BaseModel):
    # No bonus_points: the amount comes from the program's configured
    # referral_bonus_points (requirement #2 — never client-supplied).
    referral_id: str
    idempotency_key: str | None = None


class ReferralOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    referral_id: str
    program_id: str
    referrer_wallet_id: str
    referee_customer_id: str
    status: str
    bonus_points_awarded: int | None
    created_at: datetime
    completed_at: datetime | None


class ErrorOut(BaseModel):
    detail: str
