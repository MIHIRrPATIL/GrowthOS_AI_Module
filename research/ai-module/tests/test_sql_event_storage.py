"""
Unit tests for SqlEventStorageAdapter.
Validates:
1. Exact deduplication on event_id.
2. Multi-tenant isolation.
3. UTC TimeWindow slicing and count accuracy.
4. JSON payload round-trip preservation.
"""

import pytest
from datetime import datetime, timezone, timedelta

from domain.events import EventEnvelope, PageMetadata, DeviceMetadata
from domain.metrics import TimeWindow
from adapters.sql_event_storage import SqlEventStorageAdapter


@pytest.fixture
def storage():
    adapter = SqlEventStorageAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


def test_store_and_deduplicate_single_event(storage):
    event = EventEnvelope(
        tenant_id="ws_dominos_in",
        event_name="product.viewed",
        customer_id="CUST-101",
        properties={"product_id": "PRD-01", "price": 450.0}
    )

    # First insert succeeds
    assert storage.store_event(event) is True

    # Immediate second insert with same event_id is deduplicated
    assert storage.store_event(event) is False

    # Fetch event and verify data integrity
    fetched = storage.get_event(tenant_id="ws_dominos_in", event_id=event.event_id)
    assert fetched is not None
    assert fetched.event_id == event.event_id
    assert fetched.tenant_id == "ws_dominos_in"
    assert fetched.properties["price"] == 450.0
    assert fetched.properties["product_id"] == "PRD-01"


def test_batch_store_and_deduplication(storage):
    base_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            event_id=f"evt_batch_{i}",
            event_name="page.viewed",
            occurred_at=(base_time + timedelta(minutes=i)).isoformat(),
            properties={"index": i}
        )
        for i in range(10)
    ]

    # Insert 10 events
    res1 = storage.store_batch(events)
    assert res1.total_received == 10
    assert res1.inserted_count == 10
    assert res1.deduplicated_count == 0

    # Insert batch with 5 existing events and 5 new events
    mixed = events[:5] + [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            event_id=f"evt_batch_new_{i}",
            event_name="page.viewed",
            occurred_at=(base_time + timedelta(hours=1, minutes=i)).isoformat(),
            properties={"index": i}
        )
        for i in range(5)
    ]

    res2 = storage.store_batch(mixed)
    assert res2.total_received == 10
    assert res2.inserted_count == 5
    assert res2.deduplicated_count == 5


def test_multi_tenant_isolation(storage):
    event_tenant_a = EventEnvelope(
        tenant_id="ws_dominos_in",
        event_id="evt_shared_001",
        event_name="purchase.completed",
        properties={"brand": "dominos"}
    )
    event_tenant_b = EventEnvelope(
        tenant_id="ws_starbucks_in",
        event_id="evt_shared_001",  # Same event_id across different tenants
        event_name="purchase.completed",
        properties={"brand": "starbucks"}
    )

    # Both can insert because tenant_id is part of the composite primary key
    assert storage.store_event(event_tenant_a) is True
    assert storage.store_event(event_tenant_b) is True

    # Scoped retrieval
    retrieved_a = storage.get_event("ws_dominos_in", "evt_shared_001")
    retrieved_b = storage.get_event("ws_starbucks_in", "evt_shared_001")

    assert retrieved_a is not None
    assert retrieved_a.properties["brand"] == "dominos"
    assert retrieved_b is not None
    assert retrieved_b.properties["brand"] == "starbucks"

    # Querying tenant A returns only tenant A's events
    t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t_end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events_a = storage.query_events("ws_dominos_in", window=window)
    events_b = storage.query_events("ws_starbucks_in", window=window)

    assert len(events_a) == 1
    assert events_a[0].tenant_id == "ws_dominos_in"
    assert len(events_b) == 1
    assert events_b[0].tenant_id == "ws_starbucks_in"


def test_window_slicing_and_counting(storage):
    t0 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 1, 14, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 1, 16, 0, 0, tzinfo=timezone.utc)

    # 1 before window, 2 inside window, 1 after window
    e_before = EventEnvelope(tenant_id="ws_dominos_in", occurred_at=t0.isoformat(), event_name="e0")
    e_in_1 = EventEnvelope(tenant_id="ws_dominos_in", occurred_at=t1.isoformat(), event_name="e1")
    e_in_2 = EventEnvelope(tenant_id="ws_dominos_in", occurred_at=(t1 + timedelta(hours=1)).isoformat(), event_name="e2")
    e_after = EventEnvelope(tenant_id="ws_dominos_in", occurred_at=t3.isoformat(), event_name="e3")

    storage.store_batch([e_before, e_in_1, e_in_2, e_after])

    window = TimeWindow(start=t1, end=t2)
    queried = storage.query_events("ws_dominos_in", window=window)
    count = storage.count_events("ws_dominos_in", window=window)

    assert len(queried) == 2
    assert count == 2
    assert {e.event_name for e in queried} == {"e1", "e2"}
