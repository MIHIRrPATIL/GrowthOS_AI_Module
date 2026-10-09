"""
Unit and Integration Tests for Phase 4:
Closed-Loop Attribution, Click Tracking, Conversion Matching, and Offline Uploads.
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from domain.attribution import (
    ClickRecord,
    ConversionRecord,
    IngestClickRequest,
    IngestConversionRequest
)
from attribution.click_tracker import ClickTracker
from attribution.conversion_matcher import ConversionMatcher
from connectors.offline_conversion_uploader import OfflineConversionUploader
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.playback_client import PlaybackAdsConnector
from api.main import create_app
from config import AdsModuleConfig


@pytest.fixture
def storage():
    return SqlAdsStorageAdapter(":memory:")


@pytest.fixture
def click_tracker(storage):
    return ClickTracker(storage=storage)


@pytest.fixture
def conversion_matcher(storage):
    return ConversionMatcher(storage=storage, lookback_days=30)


@pytest.fixture
def uploader(storage):
    return OfflineConversionUploader(storage=storage)


@pytest.fixture
def client(storage):
    config = AdsModuleConfig(
        db_url="sqlite:///:memory:",
        workspace_id="ws_dominos_attr_test"
    )
    connector = PlaybackAdsConnector()
    app = create_app(config=config, storage=storage, connector=connector)
    return TestClient(app)


# =============================================================================
# 1. Click Tracker Tests
# =============================================================================

def test_click_tracker_records_and_retrieves(click_tracker):
    req = IngestClickRequest(
        workspace_id="ws_test",
        gclid="EAIaIQobChMI_test_gclid_999",
        utm_source="google",
        utm_campaign="weekend_pizza_search",
        utm_medium="cpc",
        anonymous_id="anon_device_101",
        user_id="cust_9876",
        landing_page="/menu/pizza"
    )

    record = click_tracker.record_click(req)
    assert record.click_id.startswith("clk_")
    assert record.gclid == "EAIaIQobChMI_test_gclid_999"

    # Retrieve history
    history = click_tracker.get_visitor_history(
        workspace_id="ws_test",
        anonymous_id="anon_device_101",
        user_id="cust_9876"
    )
    assert len(history) == 1
    assert history[0].click_id == record.click_id


# =============================================================================
# 2. Conversion Matcher Tests
# =============================================================================

def test_conversion_matcher_attributes_direct_gclid(click_tracker, conversion_matcher):
    # 1. Visitor clicks ad with GCLID
    click_tracker.record_click(
        IngestClickRequest(
            workspace_id="ws_attr",
            gclid="gclid_direct_success",
            utm_source="google",
            utm_campaign="mumbai_delivery",
            anonymous_id="anon_visitor_1",
            clicked_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        )
    )

    # 2. Visitor converts (places order)
    conv_req = IngestConversionRequest(
        workspace_id="ws_attr",
        account_id="8023466278",
        order_id="order_1001",
        anonymous_id="anon_visitor_1",
        amount_inr=1500.0,
        currency="INR"
    )

    conv = conversion_matcher.match_and_record_conversion(conv_req)

    assert conv.order_id == "order_1001"
    assert conv.attribution_type == "DIRECT_GCLID"
    assert conv.matched_gclid == "gclid_direct_success"
    assert conv.amount_paise == 150000
    assert conv.uploaded_to_google is False


def test_conversion_matcher_attributes_last_touch_utm(click_tracker, conversion_matcher):
    # 1. Visitor clicks ad without GCLID but with UTM parameters
    click_tracker.record_click(
        IngestClickRequest(
            workspace_id="ws_attr",
            gclid=None,
            utm_source="google",
            utm_campaign="brand_terms",
            utm_medium="cpc",
            anonymous_id="anon_visitor_2",
            clicked_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        )
    )

    # 2. Visitor converts
    conv_req = IngestConversionRequest(
        workspace_id="ws_attr",
        account_id="8023466278",
        order_id="order_1002",
        anonymous_id="anon_visitor_2",
        amount_inr=850.0
    )

    conv = conversion_matcher.match_and_record_conversion(conv_req)
    assert conv.order_id == "order_1002"
    assert conv.attribution_type == "LAST_TOUCH_UTM"
    assert conv.matched_gclid is None
    assert conv.amount_paise == 85000


def test_conversion_matcher_handles_organic(conversion_matcher):
    # Visitor has zero tracked ad clicks
    conv_req = IngestConversionRequest(
        workspace_id="ws_attr",
        account_id="8023466278",
        order_id="order_1003",
        anonymous_id="anon_organic_visitor",
        amount_inr=500.0
    )

    conv = conversion_matcher.match_and_record_conversion(conv_req)
    assert conv.order_id == "order_1003"
    assert conv.attribution_type == "ORGANIC"
    assert conv.matched_gclid is None


# =============================================================================
# 3. Offline Conversion Uploader Tests
# =============================================================================

def test_offline_conversion_upload_flow(storage, click_tracker, conversion_matcher, uploader):
    # Create an attributed conversion with GCLID
    click_tracker.record_click(
        IngestClickRequest(
            workspace_id="ws_upload_test",
            gclid="gclid_ready_to_upload",
            anonymous_id="anon_up",
            clicked_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        )
    )

    conversion_matcher.match_and_record_conversion(
        IngestConversionRequest(
            workspace_id="ws_upload_test",
            account_id="8023466278",
            order_id="order_up_1",
            anonymous_id="anon_up",
            amount_inr=1200.0
        )
    )

    # Check pending
    pending = storage.get_pending_conversions("ws_upload_test")
    assert len(pending) == 1
    assert pending[0].order_id == "order_up_1"

    # Trigger upload
    upload_res = uploader.upload_pending_conversions("ws_upload_test")
    assert upload_res["uploaded_count"] == 1
    assert upload_res["failed_count"] == 0

    # Verify marked uploaded
    pending_after = storage.get_pending_conversions("ws_upload_test")
    assert len(pending_after) == 0

    updated_conv = storage.get_conversion(pending[0].conversion_id)
    assert updated_conv.uploaded_to_google is True
    assert updated_conv.uploaded_at is not None


# =============================================================================
# 4. Attribution Summary Aggregation Tests
# =============================================================================

def test_attribution_summary(storage, click_tracker, conversion_matcher):
    ws = "ws_summary_test"

    # Click 1 -> GCLID conversion of 2000 INR
    click_tracker.record_click(IngestClickRequest(workspace_id=ws, gclid="g1", anonymous_id="u1"))
    conversion_matcher.match_and_record_conversion(
        IngestConversionRequest(workspace_id=ws, account_id="8023466278", order_id="ord1", anonymous_id="u1", amount_inr=2000.0)
    )

    # Click 2 -> UTM conversion of 1000 INR
    click_tracker.record_click(IngestClickRequest(workspace_id=ws, utm_source="google", anonymous_id="u2"))
    conversion_matcher.match_and_record_conversion(
        IngestConversionRequest(workspace_id=ws, account_id="8023466278", order_id="ord2", anonymous_id="u2", amount_inr=1000.0)
    )

    # Organic conversion of 500 INR
    conversion_matcher.match_and_record_conversion(
        IngestConversionRequest(workspace_id=ws, account_id="8023466278", order_id="ord3", anonymous_id="u3", amount_inr=500.0)
    )

    summary = storage.get_attribution_summary(ws)
    assert summary["total_conversions"] == 3
    assert summary["direct_gclid_conversions"] == 1
    assert summary["utm_conversions"] == 1
    assert summary["organic_conversions"] == 1
    assert summary["total_attributed_revenue_inr"] == 3000.0
    assert summary["total_revenue_inr"] == 3500.0
    assert summary["pending_upload_count"] == 1


# =============================================================================
# 5. REST API Integration Tests
# =============================================================================

def test_api_attribution_end_to_end(client):
    ws = "ws_api_attr_test"

    # 1. Ingest Click
    click_res = client.post("/api/v1/ads/attribution/clicks", json={
        "workspace_id": ws,
        "gclid": "gclid_api_test_100",
        "utm_source": "google",
        "utm_campaign": "weekend_deals",
        "anonymous_id": "device_api_99",
        "landing_page": "/deals"
    })
    assert click_res.status_code == 200
    assert click_res.json()["gclid"] == "gclid_api_test_100"

    # 2. Ingest Conversion
    conv_res = client.post("/api/v1/ads/attribution/conversions", json={
        "workspace_id": ws,
        "account_id": "8023466278",
        "order_id": "order_api_99",
        "anonymous_id": "device_api_99",
        "amount_inr": 1800.0
    })
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert conv_data["attribution_type"] == "DIRECT_GCLID"
    assert conv_data["matched_gclid"] == "gclid_api_test_100"
    assert conv_data["amount_paise"] == 180000

    # 3. Get Summary
    summary_res = client.get(f"/api/v1/ads/attribution/summary?workspace_id={ws}")
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["direct_gclid_conversions"] == 1
    assert s_data["total_attributed_revenue_inr"] == 1800.0
    assert s_data["pending_upload_count"] == 1

    # 4. Trigger Upload
    up_res = client.post(f"/api/v1/ads/attribution/conversions/upload?workspace_id={ws}")
    assert up_res.status_code == 200
    assert up_res.json()["uploaded_count"] == 1

    # 5. Verify pending becomes 0
    summary_after = client.get(f"/api/v1/ads/attribution/summary?workspace_id={ws}").json()
    assert summary_after["pending_upload_count"] == 0
    assert summary_after["uploaded_conversions_count"] == 1
