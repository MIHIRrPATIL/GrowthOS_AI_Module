-- GrowthOS Loyalty & Rewards — revision 2 schema changes (idempotent).
--
-- Fresh databases get all of this from SQLAlchemy's create_all(); this file
-- brings an EXISTING database (created by revision 1) up to date, because
-- create_all() never alters tables that already exist. Safe to re-run.
--
-- (api_keys is a brand-new table, so create_all() creates it either way.)

-- 1. Server-side referral bonus (replaces the client-supplied bonus_points).
ALTER TABLE loyalty_programs
    ADD COLUMN IF NOT EXISTS referral_bonus_points INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_program_referral_bonus_positive') THEN
        ALTER TABLE loyalty_programs
            ADD CONSTRAINT ck_program_referral_bonus_positive
            CHECK (referral_bonus_points IS NULL OR referral_bonus_points > 0);
    END IF;
END
$$;

-- 2. An original transaction can be refunded at most once.
--    If revision 1 already let a transaction be refunded twice, the ledger is
--    immutable so we cannot repair it here; fail loudly with the offenders.
DO $$
DECLARE
    dup TEXT;
BEGIN
    SELECT string_agg(related_transaction_id, ', ') INTO dup
    FROM (
        SELECT related_transaction_id
        FROM loyalty_transactions
        WHERE type = 'REFUND'
        GROUP BY related_transaction_id
        HAVING COUNT(*) > 1
    ) d;
    IF dup IS NOT NULL THEN
        RAISE EXCEPTION 'Cannot add uq_txn_single_refund: these transactions were already refunded more than once: %. Reconcile them with a compensating ADJUST row, then re-run.', dup;
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_txn_single_refund
    ON loyalty_transactions (related_transaction_id)
    WHERE type = 'REFUND';

-- 3. A referral pays out at most one BONUS.
CREATE UNIQUE INDEX IF NOT EXISTS uq_txn_single_referral_bonus
    ON loyalty_transactions (referral_id)
    WHERE type = 'BONUS';
