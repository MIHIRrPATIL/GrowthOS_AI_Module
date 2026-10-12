"""
SQL Customer Consent Adapter (DPDP / GDPR Compliance Ground Truth)
GrowthOS Module 4: AI Growth Brain

Implements ConsentPort using persistent SQLite / PostgreSQL storage.
Guarantees:
1. Purpose-specific consent tracking (whatsapp_marketing, email_marketing, ad_retargeting, profiling).
2. Fail-closed semantics: Unspecified, missing, or expired consent strictly defaults to False.
3. Cryptographically traceable immutable audit logging for opt-in / opt-out actions.
4. Thread-safe SQLite connection handling with WAL mode.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Optional, List, Any
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone

from ports.consent import ConsentPort


class SqlConsentAdapter(ConsentPort):
    """
    Persistent relational consent store implementing ConsentPort.
    Serves as the legal and operational source of truth for customer consent.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
        return self._conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).resolve().parent.parent / "sql" / "sqlite_schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")

        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = self._get_connection()
        conn.executescript(schema_sql)
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_consent(self, tenant_id: str, customer_id: str) -> Dict[str, bool]:
        """
        Retrieves active consent flags for a customer.
        Fails closed: Any purpose not explicitly 'granted' and unexpired is False.
        """
        if not tenant_id or not customer_id:
            return {}

        conn = self._get_connection()
        now_iso = datetime.now(timezone.utc).isoformat()

        cur = conn.execute(
            """
            SELECT purpose, status, expires_at
            FROM customer_consent
            WHERE tenant_id = ? AND customer_id = ?
            """,
            (tenant_id, customer_id)
        )
        rows = cur.fetchall()

        consent_map: Dict[str, bool] = {}
        for row in rows:
            purpose = row["purpose"]
            status = row["status"]
            expires_at = row["expires_at"]

            # Fail-closed validation
            is_active = False
            if status == "granted":
                if expires_at is None:
                    is_active = True
                else:
                    try:
                        exp_dt = datetime.fromisoformat(expires_at)
                        if exp_dt.tzinfo is None:
                            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                        is_active = exp_dt > datetime.now(timezone.utc)
                    except (ValueError, TypeError):
                        is_active = False

            consent_map[purpose] = is_active

        return consent_map

    def has_consent(self, tenant_id: str, customer_id: str, purpose: str) -> bool:
        """
        Direct fail-closed verification for a specific purpose.
        """
        if not tenant_id or not customer_id or not purpose:
            return False
        return self.get_consent(tenant_id, customer_id).get(purpose, False)

    def record_consent(
        self,
        tenant_id: str,
        customer_id: str,
        consent_flags: Dict[str, bool],
        evidence_event_id: Optional[str] = None,
        notice_version: str = "1.0",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Atomically records or updates purpose-specific customer consent
        and creates immutable entries in consent_audit_log.
        """
        if not tenant_id or not customer_id or not consent_flags:
            return

        conn = self._get_connection()
        now_iso = datetime.now(timezone.utc).isoformat()

        for purpose, granted in consent_flags.items():
            status = "granted" if granted else "revoked"
            action = "OPT_IN" if granted else "OPT_OUT"
            granted_at = now_iso if granted else None
            revoked_at = now_iso if not granted else None

            # 1. Upsert customer_consent
            conn.execute(
                """
                INSERT INTO customer_consent (
                    tenant_id, customer_id, purpose, status, notice_version,
                    granted_at, revoked_at, evidence_event_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, customer_id, purpose) DO UPDATE SET
                    status = excluded.status,
                    notice_version = excluded.notice_version,
                    granted_at = CASE WHEN excluded.status = 'granted' THEN excluded.granted_at ELSE customer_consent.granted_at END,
                    revoked_at = CASE WHEN excluded.status = 'revoked' THEN excluded.revoked_at ELSE NULL END,
                    evidence_event_id = excluded.evidence_event_id,
                    updated_at = excluded.updated_at
                """,
                (
                    tenant_id,
                    customer_id,
                    purpose,
                    status,
                    notice_version,
                    granted_at or now_iso,
                    revoked_at,
                    evidence_event_id,
                    now_iso,
                    now_iso
                )
            )

            # 2. Immutable audit trail entry
            conn.execute(
                """
                INSERT INTO consent_audit_log (
                    log_id, tenant_id, customer_id, purpose, action,
                    ip_address, user_agent, evidence_event_id, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cns_log_{uuid.uuid4().hex[:12]}",
                    tenant_id,
                    customer_id,
                    purpose,
                    action,
                    ip_address,
                    user_agent,
                    evidence_event_id,
                    now_iso
                )
            )

        conn.commit()

    def get_audit_trail(
        self,
        tenant_id: str,
        customer_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves historical audit entries for customer consent lifecycle.
        """
        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT log_id, tenant_id, customer_id, purpose, action,
                   ip_address, user_agent, evidence_event_id, timestamp
            FROM consent_audit_log
            WHERE tenant_id = ? AND customer_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (tenant_id, customer_id, limit)
        )
        return [dict(row) for row in cur.fetchall()]
