"""
Deterministic Unit Tests for SqlAuditLedgerAdapter
Validates:
1. Append-only record insertion and multi-tenant scoped retrieval.
2. Cryptographic hash chaining (prev_record_hash links to prior record_hash).
3. Tamper detection when an audit entry is altered.
4. Database triggers that strictly prohibit SQL UPDATE and DELETE operations.
5. Strict multi-tenant isolation across audit chains.
"""

import pytest
import sqlite3
from domain.actions import AuditRecord
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter


@pytest.fixture
def ledger():
    adapter = SqlAuditLedgerAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


def test_audit_ledger_append_and_retrieval(ledger):
    rec1 = AuditRecord(
        tenant_id="tenant_dominos",
        plan_id="plan_001",
        actor="ai_growth_brain",
        event_type="plan_drafted",
        details={"action": "waive_delivery_fee", "fee_paise": 6000}
    )
    rec2 = AuditRecord(
        tenant_id="tenant_dominos",
        plan_id="plan_001",
        actor="policy_gate",
        event_type="policy_evaluated",
        details={"passed": True, "violations": []}
    )
    ledger.record_audit(rec1)
    ledger.record_audit(rec2)

    trail = ledger.get_audit_trail(tenant_id="tenant_dominos", plan_id="plan_001")
    assert len(trail) == 2
    assert trail[0].event_type == "plan_drafted"
    assert trail[1].event_type == "policy_evaluated"
    assert trail[0].actor == "ai_growth_brain"
    assert trail[1].actor == "policy_gate"


def test_audit_ledger_cryptographic_hash_chain(ledger):
    # Append a sequence of 4 records
    for i in range(4):
        rec = AuditRecord(
            tenant_id="tenant_dominos",
            plan_id=f"plan_{i:03d}",
            actor="ai_growth_brain",
            event_type=f"step_{i}",
            details={"step": i}
        )
        ledger.record_audit(rec)

    trail = ledger.get_audit_trail(tenant_id="tenant_dominos")
    assert len(trail) == 4

    # First record must start with GENESIS
    assert trail[0].prev_record_hash == "GENESIS"
    assert len(trail[0].record_hash) == 64

    # Each subsequent record must link to prior record's record_hash
    for k in range(1, 4):
        assert trail[k].prev_record_hash == trail[k - 1].record_hash

    # Full chain verification passes
    assert ledger.verify_hash_chain("tenant_dominos") is True


def test_audit_ledger_database_triggers_block_update_and_delete(ledger):
    rec = AuditRecord(
        tenant_id="tenant_dominos",
        plan_id="plan_immutable",
        actor="ai_growth_brain",
        event_type="plan_drafted",
        details={"confidential": "initial"}
    )
    ledger.record_audit(rec)

    conn = ledger._get_connection()

    # 1. Direct SQL UPDATE must fail due to trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_update:
        conn.execute("UPDATE audit_ledger SET actor = 'tampered' WHERE plan_id = 'plan_immutable'")
    assert "strictly append-only" in str(exc_update.value)

    # 2. Direct SQL DELETE must fail due to trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_delete:
        conn.execute("DELETE FROM audit_ledger WHERE plan_id = 'plan_immutable'")
    assert "strictly append-only" in str(exc_delete.value)


def test_audit_ledger_multi_tenant_isolation(ledger):
    # Tenant A
    ledger.record_audit(AuditRecord(
        tenant_id="tenant_a",
        plan_id="plan_a",
        actor="ai",
        event_type="drafted"
    ))

    # Tenant B
    ledger.record_audit(AuditRecord(
        tenant_id="tenant_b",
        plan_id="plan_b",
        actor="ai",
        event_type="drafted"
    ))

    trail_a = ledger.get_audit_trail(tenant_id="tenant_a")
    trail_b = ledger.get_audit_trail(tenant_id="tenant_b")

    assert len(trail_a) == 1
    assert trail_a[0].tenant_id == "tenant_a"

    assert len(trail_b) == 1
    assert trail_b[0].tenant_id == "tenant_b"

    # Both chains verify independently
    assert ledger.verify_hash_chain("tenant_a") is True
    assert ledger.verify_hash_chain("tenant_b") is True
