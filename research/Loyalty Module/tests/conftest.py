"""
Test harness. Runs against a REAL PostgreSQL database (never SQLite/mocks):
the guarantees under test — CHECK constraints, the insert-only trigger,
partial unique indexes, SELECT ... FOR UPDATE locking — are Postgres features.

Point TEST_DATABASE_URL at a dedicated, disposable database. The schema is
DROPPED and recreated for the test session, so the harness refuses to run
unless the database name contains "test".
"""
import os
import threading
from dataclasses import dataclass

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://growthos:growthos_dev_pw@localhost:5432/growthos_loyalty_test",
)
_db_name = make_url(TEST_DB_URL).database or ""
if "test" not in _db_name.lower():
    pytest.exit(
        f"Refusing to run: database '{_db_name}' does not look like a test database "
        "(the test run DROPS all tables). Use a name containing 'test'.",
        returncode=2,
    )

# Must be set BEFORE the app is imported (config reads the environment once).
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["PLATFORM_ADMIN_KEY"] = "test-platform-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-test-jwt-secret-test-jwt-secret"
os.environ["JWT_TTL_SECONDS"] = "900"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from init_db import create_schema  # noqa: E402

PLATFORM = {"X-Platform-Key": "test-platform-key"}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    models.Base.metadata.drop_all(engine)
    create_schema(engine, verbose=False)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """TRUNCATE ... CASCADE is not blocked by the row-level ledger triggers."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE organizations CASCADE"))
    yield


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@dataclass
class Tenant:
    org_id: str
    admin: dict
    operator: dict
    viewer: dict
    admin_key: str
    program_id: str
    wallet_id: str
    customer_id: str
    reward_id: str          # costs 50 points, unlimited stock
    base_rule_id: str       # 10 pts / 100 spent
    promo_rule_id: str      # spend >= 500 -> double (20 pts / 100), priority 10


def _h(key: str) -> dict:
    return {"X-Api-Key": key}


def build_tenant(client: TestClient, name: str) -> Tenant:
    r = client.post("/api/v1/organizations", headers=PLATFORM, json={"name": name})
    assert r.status_code == 201, r.text
    org = r.json()
    admin = _h(org["api_key"])

    op = client.post("/api/v1/api-keys", headers=admin, json={"name": "op", "role": "OPERATOR"}).json()
    vw = client.post("/api/v1/api-keys", headers=admin, json={"name": "vw", "role": "VIEWER"}).json()

    prog = client.post(
        "/api/v1/loyalty/programs", headers=admin, json={"name": f"{name} program", "referral_bonus_points": 500}
    ).json()
    base = client.post(
        "/api/v1/loyalty/rules", headers=admin,
        json={"program_id": prog["program_id"], "name": "Base", "per_amount": "100", "points_per_unit": 10, "priority": 0},
    ).json()
    promo = client.post(
        "/api/v1/loyalty/rules", headers=admin,
        json={"program_id": prog["program_id"], "name": "Promo", "min_spend": "500", "per_amount": "100",
              "points_per_unit": 10, "multiplier": 2, "priority": 10},
    ).json()
    reward = client.post(
        "/api/v1/loyalty/rewards", headers=admin,
        json={"program_id": prog["program_id"], "name": "Coffee", "point_cost": 50},
    ).json()
    customer = f"cust-{name}"
    wallet = client.post(
        "/api/v1/customers/wallets", headers=_h(op["api_key"]),
        json={"program_id": prog["program_id"], "customer_id": customer},
    ).json()
    return Tenant(
        org_id=org["organization_id"], admin=admin, operator=_h(op["api_key"]), viewer=_h(vw["api_key"]),
        admin_key=org["api_key"], program_id=prog["program_id"], wallet_id=wallet["wallet_id"],
        customer_id=customer, reward_id=reward["reward_id"],
        base_rule_id=base["rule_id"], promo_rule_id=promo["rule_id"],
    )


@pytest.fixture
def a(client) -> Tenant:
    return build_tenant(client, "alpha")


@pytest.fixture
def b(client) -> Tenant:
    return build_tenant(client, "bravo")


# ---------- small helpers shared by tests ----------

def earn(client, t: Tenant, spend, key=None, wallet_id=None, **extra):
    body = {"wallet_id": wallet_id or t.wallet_id, "spend_amount": str(spend), **extra}
    if key:
        body["idempotency_key"] = key
    return client.post("/api/v1/loyalty/earn", headers=t.operator, json=body)


def redeem(client, t: Tenant, reward_id=None, key=None, wallet_id=None, **extra):
    body = {"wallet_id": wallet_id or t.wallet_id, "reward_id": reward_id or t.reward_id, **extra}
    if key:
        body["idempotency_key"] = key
    return client.post("/api/v1/loyalty/rewards/redeem", headers=t.operator, json=body)


def wallet(client, t: Tenant, wallet_id=None) -> dict:
    return client.get(f"/api/v1/customers/wallets/{wallet_id or t.wallet_id}", headers=t.viewer).json()


def ledger(client, t: Tenant, wallet_id=None) -> list:
    return client.get(f"/api/v1/customers/wallets/{wallet_id or t.wallet_id}/transactions", headers=t.viewer).json()


def new_wallet(client, t: Tenant, customer_id: str, program_id=None) -> str:
    r = client.post(
        "/api/v1/customers/wallets", headers=t.operator,
        json={"program_id": program_id or t.program_id, "customer_id": customer_id},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["wallet_id"]


def run_concurrently(n: int, fn):
    """Run fn(i) in n threads released simultaneously; returns results in order (exceptions captured)."""
    barrier = threading.Barrier(n)
    results = [None] * n

    def worker(i):
        barrier.wait()
        try:
            results[i] = fn(i)
        except Exception as exc:  # noqa: BLE001 - we assert on the exception type in tests
            results[i] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    return results


def session():
    return SessionLocal()


def make_reward(client, t: Tenant, cost: int, stock=None, active=True, program_id=None) -> str:
    r = client.post(
        "/api/v1/loyalty/rewards", headers=t.admin,
        json={"program_id": program_id or t.program_id, "name": f"R{cost}", "point_cost": cost,
              "stock_remaining": stock, "is_active": active},
    )
    assert r.status_code == 201, r.text
    return r.json()["reward_id"]


def make_program(client, t: Tenant, **extra) -> str:
    r = client.post("/api/v1/loyalty/programs", headers=t.admin, json={"name": "extra", **extra})
    assert r.status_code == 201, r.text
    return r.json()["program_id"]


def refund(client, t: Tenant, txn_id: str, headers=None):
    return client.post(f"/api/v1/loyalty/transactions/{txn_id}/refund", headers=headers or t.admin)
