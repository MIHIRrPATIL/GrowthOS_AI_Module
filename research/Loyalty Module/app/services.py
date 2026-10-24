"""
Core loyalty mechanics.

Every function in this file that mutates points does so as ONE atomic
database transaction: wallet row lock -> validation -> rule/reward lookup
-> ledger insert -> balance update -> commit. If anything fails, the whole
thing rolls back — there is no window where a transaction row exists
without a matching balance update, or vice versa (requirement #1).

Tenant isolation: every public function takes `organization_id` (resolved
from the caller's credential in auth.py, never from the request body) and
scopes every lookup to it. A resource that belongs to another tenant is
reported as "not found", exactly like one that doesn't exist, so IDs can't
be probed across tenants.

Concurrency: we take a `SELECT ... FOR UPDATE` row lock on the wallet (and,
where relevant, the reward) at the start of each operation. Lock order is
always wallet -> reward, and referral -> wallet, so operations can't
deadlock. A second concurrent request against the same wallet blocks at the
database until the first commits or rolls back, so two simultaneous
redemptions can never both read the same starting balance and both succeed
(classic double-spend race). The Postgres CHECK constraint on
`available_points >= 0` is the backstop underneath that lock, enforced at
the database level, not against a cache (requirement #3).

Points are computed ONLY in this file, from server-side state (the rule
engine's output for earns, `reward.point_cost` for redemptions,
`program.referral_bonus_points` for referrals). No function here accepts a
caller-supplied point amount (requirement #2).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


class LoyaltyError(Exception):
    """Base class for expected, user-facing loyalty errors (mapped to HTTP in main.py)."""

    status_code = 400


class NotFoundError(LoyaltyError):
    status_code = 404


class ConflictError(LoyaltyError):
    status_code = 409


class InsufficientPointsError(LoyaltyError):
    status_code = 402


# Transaction types a REFUND may reverse. REFUND itself is excluded (a reversal
# can't be reversed — issue a fresh earn/adjust instead); EXPIRE/ADJUST are
# corrected with another ADJUST, not a refund.
REFUNDABLE_TYPES = {models.TxnType.EARN, models.TxnType.REDEEM, models.TxnType.BONUS}


# --------------------------------------------------------------------------
# Rule engine
# --------------------------------------------------------------------------

def evaluate_best_rule(db: Session, program_id: str, spend_amount: Decimal) -> models.LoyaltyRule | None:
    """
    Return the highest-priority ACTIVE rule whose min_spend the given spend
    amount qualifies for. Ties broken by priority desc, then points_per_unit
    desc, so "the highest matching active rule determines the points" is
    well-defined even with overlapping rules (e.g. base rule + weekend promo).
    """
    stmt = (
        select(models.LoyaltyRule)
        .where(
            models.LoyaltyRule.program_id == program_id,
            models.LoyaltyRule.is_active.is_(True),
            models.LoyaltyRule.min_spend <= spend_amount,
        )
        .order_by(models.LoyaltyRule.priority.desc(), models.LoyaltyRule.points_per_unit.desc())
    )
    return db.execute(stmt).scalars().first()


def compute_earn_points(rule: models.LoyaltyRule, spend_amount: Decimal) -> int:
    units = math.floor(spend_amount / rule.per_amount)
    points = int(units * rule.points_per_unit * rule.multiplier)
    if rule.max_points_per_txn is not None:
        points = min(points, rule.max_points_per_txn)
    return max(points, 0)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _lock_wallet(db: Session, wallet_id: str, organization_id: str) -> models.CustomerWallet:
    wallet = db.execute(
        select(models.CustomerWallet)
        .where(
            models.CustomerWallet.wallet_id == wallet_id,
            models.CustomerWallet.organization_id == organization_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if wallet is None:
        raise NotFoundError(f"Wallet '{wallet_id}' not found")
    return wallet


def _idempotent_replay(
    db: Session, wallet_id: str, idempotency_key: str | None, expected_type: models.TxnType
) -> models.LoyaltyTransaction | None:
    """
    Look up a prior transaction for this (wallet, idempotency_key). A key may
    only ever replay the SAME kind of operation — reusing e.g. an earn's key
    for a redemption is a client bug and must not silently return the earn.
    """
    if not idempotency_key:
        return None
    prior = db.execute(
        select(models.LoyaltyTransaction).where(
            models.LoyaltyTransaction.wallet_id == wallet_id,
            models.LoyaltyTransaction.idempotency_key == idempotency_key,
        )
    ).scalar_one_or_none()
    if prior is not None and prior.type != expected_type:
        raise ConflictError("Idempotency key was already used for a different operation")
    return prior


# --------------------------------------------------------------------------
# EARN — single atomic transaction
# --------------------------------------------------------------------------

def earn_points(
    db: Session,
    *,
    organization_id: str,
    wallet_id: str,
    spend_amount: Decimal,
    idempotency_key: str | None = None,
) -> models.LoyaltyTransaction:
    with db.begin():
        wallet = _lock_wallet(db, wallet_id, organization_id)

        replay = _idempotent_replay(db, wallet_id, idempotency_key, models.TxnType.EARN)
        if replay is not None:
            if replay.spend_amount != spend_amount:
                raise ConflictError("Idempotency key was already used with a different spend amount")
            return replay

        program = db.get(models.LoyaltyProgram, wallet.program_id)
        if program is None or program.status != models.ProgramStatus.ACTIVE:
            raise ConflictError("Program is not active")

        rule = evaluate_best_rule(db, wallet.program_id, spend_amount)
        if rule is None:
            raise LoyaltyError("No active earn rule matches this spend amount")

        # Points computed server-side ONLY — never trust a client-sent value.
        points = compute_earn_points(rule, spend_amount)
        if points <= 0:
            raise LoyaltyError("Computed earn amount is zero for this spend")

        wallet.available_points += points
        wallet.lifetime_points += points
        new_balance = wallet.available_points

        txn = models.LoyaltyTransaction(
            program_id=wallet.program_id,
            wallet_id=wallet.wallet_id,
            type=models.TxnType.EARN,
            points=points,
            balance_after=new_balance,
            rule_id=rule.rule_id,
            spend_amount=spend_amount,
            idempotency_key=idempotency_key,
            note=f"Earned via rule '{rule.name}'",
        )
        db.add(txn)
        try:
            db.flush()
        except IntegrityError as exc:
            raise ConflictError("Duplicate idempotency key for this wallet") from exc

    db.refresh(txn)
    return txn


# --------------------------------------------------------------------------
# REDEEM — single atomic transaction, DB CHECK constraint is the backstop
# --------------------------------------------------------------------------

def redeem_reward(
    db: Session,
    *,
    organization_id: str,
    wallet_id: str,
    reward_id: str,
    idempotency_key: str | None = None,
) -> models.LoyaltyTransaction:
    with db.begin():
        wallet = _lock_wallet(db, wallet_id, organization_id)

        replay = _idempotent_replay(db, wallet_id, idempotency_key, models.TxnType.REDEEM)
        if replay is not None:
            if replay.reward_id != reward_id:
                raise ConflictError("Idempotency key was already used for a different reward")
            return replay

        # Scoped to the wallet's own program: a reward from another program or
        # another tenant is indistinguishable from one that doesn't exist.
        reward = db.execute(
            select(models.Reward)
            .where(models.Reward.reward_id == reward_id, models.Reward.program_id == wallet.program_id)
            .with_for_update()
        ).scalar_one_or_none()
        if reward is None:
            raise NotFoundError(f"Reward '{reward_id}' not found")
        if not reward.is_active:
            raise ConflictError("Reward is not active")
        if reward.stock_remaining is not None and reward.stock_remaining <= 0:
            raise ConflictError("Reward is out of stock")

        # Points cost comes ONLY from server-side reward config, never the client.
        cost = reward.point_cost

        # App-level pre-check for a clean error message...
        if wallet.available_points < cost:
            raise InsufficientPointsError(
                f"Insufficient points: wallet has {wallet.available_points}, reward costs {cost}"
            )

        wallet.available_points -= cost
        new_balance = wallet.available_points  # ...but the CHECK constraint below is what's actually load-bearing.

        if reward.stock_remaining is not None:
            reward.stock_remaining -= 1

        txn = models.LoyaltyTransaction(
            program_id=wallet.program_id,
            wallet_id=wallet.wallet_id,
            type=models.TxnType.REDEEM,
            points=-cost,
            balance_after=new_balance,
            reward_id=reward.reward_id,
            idempotency_key=idempotency_key,
            note=f"Redeemed '{reward.name}'",
        )
        db.add(txn)
        try:
            # This flush is where Postgres evaluates
            # ck_wallet_available_points_nonneg / ck_reward_stock_nonneg
            # against the actual database state under the row lock taken
            # above — the database-level check, not the cache.
            db.flush()
        except IntegrityError as exc:
            msg = str(exc.orig).lower()
            if "ck_wallet_available_points_nonneg" in msg:
                raise InsufficientPointsError("Insufficient points (rejected by database constraint)") from exc
            if "ck_reward_stock_nonneg" in msg:
                raise ConflictError("Reward went out of stock (rejected by database constraint)") from exc
            if "uq_txn_wallet_idempotency" in msg:
                raise ConflictError("Duplicate idempotency key for this wallet") from exc
            raise ConflictError("Redemption rejected by database constraint") from exc

    db.refresh(txn)
    return txn


# --------------------------------------------------------------------------
# REFUND — compensating transaction, ledger stays insert-only
# --------------------------------------------------------------------------

def refund_transaction(
    db: Session, *, organization_id: str, transaction_id: str, note: str | None = None
) -> models.LoyaltyTransaction:
    """
    Reverses an EARN/BONUS (takes the points back) or a REDEEM (gives the
    points back and returns the reward to stock) via a NEW compensating row —
    the original transaction is never edited or deleted.

    A transaction can be refunded at most once. The wallet row lock
    serializes all refunds for a wallet, so the "already refunded?" check
    below is race-free; the partial unique index uq_txn_single_refund is the
    database-level backstop.
    """
    with db.begin():
        # Tenant-scoped lookup (a wallet's organization_id is authoritative).
        original = db.execute(
            select(models.LoyaltyTransaction)
            .join(models.CustomerWallet, models.CustomerWallet.wallet_id == models.LoyaltyTransaction.wallet_id)
            .where(
                models.LoyaltyTransaction.transaction_id == transaction_id,
                models.CustomerWallet.organization_id == organization_id,
            )
        ).scalar_one_or_none()
        if original is None:
            raise NotFoundError(f"Transaction '{transaction_id}' not found")

        wallet = _lock_wallet(db, original.wallet_id, organization_id)

        if original.type not in REFUNDABLE_TYPES:
            raise ConflictError(f"{original.type.value} transactions cannot be refunded")

        prior_refund = db.execute(
            select(models.LoyaltyTransaction.transaction_id).where(
                models.LoyaltyTransaction.related_transaction_id == original.transaction_id,
                models.LoyaltyTransaction.type == models.TxnType.REFUND,
            )
        ).scalar_one_or_none()
        if prior_refund is not None:
            raise ConflictError(f"Transaction was already refunded by '{prior_refund}'")

        # Compensating delta is the exact inverse of the original.
        delta = -original.points
        wallet.available_points += delta
        if original.type in (models.TxnType.EARN, models.TxnType.BONUS):
            # Reversing an earn means those points were never really earned.
            wallet.lifetime_points += delta  # delta is negative here
        # Reversing a REDEEM gives the spend back but is NOT new earning, so
        # lifetime_points (a measure of points earned) is deliberately untouched.

        if original.type == models.TxnType.REDEEM and original.reward_id:
            reward = db.execute(
                select(models.Reward).where(models.Reward.reward_id == original.reward_id).with_for_update()
            ).scalar_one_or_none()
            if reward is not None and reward.stock_remaining is not None:
                reward.stock_remaining += 1

        txn = models.LoyaltyTransaction(
            program_id=original.program_id,
            wallet_id=original.wallet_id,
            type=models.TxnType.REFUND,
            points=delta,
            balance_after=wallet.available_points,
            related_transaction_id=original.transaction_id,
            note=note or f"Refund/reversal of {original.transaction_id}",
        )
        db.add(txn)
        try:
            db.flush()
        except IntegrityError as exc:
            msg = str(exc.orig).lower()
            if "ck_wallet_available_points_nonneg" in msg or "ck_wallet_lifetime_points_nonneg" in msg:
                raise ConflictError(
                    "Cannot reverse this transaction: the points it granted have already been spent"
                ) from exc
            if "uq_txn_single_refund" in msg:
                raise ConflictError("Transaction was already refunded") from exc
            raise ConflictError("Refund rejected by database constraint") from exc

    db.refresh(txn)
    return txn


# --------------------------------------------------------------------------
# Referrals
# --------------------------------------------------------------------------

def create_referral(
    db: Session, *, organization_id: str, program_id: str, referrer_wallet_id: str, referee_customer_id: str
) -> models.Referral:
    with db.begin():
        program = db.execute(
            select(models.LoyaltyProgram).where(
                models.LoyaltyProgram.program_id == program_id,
                models.LoyaltyProgram.organization_id == organization_id,
            )
        ).scalar_one_or_none()
        wallet = db.execute(
            select(models.CustomerWallet).where(
                models.CustomerWallet.wallet_id == referrer_wallet_id,
                models.CustomerWallet.organization_id == organization_id,
                models.CustomerWallet.program_id == program_id,
            )
        ).scalar_one_or_none()
        if program is None or wallet is None:
            raise NotFoundError("Referrer wallet not found for this program")

        if wallet.customer_id == referee_customer_id:
            raise LoyaltyError("A customer cannot refer themselves")

        # Serialize creation per (program, referee) so two referrers can't
        # race past the duplicate check below and both claim the same person.
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"referral:{program_id}:{referee_customer_id}"},
        )
        existing = db.execute(
            select(models.Referral.referral_id).where(
                models.Referral.program_id == program_id,
                models.Referral.referee_customer_id == referee_customer_id,
                models.Referral.status != models.ReferralStatus.REJECTED,
            )
        ).first()
        if existing is not None:
            raise ConflictError("This customer has already been referred in this program")

        referral = models.Referral(
            program_id=program_id,
            referrer_wallet_id=referrer_wallet_id,
            referee_customer_id=referee_customer_id,
            status=models.ReferralStatus.PENDING,
        )
        db.add(referral)

    db.refresh(referral)
    return referral


def complete_referral(
    db: Session, *, organization_id: str, referral_id: str, idempotency_key: str | None = None
) -> models.LoyaltyTransaction:
    """
    Completing a referral creates an immutable BONUS transaction for the
    referrer, atomically with marking the referral COMPLETED. The amount is
    the program's configured referral_bonus_points — never client-supplied.

    Naturally idempotent: completing an already-completed referral (with or
    without an idempotency key) returns the original bonus transaction
    instead of failing or paying twice.
    """
    with db.begin():
        referral = db.execute(
            select(models.Referral)
            .join(models.LoyaltyProgram, models.LoyaltyProgram.program_id == models.Referral.program_id)
            .where(
                models.Referral.referral_id == referral_id,
                models.LoyaltyProgram.organization_id == organization_id,
            )
            .with_for_update(of=models.Referral)
        ).scalar_one_or_none()
        if referral is None:
            raise NotFoundError(f"Referral '{referral_id}' not found")

        wallet = _lock_wallet(db, referral.referrer_wallet_id, organization_id)

        replay = _idempotent_replay(db, wallet.wallet_id, idempotency_key, models.TxnType.BONUS)
        if replay is not None:
            if replay.referral_id != referral.referral_id:
                raise ConflictError("Idempotency key was already used for a different referral")
            return replay

        if referral.status == models.ReferralStatus.COMPLETED:
            return db.execute(
                select(models.LoyaltyTransaction).where(
                    models.LoyaltyTransaction.referral_id == referral.referral_id,
                    models.LoyaltyTransaction.type == models.TxnType.BONUS,
                )
            ).scalar_one()
        if referral.status != models.ReferralStatus.PENDING:
            raise ConflictError(f"Referral is '{referral.status.value}'")

        program = db.get(models.LoyaltyProgram, referral.program_id)
        if program is None or program.status != models.ProgramStatus.ACTIVE:
            raise ConflictError("Program is not active")
        bonus_points = program.referral_bonus_points
        if not bonus_points:
            raise LoyaltyError("This program has no referral bonus configured")

        wallet.available_points += bonus_points
        wallet.lifetime_points += bonus_points

        txn = models.LoyaltyTransaction(
            program_id=referral.program_id,
            wallet_id=wallet.wallet_id,
            type=models.TxnType.BONUS,
            points=bonus_points,
            balance_after=wallet.available_points,
            referral_id=referral.referral_id,
            idempotency_key=idempotency_key,
            note="Referral bonus",
        )
        db.add(txn)

        referral.status = models.ReferralStatus.COMPLETED
        referral.bonus_points_awarded = bonus_points
        referral.completed_at = datetime.now(timezone.utc)

        try:
            db.flush()
        except IntegrityError as exc:
            raise ConflictError("Referral completion rejected by database constraint") from exc

    db.refresh(txn)
    return txn
