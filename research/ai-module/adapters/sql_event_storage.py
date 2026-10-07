"""
SQL Event Storage Adapter (Hexagonal Architecture)
Implements EventStoragePort supporting both SQLite (embedded / testing) and PostgreSQL.
Enforces multi-tenant isolation, idempotent deduplication, and window-based queries.
"""

from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime, timezone

from ports.storage import EventStoragePort
from domain.events import EventEnvelope
from domain.metrics import TimeWindow
from domain.identity import IngestionBatchResult


class SqlEventStorageAdapter(EventStoragePort):
    """
    Relational event storage adapter.
    Default uses SQLite (in-memory or file); can be initialized with any standard DB connection.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Initializes tables and indexes if they do not exist."""
        cursor = self._conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            tenant_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            schema_version TEXT NOT NULL DEFAULT '1.0.0',
            project_id TEXT NOT NULL,
            source_module TEXT NOT NULL,
            event_name TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            anonymous_id TEXT NOT NULL,
            customer_id TEXT,
            idempotency_key TEXT,
            page TEXT NOT NULL DEFAULT '{}',
            utm TEXT NOT NULL DEFAULT '{}',
            device TEXT NOT NULL DEFAULT '{}',
            network TEXT NOT NULL DEFAULT '{}',
            consent TEXT NOT NULL DEFAULT '{}',
            properties TEXT NOT NULL DEFAULT '{}',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (tenant_id, event_id)
        );

        CREATE INDEX IF NOT EXISTS idx_events_tenant_occurred 
            ON events (tenant_id, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_events_tenant_name_occurred 
            ON events (tenant_id, event_name, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_events_tenant_customer 
            ON events (tenant_id, customer_id, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_events_tenant_anonymous 
            ON events (tenant_id, anonymous_id, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_events_tenant_session 
            ON events (tenant_id, session_id, occurred_at);
        """)
        self._conn.commit()

    def _serialize_envelope(self, envelope: EventEnvelope) -> tuple:
        return (
            envelope.tenant_id,
            envelope.event_id,
            envelope.schema_version,
            envelope.project_id,
            envelope.source_module,
            envelope.event_name,
            envelope.occurred_at,
            envelope.received_at,
            envelope.session_id,
            envelope.anonymous_id,
            envelope.customer_id,
            envelope.idempotency_key,
            envelope.page.model_dump_json(),
            envelope.utm.model_dump_json(),
            envelope.device.model_dump_json(),
            envelope.network.model_dump_json(),
            envelope.consent.model_dump_json(),
            json.dumps(envelope.properties),
            json.dumps(envelope.metadata),
        )

    def _row_to_envelope(self, row: sqlite3.Row) -> EventEnvelope:
        return EventEnvelope.model_validate({
            "tenant_id": row["tenant_id"],
            "event_id": row["event_id"],
            "schema_version": row["schema_version"],
            "project_id": row["project_id"],
            "source_module": row["source_module"],
            "event_name": row["event_name"],
            "occurred_at": row["occurred_at"],
            "received_at": row["received_at"],
            "session_id": row["session_id"],
            "anonymous_id": row["anonymous_id"],
            "customer_id": row["customer_id"],
            "idempotency_key": row["idempotency_key"],
            "page": json.loads(row["page"]),
            "utm": json.loads(row["utm"]),
            "device": json.loads(row["device"]),
            "network": json.loads(row["network"]),
            "consent": json.loads(row["consent"]),
            "properties": json.loads(row["properties"]),
            "metadata": json.loads(row["metadata"]),
        })

    def store_event(self, envelope: EventEnvelope) -> bool:
        """
        Stores an event. Returns True if inserted, False if deduplicated.
        """
        sql = """
        INSERT OR IGNORE INTO events (
            tenant_id, event_id, schema_version, project_id, source_module,
            event_name, occurred_at, received_at, session_id, anonymous_id,
            customer_id, idempotency_key, page, utm, device, network,
            consent, properties, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        cursor = self._conn.cursor()
        cursor.execute(sql, self._serialize_envelope(envelope))
        self._conn.commit()
        return cursor.rowcount > 0

    def store_batch(self, events: List[EventEnvelope]) -> IngestionBatchResult:
        """
        Batch stores events using idempotent deduplication.
        """
        if not events:
            return IngestionBatchResult(
                tenant_id="",
                total_received=0,
                inserted_count=0,
                deduplicated_count=0,
                processed_at=datetime.now(timezone.utc)
            )

        tenant_id = events[0].tenant_id
        sql = """
        INSERT OR IGNORE INTO events (
            tenant_id, event_id, schema_version, project_id, source_module,
            event_name, occurred_at, received_at, session_id, anonymous_id,
            customer_id, idempotency_key, page, utm, device, network,
            consent, properties, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        cursor = self._conn.cursor()
        inserted_count = 0

        # Execute within an atomic transaction
        with self._conn:
            for event in events:
                # Ensure all events belong to declared tenant
                if event.tenant_id != tenant_id:
                    raise ValueError(f"Cross-tenant event detected in batch: expected {tenant_id}, got {event.tenant_id}")
                cursor.execute(sql, self._serialize_envelope(event))
                if cursor.rowcount > 0:
                    inserted_count += 1

        deduplicated_count = len(events) - inserted_count

        return IngestionBatchResult(
            tenant_id=tenant_id,
            total_received=len(events),
            inserted_count=inserted_count,
            deduplicated_count=deduplicated_count,
            processed_at=datetime.now(timezone.utc)
        )

    def get_event(self, tenant_id: str, event_id: str) -> Optional[EventEnvelope]:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE tenant_id = ? AND event_id = ? LIMIT 1;",
            (tenant_id, event_id)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_envelope(row)

    def query_events(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        event_names: Optional[List[str]] = None,
        customer_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        session_id: Optional[str] = None,
        exclude_test_traffic: bool = True,
        limit: int = 1000
    ) -> List[EventEnvelope]:
        start_iso = window.start.isoformat()
        end_iso = window.end.isoformat()

        query = [
            "SELECT * FROM events",
            "WHERE tenant_id = ?",
            "AND occurred_at >= ?",
            "AND occurred_at < ?"
        ]
        params: List[Any] = [tenant_id, start_iso, end_iso]

        if as_of:
            query.append("AND received_at <= ?")
            params.append(as_of.isoformat())

        if exclude_test_traffic:
            query.append("AND (json_extract(device, '$.device_type') != 'bot' OR json_extract(device, '$.device_type') IS NULL)")
            query.append("AND (json_extract(properties, '$.is_test') IS NULL OR json_extract(properties, '$.is_test') = 0 OR json_extract(properties, '$.is_test') = 'false')")
            query.append("AND (json_extract(metadata, '$.environment') != 'test' OR json_extract(metadata, '$.environment') IS NULL)")

        if event_names:
            placeholders = ",".join("?" for _ in event_names)
            query.append(f"AND event_name IN ({placeholders})")
            params.extend(event_names)

        if customer_id:
            query.append("AND customer_id = ?")
            params.append(customer_id)

        if anonymous_id:
            query.append("AND anonymous_id = ?")
            params.append(anonymous_id)

        if session_id:
            query.append("AND session_id = ?")
            params.append(session_id)

        query.append("ORDER BY occurred_at ASC")
        query.append("LIMIT ?;")
        params.append(limit)

        cursor = self._conn.cursor()
        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()
        return [self._row_to_envelope(row) for row in rows]

    def count_events(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        event_names: Optional[List[str]] = None,
        exclude_test_traffic: bool = True
    ) -> int:
        start_iso = window.start.isoformat()
        end_iso = window.end.isoformat()

        query = [
            "SELECT COUNT(*) as count FROM events",
            "WHERE tenant_id = ?",
            "AND occurred_at >= ?",
            "AND occurred_at < ?"
        ]
        params: List[Any] = [tenant_id, start_iso, end_iso]

        if as_of:
            query.append("AND received_at <= ?")
            params.append(as_of.isoformat())

        if exclude_test_traffic:
            query.append("AND (json_extract(device, '$.device_type') != 'bot' OR json_extract(device, '$.device_type') IS NULL)")
            query.append("AND (json_extract(properties, '$.is_test') IS NULL OR json_extract(properties, '$.is_test') = 0 OR json_extract(properties, '$.is_test') = 'false')")
            query.append("AND (json_extract(metadata, '$.environment') != 'test' OR json_extract(metadata, '$.environment') IS NULL)")

        if event_names:
            placeholders = ",".join("?" for _ in event_names)
            query.append(f"AND event_name IN ({placeholders})")
            params.extend(event_names)

        cursor = self._conn.cursor()
        cursor.execute(" ".join(query), params)
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_event_time_range(self, tenant_id: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Returns (min_occurred_at, max_occurred_at) for events stored for the tenant,
        or (None, None) if empty.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT MIN(occurred_at), MAX(occurred_at) FROM events WHERE tenant_id = ?;",
            (tenant_id,)
        )
        row = cursor.fetchone()
        if not row or not row[0] or not row[1]:
            return None, None
        return datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1])

    def close(self) -> None:
        self._conn.close()
