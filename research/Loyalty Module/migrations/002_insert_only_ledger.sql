-- GrowthOS Loyalty & Rewards — insert-only ledger enforcement
--
-- Requirement: "No update or delete path — transactions are insert only,
-- therefore a clean audit trail."
--
-- The application code already never calls UPDATE/DELETE on
-- loyalty_transactions (see app/services.py: corrections are done via new
-- compensating REFUND/ADJUST rows). This migration additionally enforces
-- that at the DATABASE level, so the guarantee holds even against a raw
-- psql session, a future engineer's ad-hoc script, or a compromised
-- credential that isn't the app's own role.
--
-- Approach: a trigger that raises an exception on UPDATE or DELETE. (A
-- rule-based no-op silently swallows the statement, which is worse for an
-- audit trail — we want callers to get a loud, explicit failure.)

CREATE OR REPLACE FUNCTION reject_ledger_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'loyalty_transactions is an insert-only audit ledger; % is not permitted (row transaction_id=%). Use a compensating INSERT (e.g. type=REFUND/ADJUST) instead.',
        TG_OP,
        COALESCE(OLD.transaction_id, 'unknown');
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_loyalty_transactions_no_update ON loyalty_transactions;
CREATE TRIGGER trg_loyalty_transactions_no_update
    BEFORE UPDATE ON loyalty_transactions
    FOR EACH ROW
    EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS trg_loyalty_transactions_no_delete ON loyalty_transactions;
CREATE TRIGGER trg_loyalty_transactions_no_delete
    BEFORE DELETE ON loyalty_transactions
    FOR EACH ROW
    EXECUTE FUNCTION reject_ledger_mutation();
