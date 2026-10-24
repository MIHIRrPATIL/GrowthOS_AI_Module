"""Referrals: server-side bonus, natural idempotency, abuse guards."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models, services
from conftest import ledger, make_program, new_wallet, run_concurrently, session, wallet


def create_ref(client, t, referee="friend-1", wallet_id=None, program_id=None, headers=None):
    return client.post("/api/v1/loyalty/referrals", headers=headers or t.operator, json={
        "program_id": program_id or t.program_id, "referrer_wallet_id": wallet_id or t.wallet_id,
        "referee_customer_id": referee})


def complete(client, t, referral_id, key=None, **extra):
    body = {"referral_id": referral_id, **extra}
    if key:
        body["idempotency_key"] = key
    return client.post("/api/v1/loyalty/referrals/complete", headers=t.operator, json=body)


def test_completion_awards_the_programs_configured_bonus(client, a):
    ref = create_ref(client, a).json()
    assert ref["status"] == "PENDING"
    r = complete(client, a, ref["referral_id"])
    assert r.status_code == 200, r.text
    assert (r.json()["type"], r.json()["points"]) == ("BONUS", 500)
    assert r.json()["referral_id"] == ref["referral_id"]
    w = wallet(client, a)
    assert (w["available_points"], w["lifetime_points"]) == (500, 500)


def test_client_cannot_choose_the_bonus(client, a):
    """Regression: rev-1 accepted bonus_points from the client (1,000,000 was awarded)."""
    ref = create_ref(client, a).json()
    r = complete(client, a, ref["referral_id"], bonus_points=1_000_000, points=1_000_000)
    assert r.status_code == 200
    assert r.json()["points"] == 500
    assert wallet(client, a)["available_points"] == 500


def test_retry_with_same_key_replays_instead_of_failing(client, a):
    """Regression: rev-1 returned 409 for a same-key retry."""
    ref = create_ref(client, a).json()
    first = complete(client, a, ref["referral_id"], key="evt-1")
    retry = complete(client, a, ref["referral_id"], key="evt-1")
    assert retry.status_code == 200
    assert retry.json()["transaction_id"] == first.json()["transaction_id"]
    assert wallet(client, a)["available_points"] == 500


def test_retry_without_a_key_or_with_a_new_key_never_pays_twice(client, a):
    ref = create_ref(client, a).json()
    first = complete(client, a, ref["referral_id"]).json()
    for key in (None, "different-key"):
        r = complete(client, a, ref["referral_id"], key=key)
        assert r.status_code == 200 and r.json()["transaction_id"] == first["transaction_id"]
    assert wallet(client, a)["available_points"] == 500
    assert [t["type"] for t in ledger(client, a)].count("BONUS") == 1


def test_simultaneous_completions_pay_once(client, a):
    ref = create_ref(client, a).json()

    def attempt(_):
        with session() as db:
            return services.complete_referral(
                db, organization_id=a.org_id, referral_id=ref["referral_id"]).transaction_id

    res = run_concurrently(4, attempt)
    assert all(isinstance(r, str) for r in res), res
    assert len(set(res)) == 1
    assert wallet(client, a)["available_points"] == 500


def test_database_allows_only_one_bonus_per_referral(client, a):
    ref = create_ref(client, a).json()
    complete(client, a, ref["referral_id"])
    with pytest.raises(IntegrityError, match="uq_txn_single_referral_bonus"):
        with session() as db:
            db.add(models.LoyaltyTransaction(
                program_id=a.program_id, wallet_id=a.wallet_id, type=models.TxnType.BONUS,
                points=1, balance_after=1, referral_id=ref["referral_id"]))
            db.commit()


def test_program_without_a_bonus_configured_rejects_completion(client, a):
    pid = make_program(client, a)  # no referral_bonus_points
    w2 = new_wallet(client, a, "referrer-2", program_id=pid)
    ref = create_ref(client, a, wallet_id=w2, program_id=pid).json()
    r = complete(client, a, ref["referral_id"])
    assert r.status_code == 400 and "no referral bonus" in r.json()["detail"]
    with session() as db:
        status = db.execute(select(models.Referral.status).where(
            models.Referral.referral_id == ref["referral_id"])).scalar_one()
    assert status == models.ReferralStatus.PENDING


def test_self_referral_is_rejected(client, a):
    r = create_ref(client, a, referee=a.customer_id)
    assert r.status_code == 400 and "themselves" in r.json()["detail"]


def test_same_person_cannot_be_referred_twice_in_a_program(client, a):
    other = new_wallet(client, a, "second-referrer")
    assert create_ref(client, a, referee="friend-9").status_code == 201
    r = create_ref(client, a, referee="friend-9", wallet_id=other)
    assert r.status_code == 409


def test_simultaneous_duplicate_referrals_create_only_one(client, a):
    wallets = [a.wallet_id, new_wallet(client, a, "second-referrer")]

    def attempt(i):
        with session() as db:
            return services.create_referral(
                db, organization_id=a.org_id, program_id=a.program_id,
                referrer_wallet_id=wallets[i], referee_customer_id="friend-race").referral_id

    res = run_concurrently(2, attempt)
    assert sum(isinstance(r, str) for r in res) == 1, res
    assert sum(isinstance(r, services.ConflictError) for r in res) == 1, res


def test_unknown_referral_is_404(client, a):
    assert complete(client, a, "ref_nope").status_code == 404
