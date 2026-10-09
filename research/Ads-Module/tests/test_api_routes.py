"""
Unit Tests for Ads Module FastAPI Routes
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.playback_client import PlaybackAdsConnector
from config import AdsModuleConfig


@pytest.fixture
def client():
    config = AdsModuleConfig(
        db_url="sqlite:///:memory:",
        workspace_id="ws_dominos_test"
    )
    storage = SqlAdsStorageAdapter(":memory:")
    connector = PlaybackAdsConnector()

    app = create_app(config=config, storage=storage, connector=connector)
    return TestClient(app)


def test_health_check(client):
    res = client.get("/api/v1/ads/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "growthos-ads-module"


def test_account_connect_and_list(client):
    connect_payload = {
        "workspace_id": "ws_dominos_test",
        "account_id": "1234567890",
        "account_name": "Domino's Test Store",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "login_customer_id": "9876543210"
    }

    res = client.post("/api/v1/ads/accounts/connect", json=connect_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["workspace_id"] == "ws_dominos_test"
    assert data["account_id"] == "1234567890"
    assert data["status"] == "ACTIVE"

    # List accounts
    list_res = client.get("/api/v1/ads/accounts?workspace_id=ws_dominos_test")
    assert list_res.status_code == 200
    accounts = list_res.json()
    assert len(accounts) == 1
    assert accounts[0]["account_id"] == "1234567890"


def test_trigger_sync_and_query_metrics(client):
    # Connect account first
    client.post(
        "/api/v1/ads/accounts/connect",
        json={
            "workspace_id": "ws_dominos_test",
            "account_id": "1234567890",
            "account_name": "Domino's Test Store"
        }
    )

    # Trigger sync
    sync_res = client.post(
        "/api/v1/ads/accounts/1234567890/sync",
        json={
            "workspace_id": "ws_dominos_test",
            "start_date": "2026-10-06",
            "end_date": "2026-10-08",
            "lookback_days": 3
        }
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["success"] is True
    assert sync_data["records_synced"] > 0

    # Query metrics for campaign 10101
    camp_res = client.get("/api/v1/ads/campaigns/10101/metrics?start_date=2026-10-06&end_date=2026-10-08")
    assert camp_res.status_code == 200
    metrics = camp_res.json()
    assert len(metrics) > 0
    first = metrics[0]
    assert first["campaign_id"] == "10101"
    assert first["spend_paise"] > 0
    assert first["spend_inr"] > 0.0
    assert first["currency"] == "INR"

    # Query bulk metrics
    bulk_res = client.get("/api/v1/ads/campaigns/metrics/bulk?workspace_id=ws_dominos_test&start_date=2026-10-06&end_date=2026-10-08")
    assert bulk_res.status_code == 200
    bulk_data = bulk_res.json()
    assert len(bulk_data) == sync_data["records_synced"]
