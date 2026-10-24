"""Authentication, JWT exchange, key lifecycle, and RBAC."""
import time

import jwt
import pytest
from sqlalchemy import text

from app import config
from app.database import engine
from conftest import PLATFORM

BEARER = lambda tok: {"Authorization": f"Bearer {tok}"}  # noqa: E731


# ------------------------------------------------------------ authentication

def test_health_is_open(client):
    assert client.get("/health").status_code == 200


def test_missing_credentials_are_401(client, a):
    r = client.get("/api/v1/loyalty/programs")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("headers", [
    {"X-Api-Key": "anything"},                     # rev-1 accepted ANY non-empty string
    {"X-Api-Key": "gos_forged_key_value"},
    {"Authorization": "Basic dXNlcjpwYXNz"},
    {"Authorization": "Bearer not-a-jwt"},
])
def test_unknown_or_malformed_credentials_are_401(client, a, headers):
    assert client.get("/api/v1/loyalty/programs", headers=headers).status_code == 401


def test_api_keys_are_stored_hashed_never_in_plaintext(client, a):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT key_hash, key_prefix, name FROM api_keys")).all()
    assert rows
    for key_hash, prefix, _name in rows:
        assert len(key_hash) == 64 and key_hash != a.admin_key   # sha256 hex digest, not the key
        assert prefix.startswith("gos_") and len(prefix) == 8     # display-only prefix
    assert all(a.admin_key not in " ".join(map(str, r)) for r in rows)


def test_listing_keys_never_reveals_secrets(client, a):
    body = client.get("/api/v1/api-keys", headers=a.admin).text
    assert a.admin_key not in body and "key_hash" not in body and "api_key\"" not in body


# ----------------------------------------------------------------------- JWT

def test_exchange_api_key_for_bearer_token(client, a):
    r = client.post("/api/v1/auth/token", headers=a.admin)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer" and r.json()["expires_in"] == 900
    me = client.get("/api/v1/auth/me", headers=BEARER(r.json()["access_token"])).json()
    assert (me["organization_id"], me["role"], me["auth_method"]) == (a.org_id, "ADMIN", "jwt")


def test_token_endpoint_requires_an_api_key_not_a_token(client, a):
    tok = client.post("/api/v1/auth/token", headers=a.admin).json()["access_token"]
    assert client.post("/api/v1/auth/token", headers=BEARER(tok)).status_code == 401  # no endless refresh chain


def _forge(key_id, **override):
    now = int(time.time())
    claims = {"iss": config.JWT_ISSUER, "sub": key_id, "iat": now, "exp": now + 600, **override}
    return claims


def test_expired_forged_and_wrong_issuer_tokens_are_rejected(client, a):
    key_id = client.get("/api/v1/auth/me", headers=a.admin).json()["key_id"]
    now = int(time.time())
    bad = {
        "expired": jwt.encode(_forge(key_id, iat=now - 100, exp=now - 10), config.JWT_SECRET, algorithm="HS256"),
        "wrong secret": jwt.encode(_forge(key_id), "x" * 48, algorithm="HS256"),
        "wrong issuer": jwt.encode(_forge(key_id, iss="evil"), config.JWT_SECRET, algorithm="HS256"),
        "alg none": jwt.encode(_forge(key_id), None, algorithm="none"),
        "unknown key": jwt.encode(_forge("key_does_not_exist"), config.JWT_SECRET, algorithm="HS256"),
    }
    for name, tok in bad.items():
        assert client.get("/api/v1/auth/me", headers=BEARER(tok)).status_code == 401, name
    good = jwt.encode(_forge(key_id), config.JWT_SECRET, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=BEARER(good)).status_code == 200  # control


def test_token_claims_cannot_elevate_role_database_is_authoritative(client, a):
    viewer_id = client.get("/api/v1/auth/me", headers=a.viewer).json()["key_id"]
    tok = jwt.encode(_forge(viewer_id, role="ADMIN", org="org_other"), config.JWT_SECRET, algorithm="HS256")
    me = client.get("/api/v1/auth/me", headers=BEARER(tok)).json()
    assert (me["role"], me["organization_id"]) == ("VIEWER", a.org_id)


# ------------------------------------------------------------- key lifecycle

def test_revoking_a_key_kills_it_and_its_tokens_immediately(client, a):
    second = client.post("/api/v1/api-keys", headers=a.admin, json={"name": "ci", "role": "ADMIN"}).json()
    ci = {"X-Api-Key": second["api_key"]}
    tok = client.post("/api/v1/auth/token", headers=ci).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=BEARER(tok)).status_code == 200

    assert client.delete(f"/api/v1/api-keys/{second['key_id']}", headers=a.admin).status_code == 204
    assert client.get("/api/v1/auth/me", headers=ci).status_code == 401
    assert client.get("/api/v1/auth/me", headers=BEARER(tok)).status_code == 401


def test_cannot_revoke_the_last_active_admin_key(client, a):
    admin_id = client.get("/api/v1/auth/me", headers=a.admin).json()["key_id"]
    r = client.delete(f"/api/v1/api-keys/{admin_id}", headers=a.admin)
    assert r.status_code == 409
    assert client.get("/api/v1/auth/me", headers=a.admin).status_code == 200


# ------------------------------------------------------------ platform admin

def test_tenant_creation_requires_the_platform_key(client):
    assert client.post("/api/v1/organizations", json={"name": "x"}).status_code == 401
    assert client.post("/api/v1/organizations", headers={"X-Platform-Key": "wrong"}, json={"name": "x"}).status_code == 401


def test_a_tenant_admin_key_cannot_create_tenants(client, a):
    assert client.post("/api/v1/organizations", headers=a.admin, json={"name": "x"}).status_code == 401


def test_tenant_creation_is_disabled_when_no_platform_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(config, "PLATFORM_ADMIN_KEY", None)
    assert client.post("/api/v1/organizations", headers=PLATFORM, json={"name": "x"}).status_code == 403


def test_new_tenant_gets_a_working_admin_key(client):
    org = client.post("/api/v1/organizations", headers=PLATFORM, json={"name": "fresh"}).json()
    me = client.get("/api/v1/auth/me", headers={"X-Api-Key": org["api_key"]}).json()
    assert (me["organization_id"], me["role"]) == (org["organization_id"], "ADMIN")


# ------------------------------------------------------------------- RBAC

def _admin_only(t):
    return {
        "create_program": ("POST", "/api/v1/loyalty/programs", {"name": "p"}),
        "create_rule": ("POST", "/api/v1/loyalty/rules", {"program_id": t.program_id, "name": "r", "points_per_unit": 1}),
        "create_reward": ("POST", "/api/v1/loyalty/rewards", {"program_id": t.program_id, "name": "r", "point_cost": 5}),
        "refund": ("POST", "/api/v1/loyalty/transactions/txn_x/refund", None),
        "create_api_key": ("POST", "/api/v1/api-keys", {"name": "k"}),
        "list_api_keys": ("GET", "/api/v1/api-keys", None),
        "revoke_api_key": ("DELETE", "/api/v1/api-keys/key_x", None),
    }


def _operator_up(t):
    return {
        "create_wallet": ("POST", "/api/v1/customers/wallets", {"program_id": t.program_id, "customer_id": "c9"}),
        "earn": ("POST", "/api/v1/loyalty/earn", {"wallet_id": t.wallet_id, "spend_amount": "100"}),
        "redeem": ("POST", "/api/v1/loyalty/rewards/redeem", {"wallet_id": t.wallet_id, "reward_id": t.reward_id}),
        "create_referral": ("POST", "/api/v1/loyalty/referrals",
                            {"program_id": t.program_id, "referrer_wallet_id": t.wallet_id, "referee_customer_id": "z"}),
        "complete_referral": ("POST", "/api/v1/loyalty/referrals/complete", {"referral_id": "ref_x"}),
    }


class _Stub:  # only used to enumerate endpoint names for parametrization
    program_id = wallet_id = reward_id = ""


@pytest.mark.parametrize("name", list(_admin_only(_Stub)))
def test_admin_only_endpoints(client, a, name):
    method, path, body = _admin_only(a)[name]
    for who in (a.operator, a.viewer):
        assert client.request(method, path, headers=who, json=body).status_code == 403, f"{name} {who}"
    assert client.request(method, path, headers=a.admin, json=body).status_code not in (401, 403)


@pytest.mark.parametrize("name", list(_operator_up(_Stub)))
def test_operator_endpoints_reject_viewers_but_allow_operators_and_admins(client, a, name):
    method, path, body = _operator_up(a)[name]
    assert client.request(method, path, headers=a.viewer, json=body).status_code == 403
    for who in (a.operator, a.admin):
        assert client.request(method, path, headers=who, json=body).status_code not in (401, 403)


@pytest.mark.parametrize("path", [
    "/api/v1/loyalty/programs", "/api/v1/loyalty/rules", "/api/v1/loyalty/rewards",
    "/api/v1/loyalty/transactions", "/api/v1/auth/me",
])
def test_every_role_can_read(client, a, path):
    for who in (a.viewer, a.operator, a.admin):
        assert client.get(path, headers=who).status_code == 200
