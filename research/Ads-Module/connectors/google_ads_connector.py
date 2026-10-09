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

    def deploy_campaign(
        self,
        account_id: str,
        plan: Any,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Deploys or dry-runs campaign creation via Google Ads API.
        Uses validate_only=True for dry runs to check server-side constraints without committing spend.
        """
        if not self._is_live_ready or not self.client:
            return self.playback.deploy_campaign(account_id, plan, validate_only=validate_only)

        try:
            # Live Google Ads API Campaign creation
            campaign_budget_service = self.client.get_service("CampaignBudgetService")
            campaign_service = self.client.get_service("CampaignService")

            # 1. Create budget operation
            budget_operation = self.client.get_type("CampaignBudgetOperation")
            campaign_budget = budget_operation.create
            campaign_budget.name = f"Budget for {plan.name[:50]}"
            # Convert integer paise to micros: 1 paise = 10,000 micros
            budget_micros = plan.daily_budget_paise * 10_000
            campaign_budget.amount_micros = budget_micros
            campaign_budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD
            campaign_budget.explicitly_shared = False

            # Mutate budget with validate_only flag
            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=account_id,
                operations=[budget_operation],
                validate_only=validate_only
            )

            budget_resource_name = budget_response.results[0].resource_name if not validate_only else "customers/dryrun/campaignBudgets/0"

            # 2. Create campaign operation
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = plan.name
            campaign.advertising_channel_type = self.client.enums.AdvertisingChannelTypeEnum.SEARCH
            campaign.status = self.client.enums.CampaignStatusEnum.PAUSED  # Deploy in PAUSED state for safety
            campaign.campaign_budget = budget_resource_name

            # Target CPA bidding strategy if applicable
            if getattr(plan, "target_cpa_paise", None) and plan.target_cpa_paise > 0:
                campaign.target_cpa.target_cpa_micros = plan.target_cpa_paise * 10_000

            # Mutate campaign with validate_only flag
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=account_id,
                operations=[campaign_operation],
                validate_only=validate_only
            )

            if validate_only:
                return {
                    "success": True,
                    "validate_only": True,
                    "account_id": account_id,
                    "deployed_campaign_id": "dry_run_validated",
                    "status": "VALIDATED",
                    "message": "Campaign dry-run validated by Google Ads API"
                }

            created_resource = campaign_response.results[0].resource_name
            created_id = created_resource.split("/")[-1]

            return {
                "success": True,
                "validate_only": False,
                "account_id": account_id,
                "deployed_campaign_id": str(created_id),
                "resource_name": created_resource,
                "status": "ACTIVE",
                "message": "Campaign created in Google Ads account (paused initial state)"
            }

        except Exception as e:
            logger.error(f"Error deploying Google Ads campaign ({e}). Falling back to playback simulator.")
            return self.playback.deploy_campaign(account_id, plan, validate_only=validate_only)
