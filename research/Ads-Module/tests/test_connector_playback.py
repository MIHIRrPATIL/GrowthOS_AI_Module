"""
Unit Tests for Google Ads Playback Connector
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from connectors.playback_client import PlaybackAdsConnector
from connectors.google_ads_connector import GoogleAdsConnector


def test_playback_connector_loads_fixture():
    connector = PlaybackAdsConnector()
    health = connector.health_check()
    assert health["status"] == "healthy"
    assert health["mode"] == "playback"
    assert health["fixture_loaded"] is True

    # Query matching fixture dates
    rows = connector.fetch_campaign_metrics(
        account_id="acc_test",
        start_date="2026-10-06",
        end_date="2026-10-08"
    )
    assert len(rows) > 0
    first = rows[0]
    assert first.campaign_id in ("10101", "10102", "10103")
    assert first.cost_micros > 0
    assert first.date >= "2026-10-06"


def test_playback_connector_synthetic_fallback():
    connector = PlaybackAdsConnector()
    # Query date range far outside fixture
    rows = connector.fetch_campaign_metrics(
        account_id="acc_test",
        start_date="2025-01-01",
        end_date="2025-01-03"
    )
    assert len(rows) == 3
    assert rows[0].date == "2025-01-01"
    assert rows[2].date == "2025-01-03"


def test_playback_connector_simulated_errors():
    connector = PlaybackAdsConnector()

    connector.set_simulated_error("AUTHENTICATION_FAILED")
    with pytest.raises(PermissionError):
        connector.fetch_campaign_metrics("acc_test", "2026-10-06", "2026-10-08")

    connector.set_simulated_error("RATE_LIMIT_EXCEEDED")
    with pytest.raises(RuntimeError):
        connector.fetch_campaign_metrics("acc_test", "2026-10-06", "2026-10-08")

    connector.set_simulated_error(None)
    rows = connector.fetch_campaign_metrics("acc_test", "2026-10-06", "2026-10-08")
    assert len(rows) > 0


def test_google_ads_connector_delegates_to_playback_when_unconfigured():
    # When credentials are not live, connector falls back cleanly
    connector = GoogleAdsConnector()
    health = connector.health_check()
    assert health["status"] == "healthy"

    campaigns = connector.list_campaigns("acc_test")
    assert len(campaigns) >= 3
