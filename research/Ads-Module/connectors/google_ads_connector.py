"""
Google Ads Connector
Wraps Google Ads API client (GAQL SearchStream) with fallback to PlaybackAdsConnector.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Any, Optional
import logging

from domain.models import RawGoogleAdsRow, CampaignRecord, CampaignStatus
from connectors.base import AdsConnectorBase
from connectors.playback_client import PlaybackAdsConnector
from config import AdsModuleConfig, get_config

logger = logging.getLogger(__name__)


class GoogleAdsConnector:
    """
    Connects to Google Ads API using GAQL (Google Ads Query Language).
    Delegates to PlaybackAdsConnector if live credentials are not configured or in offline mode.
    """

    def __init__(self, config: Optional[AdsModuleConfig] = None):
        self.config = config or get_config()
        self.playback = PlaybackAdsConnector()
        self.client = None
        self._is_live_ready = False

        self._initialize_google_client()

    def _initialize_google_client(self) -> None:
        if not self.config.developer_token or not self.config.client_id or not self.config.refresh_token:
            logger.info("Google Ads live credentials not fully configured. Using playback mode.")
            return

        try:
            from google.ads.googleads.client import GoogleAdsClient

            credentials_dict = {
                "developer_token": self.config.developer_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
                "use_proto_plus": self.config.use_proto_plus,
            }
            if self.config.login_customer_id:
                credentials_dict["login_customer_id"] = self.config.login_customer_id

            self.client = GoogleAdsClient.load_from_dict(credentials_dict)
            self._is_live_ready = True
            logger.info("GoogleAdsClient initialized successfully.")
        except ImportError:
            logger.warning("google-ads library not installed. Falling back to playback mode.")
        except Exception as e:
            logger.warning(f"Failed to initialize GoogleAdsClient ({e}). Falling back to playback mode.")

    def fetch_campaign_metrics(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> List[RawGoogleAdsRow]:
        if not self._is_live_ready or not self.client:
            return self.playback.fetch_campaign_metrics(account_id, start_date, end_date)

        try:
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    segments.date,
                    metrics.cost_micros,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.conversions,
                    metrics.conversions_value
                FROM campaign
                WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
                ORDER BY segments.date DESC
            """

            stream = ga_service.search_stream(customer_id=account_id, query=query)
            results: List[RawGoogleAdsRow] = []

            for batch in stream:
                for row in batch.results:
                    results.append(
                        RawGoogleAdsRow(
                            campaign_id=str(row.campaign.id),
                            campaign_name=row.campaign.name,
                            campaign_status=row.campaign.status.name,
                            date=row.segments.date,
                            cost_micros=row.metrics.cost_micros,
                            impressions=row.metrics.impressions,
                            clicks=row.metrics.clicks,
                            conversions=row.metrics.conversions,
                            conversions_value_micros=int(row.metrics.conversions_value * 1_000_000)
                        )
                    )
            return results

        except Exception as e:
            logger.error(f"Error fetching Google Ads metrics ({e}). Falling back to playback.")
            return self.playback.fetch_campaign_metrics(account_id, start_date, end_date)

    def list_campaigns(self, account_id: str) -> List[CampaignRecord]:
        if not self._is_live_ready or not self.client:
            return self.playback.list_campaigns(account_id)

        try:
            ga_service = self.client.get_service("GoogleAdsService")
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type
                FROM campaign
            """
            stream = ga_service.search_stream(customer_id=account_id, query=query)
            campaigns: List[CampaignRecord] = []

            for batch in stream:
                for row in batch.results:
                    status_str = row.campaign.status.name
                    status_mapped = CampaignStatus.ACTIVE if status_str == "ENABLED" else CampaignStatus.PAUSED
                    campaigns.append(
                        CampaignRecord(
                            campaign_id=str(row.campaign.id),
                            account_id=account_id,
                            name=row.campaign.name,
                            status=status_mapped,
                            channel_type=row.campaign.advertising_channel_type.name,
                            daily_budget_paise=0
                        )
                    )
            return campaigns

        except Exception as e:
            logger.error(f"Error listing Google Ads campaigns ({e}). Falling back to playback.")
            return self.playback.list_campaigns(account_id)

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "is_live_ready": self._is_live_ready,
            "mode": "live" if self._is_live_ready else "playback",
            "login_customer_id": self.config.login_customer_id,
            "client_customer_id": self.config.client_customer_id
        }
