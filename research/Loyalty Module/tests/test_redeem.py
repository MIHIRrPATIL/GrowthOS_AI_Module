"""Redeem flow + the three database-level guarantees + concurrency."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import services
from app.database import engine
from conftest import (earn, ledger, make_program, make_reward, new_wallet, redeem,
                      run_concurrently, session, wallet)


# ---------------------------------------------------------------- behaviour

def test_redeem_deducts_server_side_cost(client, a):
    earn(client, a, 1000)  # 200 pts
    r = redeem(client, a)
    assert r.status_code == 200, r.text
    assert (r.json()["type"], r.json()["points"], r.json()["balance_after"]) == ("REDEEM", -50, 150)
    assert r.json()["reward_id"] == a.reward_id
    assert wallet(client, a)["available_points"] == 150


def test_client_cannot_choose_the_cost(client, a):
    earn(client, a, 1000)
    r = redeem(client, a, points=1, point_cost=1)  # spoofed
    assert r.json()["points"] == -50
    assert wallet(client, a)["available_points"] == 150


def test_insufficient_points_is_402_and_leaves_no_partial_state(client, a):
    earn(client, a, 400)  # 40 pts < cost 50
    r = redeem(client, a)
    assert r.status_code == 402
    assert wallet(client, a)["available_points"] == 40
    assert [t["type"] for t in ledger(client, a)] == ["EARN"]


def test_drain_to_exactly_zero_then_next_attempt_rejected(client, a):
    earn(client, a, 500)  # 100 pts
    assert redeem(client, a).status_code == 200
    assert redeem(client, a).status_code == 200
    assert wallet(client, a)["available_points"] == 0
    assert redeem(client, a).status_code == 402
    assert wallet(client, a)["available_points"] == 0


def test_limited_stock_is_decremented_then_exhausted(client, a):
    rid = make_reward(client, a, 50, stock=1)
    earn(client, a, 1000)
    assert redeem(client, a, reward_id=rid).status_code == 200
    r = redeem(client, a, reward_id=rid)
    assert r.status_code == 409 and "out of stock" in r.json()["detail"]
    stock = [x for x in client.get("/api/v1/loyalty/rewards", headers=a.viewer).json() if x["reward_id"] == rid][0]
    assert stock["stock_remaining"] == 0


def test_inactive_reward_cannot_be_redeemed(client, a):
    rid = make_reward(client, a, 50, active=False)
    earn(client, a, 1000)
    assert redeem(client, a, reward_id=rid).status_code == 409


def test_reward_from_another_program_is_404(client, a):
    other_program = make_program(client, a)
    foreign = make_reward(client, a, 10, program_id=other_program)
    earn(client, a, 1000)
    assert redeem(client, a, reward_id=foreign).status_code == 404


def test_idempotent_redeem_replays_without_double_charge(client, a):
    earn(client, a, 1000)
    r1, r2 = redeem(client, a, key="redeem-1"), redeem(client, a, key="redeem-1")
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]
    assert wallet(client, a)["available_points"] == 150


def test_idempotency_key_reused_for_a_different_reward_conflicts(client, a):
    other = make_reward(client, a, 10)
    earn(client, a, 1000)
    assert redeem(client, a, key="k").status_code == 200
    assert redeem(client, a, reward_id=other, key="k").status_code == 409


# --------------------------------------- database-level guarantees (no app)

def test_database_itself_rejects_a_negative_balance(client, a):
    with pytest.raises(IntegrityError, match="ck_wallet_available_points_nonneg"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE customer_wallets SET available_points = -5 WHERE wallet_id=:w"),
                         {"w": a.wallet_id})


def test_ledger_rejects_update_and_delete_at_database_level(client, a):
    txn_id = earn(client, a, 600).json()["transaction_id"]
    for sql in ("UPDATE loyalty_transactions SET points = 999999 WHERE transaction_id=:t",
                "DELETE FROM loyalty_transactions WHERE transaction_id=:t"):
        with pytest.raises(DBAPIError, match="insert-only audit ledger"):
            with engine.begin() as conn:
                conn.execute(text(sql), {"t": txn_id})
    row = ledger(client, a)[0]
    assert (row["transaction_id"], row["points"]) == (txn_id, 120)


# ---------------------------------------------------------------- concurrency

def _redeem_svc(org_id, wallet_id, reward_id):
    with session() as db:
        return services.redeem_reward(db, organization_id=org_id, wallet_id=wallet_id,
                                      reward_id=reward_id).transaction_id


def test_two_simultaneous_redeems_on_a_wallet_funded_for_one(client, a):
    r100 = make_reward(client, a, 100)
    earn(client, a, 500)  # exactly 100 pts
    res = run_concurrently(2, lambda i: _redeem_svc(a.org_id, a.wallet_id, r100))
    ok = [r for r in res if isinstance(r, str)]
    rejected = [r for r in res if isinstance(r, services.InsufficientPointsError)]
    assert len(ok) == 1 and len(rejected) == 1, res
    assert wallet(client, a)["available_points"] == 0
    assert [t["type"] for t in ledger(client, a)].count("REDEEM") == 1


def test_ten_concurrent_redeems_succeed_exactly_as_often_as_funds_allow(client, a):
    r100 = make_reward(client, a, 100)
    for _ in range(3):
        earn(client, a, 500)  # 3 x 100 = 300 pts
    res = run_concurrently(10, lambda i: _redeem_svc(a.org_id, a.wallet_id, r100))
    assert sum(isinstance(r, str) for r in res) == 3, res
    assert sum(isinstance(r, services.InsufficientPointsError) for r in res) == 7, res
    assert wallet(client, a)["available_points"] == 0


def test_last_unit_of_stock_goes_to_exactly_one_of_two_wallets(client, a):
    rid = make_reward(client, a, 100, stock=1)
    w2 = new_wallet(client, a, "second-customer")
    earn(client, a, 500)
    earn(client, a, 500, wallet_id=w2)
    wallets = [a.wallet_id, w2]
    res = run_concurrently(2, lambda i: _redeem_svc(a.org_id, wallets[i], rid))
    assert sum(isinstance(r, str) for r in res) == 1, res
    assert sum(isinstance(r, services.ConflictError) for r in res) == 1, res
    stock = [x for x in client.get("/api/v1/loyalty/rewards", headers=a.viewer).json() if x["reward_id"] == rid][0]
    assert stock["stock_remaining"] == 0
