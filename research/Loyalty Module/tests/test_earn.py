"""Earn flow: rule engine, server-side points, idempotency."""
from sqlalchemy import text

from app.database import engine
from conftest import earn, ledger, make_program, new_wallet, redeem, wallet


def test_base_rule_awards_points_and_writes_ledger_row(client, a):
    r = earn(client, a, 400)  # below promo threshold -> base rule: 4 x 10
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["type"], body["points"], body["balance_after"]) == ("EARN", 40, 40)
    assert body["rule_id"] == a.base_rule_id
    w = wallet(client, a)
    assert (w["available_points"], w["lifetime_points"]) == (40, 40)
    assert [t["transaction_id"] for t in ledger(client, a)] == [body["transaction_id"]]


def test_highest_priority_matching_rule_wins(client, a):
    r = earn(client, a, 600)  # promo (min 500, x2) outranks base: 6 x 10 x 2
    assert r.json()["points"] == 120
    assert r.json()["rule_id"] == a.promo_rule_id


def test_client_cannot_supply_points(client, a):
    r = earn(client, a, 400, points=999999, point_amount=999999)  # spoofed fields
    assert r.status_code == 200
    assert r.json()["points"] == 40
    assert wallet(client, a)["available_points"] == 40


def test_max_points_per_txn_cap_is_applied(client, a):
    client.post("/api/v1/loyalty/rules", headers=a.admin, json={
        "program_id": a.program_id, "name": "Capped", "per_amount": "10",
        "points_per_unit": 10, "priority": 99, "max_points_per_txn": 25})
    assert earn(client, a, 100).json()["points"] == 25  # would be 100 uncapped


def test_idempotent_earn_replays_original_without_double_award(client, a):
    first = earn(client, a, 600, key="order-1")
    second = earn(client, a, 600, key="order-1")
    assert first.status_code == second.status_code == 200
    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    assert wallet(client, a)["available_points"] == 120
    assert len(ledger(client, a)) == 1


def test_idempotency_key_reused_with_different_spend_conflicts(client, a):
    assert earn(client, a, 600, key="order-1").status_code == 200
    r = earn(client, a, 700, key="order-1")
    assert r.status_code == 409
    assert wallet(client, a)["available_points"] == 120


def test_idempotency_key_cannot_replay_a_different_operation(client, a):
    assert earn(client, a, 1000, key="shared").status_code == 200  # +200
    r = redeem(client, a, key="shared")  # same key, different operation
    assert r.status_code == 409 and "different operation" in r.json()["detail"]
    assert wallet(client, a)["available_points"] == 200  # redemption did NOT happen


def test_no_matching_rule_is_rejected(client, a):
    pid = make_program(client, a)
    client.post("/api/v1/loyalty/rules", headers=a.admin, json={
        "program_id": pid, "name": "Big spenders", "min_spend": "1000", "points_per_unit": 10})
    w2 = new_wallet(client, a, "someone", program_id=pid)
    r = earn(client, a, 100, wallet_id=w2)
    assert r.status_code == 400 and "No active earn rule" in r.json()["detail"]


def test_spend_too_small_to_earn_is_rejected(client, a):
    r = earn(client, a, 50)  # floor(50/100) = 0 units
    assert r.status_code == 400 and "zero" in r.json()["detail"]
    assert ledger(client, a) == []


def test_non_positive_spend_is_rejected_by_validation(client, a):
    assert earn(client, a, 0).status_code == 422
    assert earn(client, a, -5).status_code == 422


def test_paused_program_cannot_earn(client, a):
    with engine.begin() as conn:
        conn.execute(text("UPDATE loyalty_programs SET status='PAUSED' WHERE program_id=:p"), {"p": a.program_id})
    r = earn(client, a, 600)
    assert r.status_code == 409 and "not active" in r.json()["detail"]


def test_unknown_wallet_is_404(client, a):
    assert earn(client, a, 600, wallet_id="wallet_nope").status_code == 404
