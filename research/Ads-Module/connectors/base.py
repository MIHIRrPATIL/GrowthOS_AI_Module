"""
Abstract Base Protocol for Ad Platform Connectors
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Protocol, List, Dict, Any, runtime_checkable
from domain.models import RawGoogleAdsRow, CampaignRecord


@runtime_checkable
class AdsConnectorBase(Protocol):
    """
    Protocol defining the standardized contract for advertising platform connectors.
    Implemented by GoogleAdsConnector and PlaybackAdsConnector.
    """

    def fetch_campaign_metrics(
        self,
        account_id: str,
        start_date: str,
        end_date: str
    ) -> List[RawGoogleAdsRow]:
        """
        Pulls campaign daily performance metrics for a specified account and date range.
        Dates in ISO format YYYY-MM-DD.
        """
        ...

    def list_campaigns(self, account_id: str) -> List[CampaignRecord]:
        """
        Retrieves active and paused campaigns for an ad account.
        """
        ...

    def health_check(self) -> Dict[str, Any]:
        """
        Checks connector availability, token health, or offline playback status.
        """
        ...

    def deploy_campaign(
        self,
        account_id: str,
        plan: Any,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Mutates or dry-runs Google Ads API to deploy a search campaign.
        Returns a dict with deployed_campaign_id, status, and details.
        """
        ...
