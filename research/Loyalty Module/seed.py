"""
Seeds the exact demo fixtures the reference frontend expects:
tenant_demo / demo-program / demo-wallet / demo-reward, plus a base earn
rule and a weekend-double-points promo rule (so the rule engine's
"highest matching active rule wins" logic has something to actually pick
between).

Usage: python seed.py
"""
from decimal import Decimal

from sqlalchemy import select

from app import models
from app.auth import hash_api_key
from app.database import SessionLocal

# Publicly-known DEMO credentials so the reference frontend works out of the
# box. They are real, hashed, tenant-bound keys — but anyone who reads this
# repo knows them. NEVER run this seed against a production database.
DEMO_KEYS = [
    ("demo-api-key", models.Role.ADMIN, "Demo admin key"),
    ("demo-operator-key", models.Role.OPERATOR, "Demo operator key"),
    ("demo-viewer-key", models.Role.VIEWER, "Demo viewer key"),
]


def main():
    db = SessionLocal()
    try:
        org = db.get(models.Organization, "tenant_demo")
        if org is None:
            org = models.Organization(organization_id="tenant_demo", name="GrowthOS Demo Tenant")
            db.add(org)
            db.flush()

        program = db.get(models.LoyaltyProgram, "demo-program")
        if program is None:
            program = models.LoyaltyProgram(
                program_id="demo-program",
                organization_id="tenant_demo",
                name="Demo Rewards Program",
                status=models.ProgramStatus.ACTIVE,
                currency="INR",
                referral_bonus_points=500,
            )
            db.add(program)
            db.flush()
        elif program.referral_bonus_points is None:
            program.referral_bonus_points = 500  # upgrade a revision-1 demo program

        wallet = db.get(models.CustomerWallet, "demo-wallet")
        if wallet is None:
            wallet = models.CustomerWallet(
                wallet_id="demo-wallet",
                program_id="demo-program",
                customer_id="demo-customer",
                organization_id="tenant_demo",
                available_points=0,
                lifetime_points=0,
            )
            db.add(wallet)
            db.flush()

        base_rule = db.get(models.LoyaltyRule, "demo-rule-base")
        if base_rule is None:
            base_rule = models.LoyaltyRule(
                rule_id="demo-rule-base",
                program_id="demo-program",
                name="Base: 10 points per ₹100 spent",
                is_active=True,
                min_spend=Decimal("0"),
                per_amount=Decimal("100"),
                points_per_unit=10,
                multiplier=1,
                priority=0,
            )
            db.add(base_rule)

        promo_rule = db.get(models.LoyaltyRule, "demo-rule-weekend")
        if promo_rule is None:
            promo_rule = models.LoyaltyRule(
                rule_id="demo-rule-weekend",
                program_id="demo-program",
                name="Promo: Double points on orders over ₹500",
                is_active=True,
                min_spend=Decimal("500"),
                per_amount=Decimal("100"),
                points_per_unit=10,
                multiplier=2,
                priority=10,  # outranks the base rule once min_spend is met
            )
            db.add(promo_rule)

        reward = db.get(models.Reward, "demo-reward")
        if reward is None:
            reward = models.Reward(
                reward_id="demo-reward",
                program_id="demo-program",
                name="Free coffee",
                description="One free coffee, on us.",
                point_cost=50,
                is_active=True,
                stock_remaining=None,
            )
            db.add(reward)

        for raw, role, name in DEMO_KEYS:
            h = hash_api_key(raw)
            if db.execute(select(models.ApiKey).where(models.ApiKey.key_hash == h)).scalar_one_or_none() is None:
                db.add(models.ApiKey(
                    organization_id="tenant_demo", name=name, key_hash=h,
                    key_prefix=raw[:8], role=role,
                ))

        db.commit()
        print("Seed complete:")
        print(f"  organization_id = {org.organization_id}")
        print(f"  program_id      = {program.program_id}")
        print(f"  wallet_id       = {wallet.wallet_id} (available_points={wallet.available_points})")
        print("  rules           = demo-rule-base (10 pts/₹100), demo-rule-weekend (20 pts/₹100 if spend>=500)")
        print(f"  reward_id       = {reward.reward_id} ({reward.point_cost} pts)")
        print(f"  referral bonus  = {program.referral_bonus_points} pts (server-side, per program)")
        print("  demo API keys   = demo-api-key (ADMIN), demo-operator-key, demo-viewer-key  [DEV ONLY]")
    finally:
        db.close()


if __name__ == "__main__":
    main()
