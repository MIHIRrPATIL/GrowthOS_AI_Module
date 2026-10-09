"""
Unit Tests for Ads Sync Service
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import date, timedelta

from domain.models import AccountConnection, AccountStatus
from domain.events import MetricsUpdatedEvent
from connectors.playback_client import PlaybackAdsConnector
from normalization.normalizer import AdsNormalizer
from storage.ads_storage import SqlAdsStorageAdapter
from events.publisher import EventPublisher
from services.sync_service import AdsSyncService


@pytest.fixture
def sync_env():
    connector = PlaybackAdsConnector()
    normalizer = AdsNormalizer()
    storage = SqlAdsStorageAdapter(":memory:")
    publisher = EventPublisher()

    # Pre-register account connection
    conn = AccountConnection(
        workspace_id="ws_dominos",
        account_id="1234567890",
        account_name="Domino's Test Store"
    )
    storage.save_account_connection(conn)

    service = AdsSyncService(
        connector=connector,
        normalizer=normalizer,
        storage=storage,
        publisher=publisher
    )

    return {
        "service": service,
        "connector": connector,
        "storage": storage,
        "publisher": publisher,
        "workspace_id": "ws_dominos",
        "account_id": "1234567890"
    }


def test_sync_account_success_and_event_publishing(sync_env):
    service = sync_env["service"]
    storage = sync_env["storage"]
    publisher = sync_env["publisher"]
    workspace_id = sync_env["workspace_id"]
    account_id = sync_env["account_id"]

    events_captured = []
    publisher.subscribe(lambda evt: events_captured.append(evt))

    res = service.sync_account(
        workspace_id=workspace_id,
        account_id=account_id,
        start_date="2026-10-06",
        end_date="2026-10-08"
    )

    assert res.success is True
    assert res.records_synced > 0
    assert res.error_message is None

    # Check event received
    assert len(events_captured) == 1
    event = events_captured[0]
    assert isinstance(event, MetricsUpdatedEvent)
    assert event.workspace_id == workspace_id
    assert event.account_id == account_id
    assert event.record_count == res.records_synced

    # Check data persisted in storage
    records = storage.get_bulk_metrics(workspace_id, "2026-10-06", "2026-10-08")
    assert len(records) == res.records_synced


def test_sync_account_authentication_failure_handling(sync_env):
    service = sync_env["service"]
    connector = sync_env["connector"]
    storage = sync_env["storage"]
    workspace_id = sync_env["workspace_id"]
    account_id = sync_env["account_id"]

    connector.set_simulated_error("AUTHENTICATION_FAILED")

    res = service.sync_account(
        workspace_id=workspace_id,
        account_id=account_id,
        start_date="2026-10-06",
        end_date="2026-10-08"
    )

    assert res.success is False
    assert res.records_synced == 0
    assert "Authentication Failed" in res.error_message

    # Check that account connection was updated to AUTHENTICATION_FAILED
    conn = storage.get_account_connection(workspace_id, account_id)
    assert conn.status == AccountStatus.AUTHENTICATION_FAILED
