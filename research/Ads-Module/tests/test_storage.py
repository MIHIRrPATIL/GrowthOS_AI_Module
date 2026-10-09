"""
Unit Tests for Ads Module SQL Storage Adapter
Validates account connections, daily metric upserts, and date window queries.
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import datetime, timezone

from domain.models import AccountConnection, AccountStatus, AdsCampaignDaily
from storage.ads_storage import SqlAdsStorageAdapter


@pytest.fixture
def storage():
    # In-memory database for isolation
    return SqlAdsStorageAdapter(db_path=":memory:")


def test_storage_account_connection_lifecycle(storage):
    conn = AccountConnection(
        workspace_id="ws_dominos",
        account_id="1234567890",
        account_name="Domino's Main Account",
        currency="INR",
        timezone="Asia/Kolkata",
        login_customer_id="9876543210"
    )

    storage.save_account_connection(conn)

    retrieved = storage.get_account_connection(workspace_id="ws_dominos", account_id="1234567890")
    assert retrieved is not None
    assert retrieved.workspace_id == "ws_dominos"
    assert retrieved.account_id == "1234567890"
    assert retrieved.status == AccountStatus.ACTIVE
    assert retrieved.currency == "INR"

    # Update status
    conn.status = AccountStatus.AUTHENTICATION_FAILED
    storage.save_account_connection(conn)

    updated = storage.get_account_connection(workspace_id="ws_dominos", account_id="1234567890")
    assert updated.status == AccountStatus.AUTHENTICATION_FAILED

    # List connections
    connections = storage.list_account_connections(workspace_id="ws_dominos")
    assert len(connections) == 1


def test_storage_upsert_daily_metrics_and_queries(storage):
    rec1 = AdsCampaignDaily(
        workspace_id="ws_dominos",
        platform="google_ads",
        account_id="acc_1",
        campaign_id="camp_101",
        campaign_name="Weekend Search",
        date="2026-10-06",
        spend_paise=100000,
        spend_inr=1000.0,
        impressions=5000,
        clicks=250,
        conversions=25.0,
        conversion_value_paise=500000,
        ctr=0.05,
        cpc_paise=400,
        cpa_paise=4000,
        roas=5.0
    )

    rec2 = AdsCampaignDaily(
        workspace_id="ws_dominos",
        platform="google_ads",
        account_id="acc_1",
        campaign_id="camp_101",
        campaign_name="Weekend Search",
        date="2026-10-07",
        spend_paise=120000,
        spend_inr=1200.0,
        impressions=6000,
        clicks=300,
        conversions=30.0,
        conversion_value_paise=600000,
        ctr=0.05,
        cpc_paise=400,
        cpa_paise=4000,
        roas=5.0
    )

    # Insert batch
    count = storage.upsert_daily_metrics([rec1, rec2])
    assert count == 2

    # Query by campaign date window
    results = storage.get_campaign_daily_metrics("camp_101", "2026-10-06", "2026-10-07")
    assert len(results) == 2
    assert results[0].date == "2026-10-06"
    assert results[1].date == "2026-10-07"

    # Idempotent upsert with revised spend (e.g. Google late conversion adjustment)
    rec1_updated = AdsCampaignDaily(
        workspace_id="ws_dominos",
        platform="google_ads",
        account_id="acc_1",
        campaign_id="camp_101",
        campaign_name="Weekend Search",
        date="2026-10-06",
        spend_paise=105000,  # Revised
        spend_inr=1050.0,
        impressions=5100,
        clicks=260,
        conversions=28.0,
        conversion_value_paise=560000,
        ctr=0.051,
        cpc_paise=403,
        cpa_paise=3750,
        roas=5.33
    )

    storage.upsert_daily_metrics([rec1_updated])

    # Re-query: row should be updated, not duplicated
    results_after = storage.get_campaign_daily_metrics("camp_101", "2026-10-06", "2026-10-07")
    assert len(results_after) == 2
    assert results_after[0].spend_paise == 105000
    assert results_after[0].conversions == 28.0


def test_storage_bulk_metrics_tenant_isolation(storage):
    r_dominos = AdsCampaignDaily(
        workspace_id="ws_dominos",
        platform="google_ads",
        account_id="acc_dominos",
        campaign_id="camp_d",
        campaign_name="Pizza",
        date="2026-10-08",
        spend_paise=50000,
        spend_inr=500.0
    )

    r_other = AdsCampaignDaily(
        workspace_id="ws_other_tenant",
        platform="google_ads",
        account_id="acc_other",
        campaign_id="camp_o",
        campaign_name="Burger",
        date="2026-10-08",
        spend_paise=80000,
        spend_inr=800.0
    )

    storage.upsert_daily_metrics([r_dominos, r_other])

    bulk_dominos = storage.get_bulk_metrics("ws_dominos", "2026-10-01", "2026-10-09")
    assert len(bulk_dominos) == 1
    assert bulk_dominos[0].campaign_id == "camp_d"

    bulk_other = storage.get_bulk_metrics("ws_other_tenant", "2026-10-01", "2026-10-09")
    assert len(bulk_other) == 1
    assert bulk_other[0].campaign_id == "camp_o"
