"""Refunds: compensating rows, at-most-once, stock + lifetime correctness."""
import pytest
from sqlalchemy.exc import IntegrityError

from app import models, services
from conftest import (earn, ledger, make_reward, redeem, refund, run_concurrently, session, wallet)


def _row(client, a, txn_id):
    return next(t for t in ledger(client, a) if t["transaction_id"] == txn_id)


def test_refund_of_earn_reverses_points_and_lifetime_and_leaves_original_untouched(client, a):
    first = earn(client, a, 600).json()      # +120
    earn(client, a, 500)                     # +100 (a different order)
    before = _row(client, a, first["transaction_id"])

    r = refund(client, a, first["transaction_id"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["type"], body["points"], body["balance_after"]) == ("REFUND", -120, 100)
    assert body["related_transaction_id"] == first["transaction_id"]

    w = wallet(client, a)
    assert (w["available_points"], w["lifetime_points"]) == (100, 100)
    assert _row(client, a, first["transaction_id"]) == before  # immutable


def test_same_transaction_cannot_be_refunded_twice_even_when_wallet_has_other_points(client, a):
    """Regression: rev-1 let this happen (balance went 1000600 -> 1000200 for a 200-pt earn)."""
    first = earn(client, a, 600).json()
    earn(client, a, 500)
    assert refund(client, a, first["transaction_id"]).status_code == 200
    again = refund(client, a, first["transaction_id"])
    assert again.status_code == 409 and "already refunded" in again.json()["detail"]
    assert wallet(client, a)["available_points"] == 100  # only ONE reversal applied
    assert [t["type"] for t in ledger(client, a)].count("REFUND") == 1


def test_two_simultaneous_refunds_apply_exactly_once(client, a):
    first = earn(client, a, 600).json()
    earn(client, a, 500)

    def attempt(_):
        with session() as db:
            return services.refund_transaction(
                db, organization_id=a.org_id, transaction_id=first["transaction_id"]).transaction_id

    res = run_concurrently(2, attempt)
    assert sum(isinstance(r, str) for r in res) == 1, res
    assert sum(isinstance(r, services.ConflictError) for r in res) == 1, res
    assert wallet(client, a)["available_points"] == 100


def test_database_enforces_single_refund_even_if_app_check_is_bypassed(client, a):
    first = earn(client, a, 600).json()
    earn(client, a, 500)
    assert refund(client, a, first["transaction_id"]).status_code == 200
    with pytest.raises(IntegrityError, match="uq_txn_single_refund"):
        with session() as db:
            db.add(models.LoyaltyTransaction(
                program_id=a.program_id, wallet_id=a.wallet_id, type=models.TxnType.REFUND,
                points=-1, balance_after=0, related_transaction_id=first["transaction_id"]))
            db.commit()


def test_refunding_a_redemption_returns_points_and_stock_but_not_lifetime(client, a):
    rid = make_reward(client, a, 50, stock=5)
    earn(client, a, 1000)  # 200 earned
    red = redeem(client, a, reward_id=rid).json()
    assert wallet(client, a)["available_points"] == 150

    r = refund(client, a, red["transaction_id"])
    assert r.status_code == 200 and r.json()["points"] == 50
    w = wallet(client, a)
    assert w["available_points"] == 200
    assert w["lifetime_points"] == 200  # rev-1 inflated this to 250
    stock = next(x for x in client.get("/api/v1/loyalty/rewards", headers=a.viewer).json() if x["reward_id"] == rid)
    assert stock["stock_remaining"] == 5  # rev-1 never gave the unit back


def test_cannot_reverse_points_that_have_already_been_spent(client, a):
    earned = earn(client, a, 500).json()  # +100
    redeem(client, a)                     # -50 -> 50 left
    r = refund(client, a, earned["transaction_id"])  # would need -100
    assert r.status_code == 409 and "already been spent" in r.json()["detail"]
    assert wallet(client, a)["available_points"] == 50
    assert [t["type"] for t in ledger(client, a)].count("REFUND") == 0


def test_a_refund_cannot_itself_be_refunded(client, a):
    first = earn(client, a, 600).json()
    rf = refund(client, a, first["transaction_id"]).json()
    r = refund(client, a, rf["transaction_id"])
    assert r.status_code == 409
    assert wallet(client, a)["available_points"] == 0


def test_unknown_transaction_is_404(client, a):
    assert refund(client, a, "txn_does_not_exist").status_code == 404
