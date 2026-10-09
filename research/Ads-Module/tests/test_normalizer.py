"""
Unit Tests for Ads Normalizer
Validates mathematical conversions, precision, and zero-division protection.
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from domain.models import RawGoogleAdsRow, AdsCampaignDaily
from normalization.normalizer import AdsNormalizer


def test_normalizer_micros_to_paise_and_inr():
    normalizer = AdsNormalizer(default_currency="INR", default_timezone="Asia/Kolkata")
    raw = RawGoogleAdsRow(
        campaign_id="10101",
        campaign_name="Domino's Weekend Pizza Delivery Search",
        campaign_status="ENABLED",
        date="2026-10-08",
        cost_micros=4500000000,  # 4,500 INR = 450,000 paise
        impressions=10000,
        clicks=500,
        conversions=50.0,
        conversions_value_micros=22500000000  # 22,500 INR = 2,250,000 paise
    )

    record = normalizer.normalize_row(raw, workspace_id="tenant_dominos", account_id="acc_123")

    assert record.workspace_id == "tenant_dominos"
    assert record.platform == "google_ads"
    assert record.campaign_id == "10101"
    assert record.date == "2026-10-08"

    # Monetary checks
    assert record.spend_paise == 450000  # 4500.00 INR * 100
    assert record.spend_inr == 4500.00
    assert record.conversion_value_paise == 2250000

    # Status check
    assert record.status == "ACTIVE"

    # Derived metrics
    assert record.ctr == 0.05  # 500 / 10000
    assert record.cpc_paise == 900  # 450000 / 500 = 900 paise = 9.00 INR
    assert record.cpa_paise == 9000  # 450000 / 50 = 9000 paise = 90.00 INR
    assert record.roas == 5.0  # 2250000 / 450000 = 5.0x


def test_normalizer_zero_division_safety():
    normalizer = AdsNormalizer()
    raw = RawGoogleAdsRow(
        campaign_id="10102",
        campaign_name="Zero Activity Campaign",
        campaign_status="PAUSED",
        date="2026-10-08",
        cost_micros=0,
        impressions=0,
        clicks=0,
        conversions=0.0,
        conversions_value_micros=0
    )

    record = normalizer.normalize_row(raw, workspace_id="tenant_dominos", account_id="acc_123")

    assert record.spend_paise == 0
    assert record.spend_inr == 0.0
    assert record.ctr == 0.0
    assert record.cpc_paise == 0
    assert record.cpa_paise == 0
    assert record.roas == 0.0
    assert record.status == "PAUSED"


def test_normalizer_status_mapping():
    normalizer = AdsNormalizer()

    def make_raw(status):
        return RawGoogleAdsRow(
            campaign_id="1",
            campaign_name="Test",
            campaign_status=status,
            date="2026-10-08"
        )

    assert normalizer.normalize_row(make_raw("ENABLED"), "w", "a").status == "ACTIVE"
    assert normalizer.normalize_row(make_raw("PAUSED"), "w", "a").status == "PAUSED"
    assert normalizer.normalize_row(make_raw("REMOVED"), "w", "a").status == "ARCHIVED"
    assert normalizer.normalize_row(make_raw("UNKNOWN"), "w", "a").status == "ACTIVE"


def test_normalizer_batch_transformation():
    normalizer = AdsNormalizer()
    rows = [
        RawGoogleAdsRow(campaign_id="1", campaign_name="A", campaign_status="ENABLED", date="2026-10-07", cost_micros=1000000),
        RawGoogleAdsRow(campaign_id="2", campaign_name="B", campaign_status="PAUSED", date="2026-10-08", cost_micros=2000000)
    ]
    batch = normalizer.normalize_batch(rows, workspace_id="tenant_dominos", account_id="acc_123")
    assert len(batch) == 2
    assert batch[0].campaign_id == "1"
    assert batch[0].spend_paise == 100
    assert batch[1].campaign_id == "2"
    assert batch[1].spend_paise == 200
