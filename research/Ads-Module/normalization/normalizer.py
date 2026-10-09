"""
Normalization Layer for Google Ads Data
Converts Google GAQL rows (micros, status, timezones) into GrowthOS 12-field schema.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Optional
from datetime import datetime, timezone
import math

from domain.models import RawGoogleAdsRow, AdsCampaignDaily


class AdsNormalizer:
    """
    Pure deterministic transformer mapping Google Ads raw GAQL rows into canonical AdsCampaignDaily.
    """

    def __init__(self, default_currency: str = "INR", default_timezone: str = "Asia/Kolkata"):
        self.default_currency = default_currency
        self.default_timezone = default_timezone

    def normalize_row(
        self,
        raw_row: RawGoogleAdsRow,
        workspace_id: str,
        account_id: str
    ) -> AdsCampaignDaily:
        # 1. Financial Conversion: Micros -> Integer Paise (1 paise = 10,000 micros)
        spend_paise = int(round(raw_row.cost_micros / 10_000.0))
        spend_inr = round(raw_row.cost_micros / 1_000_000.0, 2)
        conversion_value_paise = int(round(raw_row.conversions_value_micros / 10_000.0))

        # 2. Status Mapping
        raw_status = (raw_row.campaign_status or "ENABLED").upper()
        if raw_status == "ENABLED":
            mapped_status = "ACTIVE"
        elif raw_status == "PAUSED":
            mapped_status = "PAUSED"
        elif raw_status in ("REMOVED", "ARCHIVED"):
            mapped_status = "ARCHIVED"
        else:
            mapped_status = "ACTIVE"

        # 3. Derived Metrics (with Zero-Division Protection)
        impressions = max(0, raw_row.impressions)
        clicks = max(0, raw_row.clicks)
        conversions = max(0.0, raw_row.conversions)

        ctr = round(float(clicks) / float(impressions), 4) if impressions > 0 else 0.0
        cpc_paise = int(round(float(spend_paise) / float(clicks))) if clicks > 0 else 0
        cpa_paise = int(round(float(spend_paise) / conversions)) if conversions > 0 else 0
        roas = round(float(conversion_value_paise) / float(spend_paise), 2) if spend_paise > 0 else 0.0

        return AdsCampaignDaily(
            workspace_id=workspace_id,
            platform="google_ads",
            account_id=account_id,
            campaign_id=raw_row.campaign_id,
            campaign_name=raw_row.campaign_name,
            date=raw_row.date,
            spend_paise=spend_paise,
            spend_inr=spend_inr,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            conversion_value_paise=conversion_value_paise,
            ctr=ctr,
            cpc_paise=cpc_paise,
            cpa_paise=cpa_paise,
            roas=roas,
            currency=self.default_currency,
            timezone=self.default_timezone,
            status=mapped_status,
            synced_at=datetime.now(timezone.utc).isoformat()
        )

    def normalize_batch(
        self,
        raw_rows: List[RawGoogleAdsRow],
        workspace_id: str,
        account_id: str
    ) -> List[AdsCampaignDaily]:
        return [self.normalize_row(r, workspace_id, account_id) for r in raw_rows]
