"""
GrowthOS Loyalty & Rewards — Phase 1 data model.

Design guarantees baked in at the DATABASE level (not just app code):

1. Wallet balances can never go negative:
   -> CHECK (available_points >= 0) on customer_wallets.
      This is the last line of defense during redemption; even if the
      application logic had a bug or two requests raced past the
      row lock somehow, Postgres itself refuses the write.

2. Loyalty transactions are an append-only ledger:
   -> No ORM update()/delete() path is exposed for LoyaltyTransaction.
   -> A Postgres trigger (see migrations/002_insert_only_ledger.sql) raises
      on UPDATE/DELETE of loyalty_transactions at the database level, so even
      a raw SQL statement outside this app can't mutate history.
   -> Partial unique indexes (see LoyaltyTransaction) additionally guarantee
      that an original transaction is refunded at most once and that a
      referral pays out at most one BONUS.
      Corrections happen via new compensating rows (type=ADJUST/REFUND),
      exactly like the spec's refund/cancellation logic.

3. Points are never accepted from the client:
   -> LoyaltyTransaction.points has no client-settable path in the API;
      it is only ever computed server-side in services.py, either by the
      rule engine (earn) or from the reward's point_cost (redeem).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Enum as SAEnum,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class Base(DeclarativeBase):
    pass


class TxnType(str, enum.Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"
    EXPIRE = "EXPIRE"
    ADJUST = "ADJUST"
    REFUND = "REFUND"
    BONUS = "BONUS"


class ProgramStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class ReferralStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class Role(str, enum.Enum):
    """RBAC roles, lowest to highest privilege."""

    VIEWER = "VIEWER"      # read-only
    OPERATOR = "OPERATOR"  # run earn/redeem/referral flows, create wallets
    ADMIN = "ADMIN"        # configure programs/rules/rewards, refunds, manage API keys


class Organization(Base):
    """Tenant. Every other row is scoped to one of these (RBAC/isolation boundary)."""

    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("org"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    programs: Mapped[list["LoyaltyProgram"]] = relationship(back_populates="organization")


class LoyaltyProgram(Base):
    __tablename__ = "loyalty_programs"

    program_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("prog"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ProgramStatus] = mapped_column(
        SAEnum(ProgramStatus, name="program_status"), default=ProgramStatus.ACTIVE, nullable=False
    )
    currency: Mapped[str] = mapped_column(String, default="INR", nullable=False)
    points_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Server-side referral reward. NULL = referrals are not rewarded in this
    # program. The client never supplies a bonus amount.
    referral_bonus_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "referral_bonus_points IS NULL OR referral_bonus_points > 0",
            name="ck_program_referral_bonus_positive",
        ),
    )

    organization: Mapped["Organization"] = relationship(back_populates="programs")
    rules: Mapped[list["LoyaltyRule"]] = relationship(back_populates="program")
    rewards: Mapped[list["Reward"]] = relationship(back_populates="program")
    wallets: Mapped[list["CustomerWallet"]] = relationship(back_populates="program")


class LoyaltyRule(Base):
    """
    Deterministic earn rule: `points = floor(spend / per_amount) * points_per_unit`,
    gated by min_spend / active window / weekday multiplier.

    Rules are evaluated by the rule engine server-side only (services.py:
    evaluate_best_rule). Clients never supply the resulting point amount.
    """

    __tablename__ = "loyalty_rules"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rule"))
    program_id: Mapped[str] = mapped_column(ForeignKey("loyalty_programs.program_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Condition: minimum spend (in program currency, minor-unit-free decimal) to qualify.
    min_spend: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    # Action: points_per_unit points awarded per per_amount spent.
    per_amount: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=100, nullable=False)
    points_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional multiplier, e.g. "double points on weekends". 1 = no multiplier.
    multiplier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Priority: higher number wins when multiple active rules match ("highest matching rule").
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Per-transaction cap on awarded points (0/NULL = uncapped).
    max_points_per_txn: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    program: Mapped["LoyaltyProgram"] = relationship(back_populates="rules")

    __table_args__ = (
        CheckConstraint("min_spend >= 0", name="ck_rule_min_spend_nonneg"),
        CheckConstraint("per_amount > 0", name="ck_rule_per_amount_positive"),
        CheckConstraint("points_per_unit >= 0", name="ck_rule_points_per_unit_nonneg"),
        CheckConstraint("multiplier >= 1", name="ck_rule_multiplier_min_1"),
    )


class Reward(Base):
    """
    A redeemable benefit. point_cost is the ONLY source of truth for how many
    points a redemption costs — the client only ever sends a reward_id.
    """

    __tablename__ = "rewards"

    reward_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rwd"))
    program_id: Mapped[str] = mapped_column(ForeignKey("loyalty_programs.program_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    point_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    stock_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    program: Mapped["LoyaltyProgram"] = relationship(back_populates="rewards")

    __table_args__ = (
        CheckConstraint("point_cost > 0", name="ck_reward_point_cost_positive"),
        CheckConstraint("stock_remaining IS NULL OR stock_remaining >= 0", name="ck_reward_stock_nonneg"),
    )


class CustomerWallet(Base):
    """
    The wallet balance is a cached/denormalized aggregate of the transaction
    ledger, kept consistent with it inside the SAME DB transaction as every
    ledger insert (see services.py). The CHECK constraint below is the
    database-level backstop against ever going negative — required even
    though the app also validates in-code, per the spec ("always performs a
    check constraint at the database level, not the cache, when redeeming").
    """

    __tablename__ = "customer_wallets"

    wallet_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("wallet"))
    program_id: Mapped[str] = mapped_column(ForeignKey("loyalty_programs.program_id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)

    available_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[str] = mapped_column(String, default="STANDARD", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    program: Mapped["LoyaltyProgram"] = relationship(back_populates="wallets")

    __table_args__ = (
        UniqueConstraint("program_id", "customer_id", name="uq_wallet_program_customer"),
        # DATABASE-LEVEL backstop: balance can never go negative, no matter what
        # code path touched it. This is enforced by Postgres itself on every
        # UPDATE, not by an application-level cache check.
        CheckConstraint("available_points >= 0", name="ck_wallet_available_points_nonneg"),
        CheckConstraint("lifetime_points >= 0", name="ck_wallet_lifetime_points_nonneg"),
    )


class LoyaltyTransaction(Base):
    """
    Immutable, insert-only ledger row. This is the single source of truth for
    every points movement; CustomerWallet.available_points is a running
    cache derived from these rows, always updated in the same DB transaction
    as the insert.

    There is intentionally NO update_transaction / delete_transaction
    function anywhere in this codebase, and the migration
    002_insert_only_ledger.sql additionally blocks UPDATE/DELETE at the
    Postgres level via triggers, so this holds even against out-of-band SQL.
    """

    __tablename__ = "loyalty_transactions"

    transaction_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("txn"))
    program_id: Mapped[str] = mapped_column(ForeignKey("loyalty_programs.program_id"), nullable=False)
    wallet_id: Mapped[str] = mapped_column(ForeignKey("customer_wallets.wallet_id"), nullable=False)
    type: Mapped[TxnType] = mapped_column(SAEnum(TxnType, name="txn_type"), nullable=False)

    # Signed points delta actually applied to the wallet in this same DB
    # transaction. Positive for EARN/BONUS/REFUND-of-a-redeem, negative for
    # REDEEM/EXPIRE/ADJUST-down. This value is ALWAYS computed server-side.
    points: Mapped[int] = mapped_column(Integer, nullable=False)

    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    # Provenance: exactly one of these should typically be set, recording
    # *why* the server computed `points` the way it did — never a client-sent
    # point amount.
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("loyalty_rules.rule_id"), nullable=True)
    reward_id: Mapped[str | None] = mapped_column(ForeignKey("rewards.reward_id"), nullable=True)
    referral_id: Mapped[str | None] = mapped_column(ForeignKey("referrals.referral_id"), nullable=True)
    related_transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("loyalty_transactions.transaction_id"), nullable=True
    )

    spend_amount: Mapped[Numeric | None] = mapped_column(Numeric(12, 2), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("balance_after >= 0", name="ck_txn_balance_after_nonneg"),
        UniqueConstraint("wallet_id", "idempotency_key", name="uq_txn_wallet_idempotency"),
        # An original transaction can be reversed at most once (database-level
        # backstop for the application check in services.refund_transaction).
        Index(
            "uq_txn_single_refund",
            "related_transaction_id",
            unique=True,
            postgresql_where=text("type = 'REFUND'"),
        ),
        # A referral pays out at most one bonus.
        Index(
            "uq_txn_single_referral_bonus",
            "referral_id",
            unique=True,
            postgresql_where=text("type = 'BONUS'"),
        ),
    )


class Referral(Base):
    __tablename__ = "referrals"

    referral_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ref"))
    program_id: Mapped[str] = mapped_column(ForeignKey("loyalty_programs.program_id"), nullable=False)
    referrer_wallet_id: Mapped[str] = mapped_column(ForeignKey("customer_wallets.wallet_id"), nullable=False)
    referee_customer_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ReferralStatus] = mapped_column(
        SAEnum(ReferralStatus, name="referral_status"), default=ReferralStatus.PENDING, nullable=False
    )
    bonus_points_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "bonus_points_awarded IS NULL OR bonus_points_awarded > 0", name="ck_referral_bonus_positive"
        ),
    )


class ApiKey(Base):
    """
    Tenant-bound credential. The raw key is shown exactly once at creation;
    only its SHA-256 digest is stored (keys are 256-bit random values, so a
    fast hash is appropriate — unlike human passwords). Every authenticated
    request resolves to (organization_id, role) from this table, and every
    query downstream is scoped to that organization.
    """

    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("key"))
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)  # display only, e.g. "gos_AbCd"
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="api_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("key_hash", name="uq_api_key_hash"),)
