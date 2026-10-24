# GrowthOS — Loyalty & Rewards, Phase 1 Backend (revision 2)

A working REST API for the core rewards flow from the Module 1 spec
(programs → rules → wallets → earn/redeem → refunds → referrals).

Revision 2 fixes four correctness bugs found in revision 1, adds real
authentication with tenant isolation and RBAC, and adds an automated test
suite that runs against a real PostgreSQL.

Still out of scope (owned by other modules / later phases): Customer
Intelligence integration, AI natural-language rule config, browser extension,
checkout widget, tier/expiry automation, fraud-detection ML, Kafka/event bus.

## What changed in revision 2

### Bugs fixed

| # | Bug in revision 1 | Fix |
|---|---|---|
| 1 | `POST /referrals/complete` took `bonus_points` from the client (a request for 1,000,000 was honored) — violating "points are never client-supplied". | The bonus is `program.referral_bonus_points`, configured server-side. The request body no longer has the field; if a client still sends one it is ignored. |
| 2 | The same transaction could be refunded repeatedly (balance dropped 400 for a 200-pt earn when the wallet held other points). | Refund checks for a prior refund under the wallet row lock, **and** a partial unique index `uq_txn_single_refund` enforces it in Postgres. A refund can't itself be refunded. |
| 3 | Retrying referral completion with the same idempotency key returned 409. | Completion is now naturally idempotent: a retry (same key, new key, or none) returns the original BONUS transaction. A partial unique index `uq_txn_single_referral_bonus` guarantees one payout per referral. |
| 4 | Refunding a redemption never returned the reward to stock. | Stock is restored (reward row locked, same wallet→reward lock order as redeem). |
| 5 | *(found while fixing the above)* Refunding a redemption *increased* `lifetime_points`; refunding an earn left it unchanged. | `lifetime_points` now tracks earnings only: reversing an EARN/BONUS reduces it, reversing a REDEEM leaves it alone. |
| 6 | *(found while fixing the above)* An idempotency key could replay a *different* operation (an earn's key returned as a successful redeem). | A key only replays the same operation type, and the same spend / reward / referral. Otherwise → 409. |

Small hardening added alongside: self-referral is rejected; one person can't
be referred twice in a program (serialized with a Postgres advisory lock so
concurrent requests can't race past the check); cross-program reward IDs are
reported as "not found".

### Authentication, tenancy, RBAC

* Every request resolves to **(organization, role)** from the credential.
  The client never states its tenant; every query is scoped to it.
* Another tenant's resource is reported as **404** — identical to a missing
  one — so IDs can't be probed.
* **Credentials** (`app/auth.py`):
  * `X-Api-Key: <key>` — long-lived; only a SHA-256 digest is stored; shown once at creation.
  * `Authorization: Bearer <jwt>` — short-lived (default 15 min), minted by `POST /api/v1/auth/token`
    in exchange for an API key. The database row of the key stays authoritative for org + role,
    so revoking a key kills its tokens immediately, and token claims can't elevate privileges.
* **Roles:** `VIEWER` (read) < `OPERATOR` (+ wallets, earn, redeem, referrals) < `ADMIN`
  (+ programs, rules, rewards, refunds, API-key management).
* **Tenant creation** is a separate platform credential (`X-Platform-Key` =
  `PLATFORM_ADMIN_KEY`) and is disabled unless that variable is set.
  `POST /api/v1/organizations` returns the tenant plus its first ADMIN key.
* The last active ADMIN key of an org can't be revoked (no self-lockout).

| Endpoint | Min. role |
|---|---|
| `GET` programs / rules / rewards / wallets / transactions, `GET /auth/me` | VIEWER |
| `POST` wallets, earn, redeem, referrals, referrals/complete | OPERATOR |
| `POST` programs / rules / rewards, `POST …/refund`, `/api-keys` (create/list/revoke) | ADMIN |
| `POST /auth/token` | any valid API key |
| `POST /organizations` | platform key |

## Project layout

```
app/
  config.py     env-driven settings (JWT secret, platform key, CORS)
  auth.py       API-key + JWT authentication, RBAC dependencies, tenant resolution
  models.py     SQLAlchemy models — CHECK constraints, partial unique indexes, ApiKey
  schemas.py    Pydantic shapes (earn/redeem/referral completion never take points)
  services.py   All business logic; every mutation is one atomic, tenant-scoped DB transaction
  database.py   Engine/session
  main.py       FastAPI routes
migrations/
  002_insert_only_ledger.sql        trigger blocking UPDATE/DELETE on the ledger
  003_tenancy_and_integrity.sql     upgrades an existing revision-1 database (idempotent)
tests/          pytest suite (real PostgreSQL)
demo-frontend/index.html            single-file demo UI
init_db.py      creates tables + applies migrations (safe to re-run)
seed.py         demo tenant, program, wallet, rules, reward, and DEV-ONLY demo API keys
```

## Run it

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit: DATABASE_URL, JWT_SECRET, PLATFORM_ADMIN_KEY

python init_db.py           # tables + migrations
python seed.py              # DEV ONLY: demo tenant + publicly-known demo keys
uvicorn app.main:app --reload --port 8000
```

Demo UI: `cd demo-frontend && python3 -m http.server 5173`, open
`http://localhost:5173`. The key field is pre-filled with `demo-api-key` (ADMIN).
Try `demo-operator-key` (can't create programs) or `demo-viewer-key` (read-only)
to see RBAC in the UI. Interactive API docs: `http://localhost:8000/docs`.

> The seeded demo keys are public knowledge. Never run `seed.py` against a production database.

Creating a real tenant:

```bash
curl -X POST localhost:8000/api/v1/organizations \
  -H "X-Platform-Key: $PLATFORM_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"name": "Acme"}'          # response includes the tenant's ADMIN api_key (shown once)
```

### Upgrading an existing revision-1 database

`python init_db.py` is enough: `create_all` adds the new `api_keys` table and
`003_tenancy_and_integrity.sql` adds the new column and indexes. Then run
`python seed.py` to add the demo keys. **Your old requests that sent any API key
will now get 401** — use a real key.

If revision 1 already let some transaction be refunded twice, migration 003
**refuses to run** and names the transaction(s), because the ledger is
immutable and can't be silently repaired. For a dev database the simplest fix is
to drop and recreate it, then re-run `init_db.py` and `seed.py`.

## Tests

```bash
pip install -r requirements-dev.txt
# a throwaway Postgres database whose name contains "test" (the suite DROPs its tables):
createdb growthos_loyalty_test
export TEST_DATABASE_URL="postgresql+psycopg2://USER:PASS@localhost:5432/growthos_loyalty_test"
pytest
```

The suite refuses to run against a database whose name doesn't contain
`test`. It uses real PostgreSQL because the guarantees under test — CHECK
constraints, the insert-only trigger, partial unique indexes, `FOR UPDATE`
locking — are Postgres features that SQLite or mocks can't exercise.

What's covered (89 tests):

* **Earn** — rule priority, server-side points (spoofed fields ignored), caps, idempotency, inactive program.
* **Redeem** — server-side cost, insufficient funds, drain-to-zero, stock, inactive/foreign rewards.
* **DB guarantees without the app** — raw SQL negative balance rejected; raw UPDATE/DELETE on the ledger rejected;
  duplicate REFUND / BONUS rows rejected.
* **Concurrency (real threads, real locks)** — two simultaneous redeems on a wallet funded for one; ten on a wallet funded for three;
  last unit of stock across two wallets; two simultaneous refunds; four simultaneous referral completions; racing duplicate referrals.
* **Refunds** — reversal, immutability of the original row, single-refund, stock/lifetime correctness, can't reverse spent points.
* **Referrals** — server-side bonus, client bonus ignored, retries, no-bonus program, self/duplicate referral.
* **Auth** — 401 for missing/forged/unknown/revoked credentials; JWT expiry, wrong secret/issuer, `alg=none`,
  claim-elevation attempts, revocation of live tokens; keys stored hashed; platform-key gating; last-admin protection.
* **RBAC** — every endpoint's minimum role, checked for all three roles.
* **Tenant isolation** — lists, reads, earn/redeem/refund, rule/reward/wallet creation, referrals, API-key management,
  and a malicious `organization_id` in a request body.

## Remaining work (not in this revision)

* Events: outbox + publisher for `loyalty.*` events (Kafka later); `POST /loyalty/events`.
* Rule management: update/deactivate rules; birthday, first-purchase, weekday-multiplier and product rules.
* Spec endpoint shapes (`GET /customers/{id}/wallet`, `/customers/{id}/rewards`).
* Tiers, points expiry, fraud flagging, webhooks.
* Defense in depth for tenancy: Postgres row-level security keyed to the org, so a future query that forgets a filter still can't leak.
* Rate limiting and an audit log of auth events (the ledger already audits points movements).
* Pagination on list endpoints.
* Browser extension, checkout widget, AI features, Redis, monitoring.
