from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config, models, schemas, services
from .auth import (
    Principal,
    generate_api_key,
    hash_api_key,
    issue_token,
    principal_from_api_key,
    require_platform_admin,
    require_role,
)
from .database import get_db

app = FastAPI(
    title="GrowthOS — Loyalty & Rewards API",
    version="2.0.0",
    description=(
        "Phase 1 Loyalty & Rewards REST API. Authenticate with `X-Api-Key` or a "
        "Bearer token from `POST /api/v1/auth/token`. Every resource is scoped "
        "to the caller's organization; roles are VIEWER < OPERATOR < ADMIN."
    ),
)

# CORS origins come from CORS_ORIGINS (comma-separated; default "*" for local demos).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIEWER = Depends(require_role(models.Role.VIEWER))
OPERATOR = Depends(require_role(models.Role.OPERATOR))
ADMIN = Depends(require_role(models.Role.ADMIN))


def loyalty_error_to_http(exc: services.LoyaltyError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _program_or_404(db: Session, program_id: str, org_id: str) -> models.LoyaltyProgram:
    program = db.execute(
        select(models.LoyaltyProgram).where(
            models.LoyaltyProgram.program_id == program_id,
            models.LoyaltyProgram.organization_id == org_id,
        )
    ).scalar_one_or_none()
    if program is None:
        raise HTTPException(404, f"Program '{program_id}' not found")
    return program


def _wallet_or_404(db: Session, wallet_id: str, org_id: str) -> models.CustomerWallet:
    wallet = db.execute(
        select(models.CustomerWallet).where(
            models.CustomerWallet.wallet_id == wallet_id,
            models.CustomerWallet.organization_id == org_id,
        )
    ).scalar_one_or_none()
    if wallet is None:
        raise HTTPException(404, f"Wallet '{wallet_id}' not found")
    return wallet


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Platform: tenant creation (separate platform credential, off unless configured)
# ---------------------------------------------------------------------------

@app.post("/api/v1/organizations", response_model=schemas.OrganizationCreated, status_code=201)
def create_organization(
    payload: schemas.OrganizationCreate, db: Session = Depends(get_db), _=Depends(require_platform_admin)
):
    org = models.Organization(name=payload.name)
    db.add(org)
    db.flush()
    raw = generate_api_key()
    key = models.ApiKey(
        organization_id=org.organization_id,
        name="Initial admin key",
        key_hash=hash_api_key(raw),
        key_prefix=raw[:8],
        role=models.Role.ADMIN,
    )
    db.add(key)
    db.commit()
    db.refresh(org)
    db.refresh(key)
    return {
        "organization_id": org.organization_id,
        "name": org.name,
        "created_at": org.created_at,
        "api_key": raw,
        "api_key_id": key.key_id,
    }


# ---------------------------------------------------------------------------
# Auth & API-key management
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/token", response_model=schemas.TokenOut)
def create_token(principal: Principal = Depends(principal_from_api_key)):
    """Exchange an API key (X-Api-Key) for a short-lived Bearer JWT."""
    token, ttl = issue_token(principal)
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl}


@app.get("/api/v1/auth/me", response_model=schemas.MeOut)
def whoami(principal: Principal = VIEWER):
    return {
        "organization_id": principal.organization_id,
        "role": principal.role.value,
        "key_id": principal.key_id,
        "auth_method": principal.auth_method,
    }


@app.post("/api/v1/api-keys", response_model=schemas.ApiKeyCreated, status_code=201)
def create_api_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db), principal: Principal = ADMIN):
    raw = generate_api_key()
    key = models.ApiKey(
        organization_id=principal.organization_id,
        name=payload.name,
        key_hash=hash_api_key(raw),
        key_prefix=raw[:8],
        role=models.Role(payload.role),
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {
        "key_id": key.key_id,
        "name": key.name,
        "role": key.role.value,
        "key_prefix": key.key_prefix,
        "is_active": key.is_active,
        "created_at": key.created_at,
        "revoked_at": key.revoked_at,
        "api_key": raw,
    }


@app.get("/api/v1/api-keys", response_model=list[schemas.ApiKeyOut])
def list_api_keys(db: Session = Depends(get_db), principal: Principal = ADMIN):
    stmt = (
        select(models.ApiKey)
        .where(models.ApiKey.organization_id == principal.organization_id)
        .order_by(models.ApiKey.created_at)
    )
    return db.execute(stmt).scalars().all()


@app.delete("/api/v1/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: str, db: Session = Depends(get_db), principal: Principal = ADMIN):
    """Revoke (soft-delete) a key. Takes effect immediately, including for JWTs minted from it."""
    key = db.execute(
        select(models.ApiKey).where(
            models.ApiKey.key_id == key_id,
            models.ApiKey.organization_id == principal.organization_id,
        )
    ).scalar_one_or_none()
    if key is None:
        raise HTTPException(404, f"API key '{key_id}' not found")
    if key.is_active and key.role == models.Role.ADMIN:
        # Lock the org's active admin keys so two concurrent revocations
        # can't each see "another admin exists" and leave the org locked out.
        active_admins = db.execute(
            select(models.ApiKey)
            .where(
                models.ApiKey.organization_id == principal.organization_id,
                models.ApiKey.role == models.Role.ADMIN,
                models.ApiKey.is_active.is_(True),
            )
            .with_for_update()
        ).scalars().all()
        if len(active_admins) <= 1:
            db.rollback()
            raise HTTPException(409, "Cannot revoke the organization's last active ADMIN key")
    key.is_active = False
    key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------

@app.post("/api/v1/loyalty/programs", response_model=schemas.ProgramOut, status_code=201)
def create_program(payload: schemas.ProgramCreate, db: Session = Depends(get_db), principal: Principal = ADMIN):
    program = models.LoyaltyProgram(
        organization_id=principal.organization_id,  # from the credential, never the body
        name=payload.name,
        currency=payload.currency,
        points_expiry_days=payload.points_expiry_days,
        referral_bonus_points=payload.referral_bonus_points,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@app.get("/api/v1/loyalty/programs", response_model=list[schemas.ProgramOut])
def list_programs(db: Session = Depends(get_db), principal: Principal = VIEWER):
    stmt = select(models.LoyaltyProgram).where(models.LoyaltyProgram.organization_id == principal.organization_id)
    return db.execute(stmt).scalars().all()


@app.get("/api/v1/loyalty/programs/{program_id}", response_model=schemas.ProgramOut)
def get_program(program_id: str, db: Session = Depends(get_db), principal: Principal = VIEWER):
    return _program_or_404(db, program_id, principal.organization_id)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@app.post("/api/v1/loyalty/rules", response_model=schemas.RuleOut, status_code=201)
def create_rule(payload: schemas.RuleCreate, db: Session = Depends(get_db), principal: Principal = ADMIN):
    _program_or_404(db, payload.program_id, principal.organization_id)
    rule = models.LoyaltyRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.get("/api/v1/loyalty/rules", response_model=list[schemas.RuleOut])
def list_rules(program_id: str | None = None, db: Session = Depends(get_db), principal: Principal = VIEWER):
    stmt = (
        select(models.LoyaltyRule)
        .join(models.LoyaltyProgram, models.LoyaltyProgram.program_id == models.LoyaltyRule.program_id)
        .where(models.LoyaltyProgram.organization_id == principal.organization_id)
    )
    if program_id:
        stmt = stmt.where(models.LoyaltyRule.program_id == program_id)
    return db.execute(stmt).scalars().all()


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

@app.post("/api/v1/loyalty/rewards", response_model=schemas.RewardOut, status_code=201)
def create_reward(payload: schemas.RewardCreate, db: Session = Depends(get_db), principal: Principal = ADMIN):
    _program_or_404(db, payload.program_id, principal.organization_id)
    reward = models.Reward(**payload.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@app.get("/api/v1/loyalty/rewards", response_model=list[schemas.RewardOut])
def list_rewards(program_id: str | None = None, db: Session = Depends(get_db), principal: Principal = VIEWER):
    stmt = (
        select(models.Reward)
        .join(models.LoyaltyProgram, models.LoyaltyProgram.program_id == models.Reward.program_id)
        .where(models.LoyaltyProgram.organization_id == principal.organization_id)
    )
    if program_id:
        stmt = stmt.where(models.Reward.program_id == program_id)
    return db.execute(stmt).scalars().all()


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------

@app.post("/api/v1/customers/wallets", response_model=schemas.WalletOut, status_code=201)
def create_wallet(payload: schemas.WalletCreate, db: Session = Depends(get_db), principal: Principal = OPERATOR):
    program = _program_or_404(db, payload.program_id, principal.organization_id)

    def existing_wallet():
        return db.execute(
            select(models.CustomerWallet).where(
                models.CustomerWallet.program_id == payload.program_id,
                models.CustomerWallet.customer_id == payload.customer_id,
            )
        ).scalar_one_or_none()

    existing = existing_wallet()
    if existing is not None:
        return existing
    wallet = models.CustomerWallet(
        program_id=payload.program_id,
        customer_id=payload.customer_id,
        organization_id=program.organization_id,
    )
    db.add(wallet)
    try:
        db.commit()
    except IntegrityError:
        # Lost a create race for the same (program, customer): return the winner.
        db.rollback()
        return existing_wallet()
    db.refresh(wallet)
    return wallet


@app.get("/api/v1/customers/wallets/{wallet_id}", response_model=schemas.WalletOut)
def get_wallet(wallet_id: str, db: Session = Depends(get_db), principal: Principal = VIEWER):
    return _wallet_or_404(db, wallet_id, principal.organization_id)


@app.get("/api/v1/customers/wallets/{wallet_id}/transactions", response_model=list[schemas.TransactionOut])
def get_wallet_transactions(wallet_id: str, db: Session = Depends(get_db), principal: Principal = VIEWER):
    _wallet_or_404(db, wallet_id, principal.organization_id)
    stmt = (
        select(models.LoyaltyTransaction)
        .where(models.LoyaltyTransaction.wallet_id == wallet_id)
        .order_by(models.LoyaltyTransaction.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


# ---------------------------------------------------------------------------
# Earn / Redeem — the atomic core of the module
# ---------------------------------------------------------------------------

@app.post("/api/v1/loyalty/earn", response_model=schemas.TransactionOut)
def earn(payload: schemas.EarnRequest, db: Session = Depends(get_db), principal: Principal = OPERATOR):
    try:
        return services.earn_points(
            db,
            organization_id=principal.organization_id,
            wallet_id=payload.wallet_id,
            spend_amount=payload.spend_amount,
            idempotency_key=payload.idempotency_key,
        )
    except services.LoyaltyError as exc:
        raise loyalty_error_to_http(exc)


@app.post("/api/v1/loyalty/rewards/redeem", response_model=schemas.TransactionOut)
def redeem(payload: schemas.RedeemRequest, db: Session = Depends(get_db), principal: Principal = OPERATOR):
    try:
        return services.redeem_reward(
            db,
            organization_id=principal.organization_id,
            wallet_id=payload.wallet_id,
            reward_id=payload.reward_id,
            idempotency_key=payload.idempotency_key,
        )
    except services.LoyaltyError as exc:
        raise loyalty_error_to_http(exc)


@app.post("/api/v1/loyalty/transactions/{transaction_id}/refund", response_model=schemas.TransactionOut)
def refund(transaction_id: str, db: Session = Depends(get_db), principal: Principal = ADMIN):
    try:
        return services.refund_transaction(
            db, organization_id=principal.organization_id, transaction_id=transaction_id
        )
    except services.LoyaltyError as exc:
        raise loyalty_error_to_http(exc)


@app.get("/api/v1/loyalty/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(program_id: str | None = None, db: Session = Depends(get_db), principal: Principal = VIEWER):
    stmt = (
        select(models.LoyaltyTransaction)
        .join(models.LoyaltyProgram, models.LoyaltyProgram.program_id == models.LoyaltyTransaction.program_id)
        .where(models.LoyaltyProgram.organization_id == principal.organization_id)
        .order_by(models.LoyaltyTransaction.created_at.desc())
    )
    if program_id:
        stmt = stmt.where(models.LoyaltyTransaction.program_id == program_id)
    return db.execute(stmt).scalars().all()


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------

@app.post("/api/v1/loyalty/referrals", response_model=schemas.ReferralOut, status_code=201)
def create_referral(payload: schemas.ReferralCreate, db: Session = Depends(get_db), principal: Principal = OPERATOR):
    try:
        return services.create_referral(
            db,
            organization_id=principal.organization_id,
            program_id=payload.program_id,
            referrer_wallet_id=payload.referrer_wallet_id,
            referee_customer_id=payload.referee_customer_id,
        )
    except services.LoyaltyError as exc:
        raise loyalty_error_to_http(exc)


@app.post("/api/v1/loyalty/referrals/complete", response_model=schemas.TransactionOut)
def complete_referral(
    payload: schemas.ReferralCompleteRequest, db: Session = Depends(get_db), principal: Principal = OPERATOR
):
    try:
        return services.complete_referral(
            db,
            organization_id=principal.organization_id,
            referral_id=payload.referral_id,
            idempotency_key=payload.idempotency_key,
        )
    except services.LoyaltyError as exc:
        raise loyalty_error_to_http(exc)
