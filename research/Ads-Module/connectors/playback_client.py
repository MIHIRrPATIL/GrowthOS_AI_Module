"""
Offline Playback Client for Google Ads Connector
Loads recorded fixtures and simulates GAQL query responses.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime, date, timedelta

from domain.models import RawGoogleAdsRow, CampaignRecord, CampaignStatus
from connectors.base import AdsConnectorBase


class PlaybackAdsConnector:
    """
    Simulates Google Ads API GAQL SearchStream for development, testing, and offline environments.
    """

    def __init__(self, fixture_path: Optional[str] = None):
        if fixture_path is None:
            base_dir = Path(__file__).parent
            self.fixture_path = base_dir / "fixtures" / "campaign_search_stream.json"
        else:
            self.fixture_path = Path(fixture_path)

        self._simulated_error: Optional[str] = None

    def set_simulated_error(self, error_type: Optional[str]) -> None:
        """
        Allows tests to simulate error scenarios (e.g. 'RATE_LIMIT_EXCEEDED', 'AUTHENTICATION_FAILED').
        """
        self._simulated_error = error_type

    def fetch_campaign_metrics(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> List[RawGoogleAdsRow]:
        if self._simulated_error == "AUTHENTICATION_FAILED":
            raise PermissionError("Google Ads API Authentication Failed (Simulated)")
        if self._simulated_error == "RATE_LIMIT_EXCEEDED":
            raise RuntimeError("Google Ads API Rate Limit Exceeded (Simulated)")

        records: List[RawGoogleAdsRow] = []

        if self.fixture_path.exists():
            with open(self.fixture_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            for item in raw_data:
                seg_date = item.get("segments", {}).get("date")
                if not seg_date:
                    continue

                # Filter by requested date window
                if start_date <= seg_date <= end_date:
                    campaign = item.get("campaign", {})
                    metrics = item.get("metrics", {})
                    records.append(
                        RawGoogleAdsRow(
                            campaign_id=str(campaign.get("id", "10101")),
                            campaign_name=campaign.get("name", "Demo Campaign"),
                            campaign_status=campaign.get("status", "ENABLED"),
                            date=seg_date,
                            cost_micros=int(metrics.get("cost_micros", 0)),
                            impressions=int(metrics.get("impressions", 0)),
                            clicks=int(metrics.get("clicks", 0)),
                            conversions=float(metrics.get("conversions", 0.0)),
                            conversions_value_micros=int(metrics.get("conversions_value", 0))
                        )
                    )

        # If date range is outside fixture, generate synthetic continuous baseline
        if not records:
            records = self._generate_synthetic_rows(account_id, start_date, end_date)

        return records

    def list_campaigns(self, account_id: str) -> List[CampaignRecord]:
        return [
            CampaignRecord(
                campaign_id="10101",
                account_id=account_id,
                name="Domino's Weekend Pizza Delivery Search",
                status=CampaignStatus.ACTIVE,
                channel_type="SEARCH",
                daily_budget_paise=500000
            ),
            CampaignRecord(
                campaign_id="10102",
                account_id=account_id,
                name="Domino's Late Night Pizza Search",
                status=CampaignStatus.ACTIVE,
                channel_type="SEARCH",
                daily_budget_paise=250000
            ),
            CampaignRecord(
                campaign_id="10103",
                account_id=account_id,
                name="Domino's Brand Protection Search",
                status=CampaignStatus.ACTIVE,
                channel_type="SEARCH",
                daily_budget_paise=100000
            )
        ]

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "mode": "playback",
            "fixture_loaded": self.fixture_path.exists(),
            "simulated_error": self._simulated_error
        }

    def deploy_campaign(
        self,
        account_id: str,
        plan: Any,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        if self._simulated_error == "AUTHENTICATION_FAILED":
            raise PermissionError("Google Ads API Authentication Failed (Simulated)")
        if self._simulated_error == "VALIDATION_FAILED":
            raise ValueError("Google Ads Platform Validation Error (Simulated)")

        plan_id = getattr(plan, "plan_id", "default")
        campaign_id = f"sim_camp_{plan_id[-6:]}"
        return {
            "success": True,
            "validate_only": validate_only,
            "account_id": account_id,
            "deployed_campaign_id": campaign_id,
            "status": "VALIDATED" if validate_only else "ACTIVE",
            "message": "Campaign validated successfully in dry-run mode" if validate_only else "Campaign deployed successfully to Google Ads"
        }

    def _generate_synthetic_rows(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> List[RawGoogleAdsRow]:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        curr = start
        rows: List[RawGoogleAdsRow] = []

        while curr <= end:
            dt_str = curr.isoformat()
            rows.append(
                RawGoogleAdsRow(
                    campaign_id="10101",
                    campaign_name="Domino's Weekend Pizza Delivery Search",
                    campaign_status="ENABLED",
                    date=dt_str,
                    cost_micros=4000000000,
                    impressions=10000,
                    clicks=500,
                    conversions=35.0,
                    conversions_value_micros=17500000000
                )
            )
            curr += timedelta(days=1)

        return rows
