"""Tenant isolation: tenant B can never see or touch tenant A's data."""
from conftest import earn, ledger, redeem, refund, wallet
from test_referrals import complete, create_ref


def test_lists_only_contain_the_callers_own_data(client, a, b):
    earn(client, a, 600)
    earn(client, b, 400)
    for t, other in ((a, b), (b, a)):
        progs = client.get("/api/v1/loyalty/programs", headers=t.viewer).json()
        assert [p["program_id"] for p in progs] == [t.program_id]
        assert all(r["program_id"] == t.program_id for r in client.get("/api/v1/loyalty/rules", headers=t.viewer).json())
        assert all(r["program_id"] == t.program_id for r in client.get("/api/v1/loyalty/rewards", headers=t.viewer).json())
        txns = client.get("/api/v1/loyalty/transactions", headers=t.viewer).json()
        assert len(txns) == 1 and txns[0]["program_id"] == t.program_id
        assert client.get(f"/api/v1/loyalty/rules?program_id={other.program_id}", headers=t.viewer).json() == []
        assert client.get(f"/api/v1/loyalty/transactions?program_id={other.program_id}", headers=t.viewer).json() == []


def test_foreign_resources_look_exactly_like_missing_ones(client, a, b):
    assert client.get(f"/api/v1/loyalty/programs/{a.program_id}", headers=b.admin).status_code == 404
    assert client.get(f"/api/v1/customers/wallets/{a.wallet_id}", headers=b.admin).status_code == 404
    assert client.get(f"/api/v1/customers/wallets/{a.wallet_id}/transactions", headers=b.admin).status_code == 404
    missing = client.get("/api/v1/customers/wallets/wallet_nope", headers=b.admin)
    foreign = client.get(f"/api/v1/customers/wallets/{a.wallet_id}", headers=b.admin)
    assert missing.json()["detail"].split("'")[0] == foreign.json()["detail"].split("'")[0]


def test_cannot_create_children_under_another_tenants_program(client, a, b):
    assert client.post("/api/v1/loyalty/rules", headers=b.admin, json={
        "program_id": a.program_id, "name": "x", "points_per_unit": 1}).status_code == 404
    assert client.post("/api/v1/loyalty/rewards", headers=b.admin, json={
        "program_id": a.program_id, "name": "x", "point_cost": 1}).status_code == 404
    assert client.post("/api/v1/customers/wallets", headers=b.operator, json={
        "program_id": a.program_id, "customer_id": "intruder"}).status_code == 404


def test_cannot_earn_redeem_or_refund_against_another_tenants_wallet(client, a, b):
    txn = earn(client, a, 1000).json()  # A: 200 pts
    before = wallet(client, a)

    assert earn(client, b, 1000, wallet_id=a.wallet_id).status_code == 404
    assert redeem(client, b, wallet_id=a.wallet_id, reward_id=a.reward_id).status_code == 404
    assert refund(client, b, txn["transaction_id"]).status_code == 404

    assert wallet(client, a) == before
    assert len(ledger(client, a)) == 1


def test_cannot_redeem_another_tenants_reward_from_own_wallet(client, a, b):
    earn(client, b, 1000)
    r = redeem(client, b, reward_id=a.reward_id)
    assert r.status_code == 404
    assert wallet(client, b)["available_points"] == 200


def test_referrals_do_not_cross_tenants(client, a, b):
    ref = create_ref(client, a).json()
    assert create_ref(client, b, wallet_id=a.wallet_id, program_id=a.program_id).status_code == 404
    assert complete(client, b, ref["referral_id"]).status_code == 404
    assert wallet(client, a)["available_points"] == 0
    assert complete(client, a, ref["referral_id"]).status_code == 200  # still completable by its owner


def test_program_organization_comes_from_the_credential_not_the_body(client, a, b):
    """The old frontend sends organization_id; a malicious client could point it at someone else."""
    r = client.post("/api/v1/loyalty/programs", headers=b.admin,
                    json={"name": "sneaky", "organization_id": a.org_id})
    assert r.status_code == 201
    assert r.json()["organization_id"] == b.org_id
    assert r.json()["program_id"] not in [p["program_id"] for p in
                                          client.get("/api/v1/loyalty/programs", headers=a.admin).json()]


def test_same_customer_id_in_two_tenants_gets_independent_wallets(client, a, b):
    wa = client.post("/api/v1/customers/wallets", headers=a.operator,
                     json={"program_id": a.program_id, "customer_id": "shared"}).json()
    wb = client.post("/api/v1/customers/wallets", headers=b.operator,
                     json={"program_id": b.program_id, "customer_id": "shared"}).json()
    assert wa["wallet_id"] != wb["wallet_id"]
    earn(client, a, 1000, wallet_id=wa["wallet_id"])
    assert wallet(client, b, wb["wallet_id"])["available_points"] == 0


def test_api_key_management_is_tenant_scoped(client, a, b):
    a_key_id = client.get("/api/v1/auth/me", headers=a.admin).json()["key_id"]
    assert client.delete(f"/api/v1/api-keys/{a_key_id}", headers=b.admin).status_code == 404
    assert a_key_id not in [k["key_id"] for k in client.get("/api/v1/api-keys", headers=b.admin).json()]
    assert client.get("/api/v1/auth/me", headers=a.admin).status_code == 200
