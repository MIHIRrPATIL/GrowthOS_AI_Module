"""
Relational Identity Resolver Adapter (Hexagonal Architecture)
Implements IdentityResolutionPort using relational tables for reversible identity linkage.
Does NOT require a graph database; maintains full bidirectional traversal and clean rollbacks.
"""

from typing import List, Optional, Set
import sqlite3
import uuid
from datetime import datetime, timezone

from ports.identity import IdentityResolutionPort
from domain.identity import IdentityLink, IdentityType


class SqlIdentityResolver(IdentityResolutionPort):
    """
    Manages reversible identity links and canonical identity resolution.
    Raw event telemetry is never mutated; linkages are stored and traversed as relational records.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS identity_links (
            link_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            link_reason TEXT NOT NULL,
            confidence_score REAL NOT NULL DEFAULT 1.0,
            evidence_event_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            reversed_at TEXT,
            reversed_by TEXT,
            reversal_reason TEXT,
            PRIMARY KEY (tenant_id, link_id)
        );

        CREATE INDEX IF NOT EXISTS idx_links_tenant_source 
            ON identity_links (tenant_id, source_type, source_id, status);

        CREATE INDEX IF NOT EXISTS idx_links_tenant_target 
            ON identity_links (tenant_id, target_type, target_id, status);

        CREATE INDEX IF NOT EXISTS idx_links_tenant_evidence 
            ON identity_links (tenant_id, evidence_event_id);


        CREATE TABLE IF NOT EXISTS identity_nodes (
            tenant_id TEXT NOT NULL,
            identifier_type TEXT NOT NULL,
            identifier_value TEXT NOT NULL,
            canonical_customer_id TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            last_resolved_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (tenant_id, identifier_type, identifier_value)
        );

        CREATE INDEX IF NOT EXISTS idx_nodes_tenant_canonical 
            ON identity_nodes (tenant_id, canonical_customer_id);
        """)
        self._conn.commit()

    def _row_to_link(self, row: sqlite3.Row) -> IdentityLink:
        return IdentityLink.model_validate({
            "link_id": row["link_id"],
            "tenant_id": row["tenant_id"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "link_reason": row["link_reason"],
            "confidence_score": row["confidence_score"],
            "evidence_event_id": row["evidence_event_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "reversed_at": row["reversed_at"],
            "reversed_by": row["reversed_by"],
            "reversal_reason": row["reversal_reason"],
        })

    def link_identities(
        self,
        tenant_id: str,
        source_type: IdentityType,
        source_id: str,
        target_type: IdentityType,
        target_id: str,
        link_reason: str,
        evidence_event_id: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> IdentityLink:
        """
        Creates or returns an active reversible link.
        """
        cursor = self._conn.cursor()

        # Check if an active link already exists between these two
        cursor.execute(
            """
            SELECT * FROM identity_links 
            WHERE tenant_id = ? AND source_id = ? AND target_id = ? AND status = 'active'
            LIMIT 1;
            """,
            (tenant_id, source_id, target_id)
        )
        existing = cursor.fetchone()
        if existing:
            return self._row_to_link(existing)

        link_id = f"link_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._conn:
            # Insert edge
            cursor.execute(
                """
                INSERT INTO identity_links (
                    link_id, tenant_id, source_type, source_id, target_type, target_id,
                    link_reason, confidence_score, evidence_event_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?);
                """,
                (
                    link_id, tenant_id, source_type, source_id, target_type, target_id,
                    link_reason, confidence_score, evidence_event_id, now_iso
                )
            )

            # Update identity_nodes cache for source_id -> target_id
            cursor.execute(
                """
                INSERT INTO identity_nodes (
                    tenant_id, identifier_type, identifier_value, canonical_customer_id,
                    first_seen_at, last_seen_at, last_resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, identifier_type, identifier_value) DO UPDATE SET
                    canonical_customer_id = excluded.canonical_customer_id,
                    last_seen_at = excluded.last_seen_at,
                    last_resolved_at = excluded.last_resolved_at;
                """,
                (tenant_id, source_type, source_id, target_id, now_iso, now_iso, now_iso)
            )

            # Ensure canonical node exists for target_id
            cursor.execute(
                """
                INSERT INTO identity_nodes (
                    tenant_id, identifier_type, identifier_value, canonical_customer_id,
                    first_seen_at, last_seen_at, last_resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, identifier_type, identifier_value) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    last_resolved_at = excluded.last_resolved_at;
                """,
                (tenant_id, target_type, target_id, target_id, now_iso, now_iso, now_iso)
            )

        cursor.execute("SELECT * FROM identity_links WHERE tenant_id = ? AND link_id = ?", (tenant_id, link_id))
        return self._row_to_link(cursor.fetchone())

    def reverse_link(
        self,
        tenant_id: str,
        link_id: str,
        reversed_by: str,
        reversal_reason: str
    ) -> IdentityLink:
        """
        Reverses an active link. Restores source identity to independent status
        if no other active links exist.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM identity_links WHERE tenant_id = ? AND link_id = ? LIMIT 1;",
            (tenant_id, link_id)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Link not found: tenant={tenant_id}, link_id={link_id}")

        if row["status"] == "reversed":
            return self._row_to_link(row)

        source_id = row["source_id"]
        source_type = row["source_type"]
        reversed_at_iso = datetime.now(timezone.utc).isoformat()

        with self._conn:
            # Mark link reversed
            cursor.execute(
                """
                UPDATE identity_links 
                SET status = 'reversed', reversed_at = ?, reversed_by = ?, reversal_reason = ?
                WHERE tenant_id = ? AND link_id = ?;
                """,
                (reversed_at_iso, reversed_by, reversal_reason, tenant_id, link_id)
            )

            # Check if source_id still has other active links
            cursor.execute(
                """
                SELECT target_id FROM identity_links 
                WHERE tenant_id = ? AND source_id = ? AND status = 'active'
                ORDER BY created_at DESC LIMIT 1;
                """,
                (tenant_id, source_id)
            )
            fallback = cursor.fetchone()

            if fallback:
                new_canonical = fallback["target_id"]
            else:
                # No active links remain: uncouple source_id
                new_canonical = source_id

            cursor.execute(
                """
                UPDATE identity_nodes
                SET canonical_customer_id = ?, last_resolved_at = ?
                WHERE tenant_id = ? AND identifier_value = ?;
                """,
                (new_canonical, reversed_at_iso, tenant_id, source_id)
            )

        cursor.execute("SELECT * FROM identity_links WHERE tenant_id = ? AND link_id = ?", (tenant_id, link_id))
        return self._row_to_link(cursor.fetchone())

    def get_canonical_customer_id(self, tenant_id: str, identifier: str) -> Optional[str]:
        """
        Resolves identifier to canonical customer_id via active links.
        """
        cursor = self._conn.cursor()

        # Check identity_nodes cache first
        cursor.execute(
            """
            SELECT canonical_customer_id FROM identity_nodes 
            WHERE tenant_id = ? AND identifier_value = ?
            LIMIT 1;
            """,
            (tenant_id, identifier)
        )
        node = cursor.fetchone()
        if node and node["canonical_customer_id"]:
            return node["canonical_customer_id"]

        # Traversal fallback directly from active links
        cursor.execute(
            """
            SELECT target_id FROM identity_links 
            WHERE tenant_id = ? AND source_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1;
            """,
            (tenant_id, identifier)
        )
        link = cursor.fetchone()
        if link:
            return link["target_id"]

        # If it's already a target in active links, it is canonical
        cursor.execute(
            """
            SELECT target_id FROM identity_links 
            WHERE tenant_id = ? AND target_id = ? AND status = 'active'
            LIMIT 1;
            """,
            (tenant_id, identifier)
        )
        as_target = cursor.fetchone()
        if as_target:
            return as_target["target_id"]

        return None

    def get_linked_identifiers(self, tenant_id: str, canonical_customer_id: str) -> Set[str]:
        """
        Returns all active alias identifiers connected to this customer_id.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT source_id FROM identity_links 
            WHERE tenant_id = ? AND target_id = ? AND status = 'active';
            """,
            (tenant_id, canonical_customer_id)
        )
        rows = cursor.fetchall()
        aliases = {row["source_id"] for row in rows}
        aliases.add(canonical_customer_id)
        return aliases

    def get_links_for_identifier(
        self,
        tenant_id: str,
        identifier: str,
        include_reversed: bool = False
    ) -> List[IdentityLink]:
        cursor = self._conn.cursor()
        if include_reversed:
            cursor.execute(
                """
                SELECT * FROM identity_links 
                WHERE tenant_id = ? AND (source_id = ? OR target_id = ?)
                ORDER BY created_at DESC;
                """,
                (tenant_id, identifier, identifier)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM identity_links 
                WHERE tenant_id = ? AND (source_id = ? OR target_id = ?) AND status = 'active'
                ORDER BY created_at DESC;
                """,
                (tenant_id, identifier, identifier)
            )
        rows = cursor.fetchall()
        return [self._row_to_link(row) for row in rows]

    def close(self) -> None:
        self._conn.close()
