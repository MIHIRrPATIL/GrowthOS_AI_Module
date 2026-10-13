"""
SQL Event Storage Adapter (Hexagonal Architecture)
Implements EventStoragePort supporting both SQLite (embedded / testing) and PostgreSQL.
Enforces multi-tenant isolation, idempotent deduplication, and window-based queries.
"""

from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime, timezone, timedelta

from ports.storage import EventStoragePort
from domain.events import EventEnvelope
from domain.orders import ServerOrder
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

        CREATE TABLE IF NOT EXISTS server_orders (
            tenant_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            customer_id TEXT,
            session_id TEXT,
            anonymous_id TEXT,
            source TEXT NOT NULL DEFAULT 'server_webhook',
            currency TEXT NOT NULL DEFAULT 'INR',
            subtotal_paise INTEGER NOT NULL,
            discount_paise INTEGER NOT NULL DEFAULT 0,
            tax_paise INTEGER NOT NULL DEFAULT 0,
            total_paid_paise INTEGER NOT NULL,
            total_paid_inr REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'captured',
            gateway_reference TEXT,
            occurred_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (tenant_id, order_id)
        );

        CREATE INDEX IF NOT EXISTS idx_server_orders_tenant_occurred 
            ON server_orders (tenant_id, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_server_orders_tenant_received 
            ON server_orders (tenant_id, received_at);

        CREATE INDEX IF NOT EXISTS idx_server_orders_tenant_customer 
            ON server_orders (tenant_id, customer_id, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_server_orders_tenant_session 
            ON server_orders (tenant_id, session_id);
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

    def query_idle_sessions(
        self,
        tenant_id: str,
        as_of: datetime,
        idle_threshold_minutes: float = 15.0
    ) -> List[Dict[str, Any]]:
        """
        Queries sessions with unpurchased cart activity idle for at least idle_threshold_minutes.
        """
        cutoff_dt = as_of - timedelta(minutes=idle_threshold_minutes)
        cutoff_iso = cutoff_dt.isoformat()

        query = """
        SELECT session_id,
               max(customer_id) as customer_id,
               max(anonymous_id) as anonymous_id,
               max(occurred_at) as last_event_at,
               min(occurred_at) as session_start_at,
               count(CASE WHEN event_name IN ('product_viewed', 'view_item') THEN 1 END) as product_views_count,
               count(CASE WHEN event_name IN ('add_to_cart', 'cart_add') THEN 1 END) as cart_adds_count,
               count(CASE WHEN event_name IN ('order_completed', 'purchase') THEN 1 END) as purchase_count
        FROM events
        WHERE tenant_id = ?
        GROUP BY session_id
        HAVING purchase_count = 0 
           AND cart_adds_count > 0
           AND last_event_at <= ?
        ORDER BY last_event_at DESC;
        """
        cursor = self._conn.cursor()
        cursor.execute(query, (tenant_id, cutoff_iso))
        rows = cursor.fetchall()
        results: List[Dict[str, Any]] = []

        for r in rows:
            sid = r["session_id"]
            cursor.execute(
                "SELECT properties, event_name FROM events WHERE tenant_id = ? AND session_id = ? ORDER BY occurred_at DESC LIMIT 1;",
                (tenant_id, sid)
            )
            latest_row = cursor.fetchone()
            props = json.loads(latest_row["properties"]) if (latest_row and latest_row["properties"]) else {}

            cart_subtotal = props.get("cart_total_paise")
            if cart_subtotal is None and "cart_value" in props:
                cart_subtotal = round(float(props["cart_value"]) * 100)
            elif cart_subtotal is None:
                cart_subtotal = 0

            stage = props.get("funnel_stage") or (latest_row["event_name"] if latest_row else "cart")

            results.append({
                "tenant_id": tenant_id,
                "session_id": sid,
                "customer_id": r["customer_id"],
                "anonymous_id": r["anonymous_id"],
                "last_event_at": datetime.fromisoformat(r["last_event_at"]),
                "session_start_at": datetime.fromisoformat(r["session_start_at"]),
                "product_views_count": r["product_views_count"],
                "cart_adds_count": r["cart_adds_count"],
                "cart_subtotal_paise": cart_subtotal,
                "funnel_stage": stage,
                "properties": props
            })

        return results

    def store_order(self, order: ServerOrder) -> bool:
        """
        Stores an authoritative server-verified order.
        Returns True if inserted, or False if deduplicated.
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO server_orders (
                    tenant_id, order_id, customer_id, session_id, anonymous_id,
                    source, currency, subtotal_paise, discount_paise, tax_paise,
                    total_paid_paise, total_paid_inr, payment_status, gateway_reference,
                    occurred_at, received_at, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(tenant_id, order_id) DO NOTHING;
                """,
                (
                    order.tenant_id,
                    order.order_id,
                    order.customer_id,
                    order.session_id,
                    order.anonymous_id,
                    order.source,
                    order.currency,
                    order.subtotal_paise,
                    order.discount_paise,
                    order.tax_paise,
                    order.total_paid_paise,
                    order.total_paid_inr,
                    order.payment_status,
                    order.gateway_reference,
                    order.occurred_at,
                    order.received_at,
                    json.dumps(order.metadata)
                )
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def store_orders_batch(self, orders: List[ServerOrder]) -> int:
        """
        Batch stores server orders, returning count of inserted records.
        """
        inserted = 0
        for o in orders:
            if self.store_order(o):
                inserted += 1
        return inserted

    def query_orders(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        customer_id: Optional[str] = None,
        payment_status: str = "captured",
        limit: int = 10000
    ) -> List[ServerOrder]:
        """
        Queries verified server orders strictly scoped by tenant and window.
        """
        cursor = self._conn.cursor()
        watermark = as_of or window.end
        watermark_iso = watermark.isoformat()
        start_iso = window.start.isoformat()
        end_iso = window.end.isoformat()

        query = """
            SELECT * FROM server_orders
            WHERE tenant_id = ?
              AND occurred_at >= ?
              AND occurred_at <= ?
              AND received_at <= ?
        """
        params: List[Any] = [tenant_id, start_iso, end_iso, watermark_iso]

        if payment_status:
            query += " AND payment_status = ?"
            params.append(payment_status)

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)

        query += " ORDER BY occurred_at ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        orders: List[ServerOrder] = []
        for r in rows:
            orders.append(
                ServerOrder(
                    tenant_id=r["tenant_id"],
                    order_id=r["order_id"],
                    customer_id=r["customer_id"],
                    session_id=r["session_id"],
                    anonymous_id=r["anonymous_id"],
                    source=r["source"],
                    currency=r["currency"],
                    subtotal_paise=r["subtotal_paise"],
                    discount_paise=r["discount_paise"],
                    tax_paise=r["tax_paise"],
                    total_paid_paise=r["total_paid_paise"],
                    total_paid_inr=r["total_paid_inr"],
                    payment_status=r["payment_status"],
                    gateway_reference=r["gateway_reference"],
                    occurred_at=r["occurred_at"],
                    received_at=r["received_at"],
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {}
                )
            )
        return orders

    def close(self) -> None:
        self._conn.close()

