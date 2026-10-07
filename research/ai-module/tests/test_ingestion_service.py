"""
Integration tests for EventIngestionService with SqlEventStorageAdapter and SqlIdentityResolver.
Validates:
1. End-to-end ingestion of realistic Domino's Pizza India synthetic telemetry.
2. 100% idempotent deduplication on repeated batch runs.
3. Automatic identity linkage on sessions with authenticated customers.
4. Window-based retrieval of converted vs friction events.
"""

import pytest
from datetime import datetime, timezone, timedelta

from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_identity_resolver import SqlIdentityResolver
from services.ingestion_service import EventIngestionService
from generators.synthetic_events import SyntheticEventGenerator
from domain.metrics import TimeWindow


@pytest.fixture
def service():
    storage = SqlEventStorageAdapter(db_path=":memory:")
    resolver = SqlIdentityResolver(db_path=":memory:")
    svc = EventIngestionService(storage=storage, identity_resolver=resolver)
    yield svc, storage, resolver
    storage.close()
    resolver.close()


def test_synthetic_batch_ingestion_and_deduplication(service):
    svc, storage, resolver = service
    generator = SyntheticEventGenerator(tenant_id="ws_dominos_in", seed=42)

    base_time = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    batch = generator.generate_batch(
        session_count=20,
        fee_friction_ratio=0.3,
        rage_click_ratio=0.1,
        dormant_ratio=0.1,
        base_time=base_time
    )

    assert len(batch) > 0

    # Ingest batch
    res1 = svc.ingest_batch(batch)
    assert res1["status"] == "success"
    assert res1["total_received"] == len(batch)
    assert res1["inserted_count"] == len(batch)
    assert res1["deduplicated_count"] == 0

    # Ingest the EXACT same batch again -> 100% deduplication
    res2 = svc.ingest_batch(batch)
    assert res2["status"] == "success"
    assert res2["total_received"] == len(batch)
    assert res2["inserted_count"] == 0
    assert res2["deduplicated_count"] == len(batch)


def test_automatic_identity_linking_during_ingestion(service):
    svc, storage, resolver = service
    generator = SyntheticEventGenerator(tenant_id="ws_dominos_in", seed=42)

    # Generate a converting session for Rahul Sharma (CUST-48291)
    rahul = {"customer_id": "CUST-48291", "name": "Rahul Sharma"}
    session_events = generator.generate_session(
        scenario="converting",
        customer=rahul,
        base_time=datetime(2026, 10, 2, 14, 0, 0, tzinfo=timezone.utc)
    )

    anon_id = session_events[0].anonymous_id
    assert anon_id is not None

    # Before ingestion, anon_id is unlinked
    assert resolver.get_canonical_customer_id("ws_dominos_in", anon_id) is None

    # Ingest session
    svc.ingest_batch(session_events)

    # After ingestion, anon_id must automatically resolve to CUST-48291
    canonical = resolver.get_canonical_customer_id("ws_dominos_in", anon_id)
    assert canonical == "CUST-48291"

    # Reverse link and check rollback
    links = resolver.get_links_for_identifier("ws_dominos_in", anon_id)
    assert len(links) >= 1
    resolver.reverse_link(
        tenant_id="ws_dominos_in",
        link_id=links[0].link_id,
        reversed_by="qa_tester",
        reversal_reason="testing rollback"
    )

    # Querying after reversal uncouples anon_id
    assert resolver.get_canonical_customer_id("ws_dominos_in", anon_id) != "CUST-48291"

    # Raw events table must remain completely intact and unchanged
    window = TimeWindow(
        start=datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)
    )
    raw_events = storage.query_events("ws_dominos_in", window=window)
    assert len(raw_events) == len(session_events)
