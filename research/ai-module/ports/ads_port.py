"""
Ads Layer Port Interface (Module 4 Consuming Module 3)
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Protocol, List, Optional, runtime_checkable
from domain.metrics import AdsCampaignDaily


@runtime_checkable
class AdsPort(Protocol):
    """
    Outbound port defining the contract for retrieving normalized advertising metrics.
    """

    def fetch_bulk_metrics(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        """
        Retrieves daily campaign performance rows for all campaigns in a workspace.
        """
        ...

    def fetch_campaign_metrics(
        self,
        campaign_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        """
        Retrieves daily performance rows for a specific campaign ID.
        """
        ...
