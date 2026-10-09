"""
HTTP Ads Layer Adapter (Module 4 Consuming Module 3 REST API)
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Optional, Dict, Any
import logging
import httpx

from domain.metrics import AdsCampaignDaily
from ports.ads_port import AdsPort

logger = logging.getLogger(__name__)


class HttpAdsAdapter:
    """
    HTTP client querying GrowthOS Ads Module REST API (port 8001).
    Implements AdsPort.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout_seconds: float = 5.0,
        transport: Optional[httpx.BaseTransport] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.transport = transport

    def fetch_bulk_metrics(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        url = f"{self.base_url}/api/v1/ads/campaigns/metrics/bulk"
        params = {
            "workspace_id": workspace_id,
            "start_date": start_date,
            "end_date": end_date
        }

        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                res = client.get(url, params=params)
                res.raise_for_status()
                data = res.json()
                return [AdsCampaignDaily(**item) for item in data]
        except Exception as e:
            logger.error(f"Failed to fetch bulk ad metrics from {url}: {e}")
            raise RuntimeError(f"Ads Module API communication error: {e}") from e

    def fetch_campaign_metrics(
        self,
        campaign_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        url = f"{self.base_url}/api/v1/ads/campaigns/{campaign_id}/metrics"
        params = {
            "start_date": start_date,
            "end_date": end_date
        }

        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                res = client.get(url, params=params)
                res.raise_for_status()
                data = res.json()
                return [AdsCampaignDaily(**item) for item in data]
        except Exception as e:
            logger.error(f"Failed to fetch campaign metrics from {url}: {e}")
            raise RuntimeError(f"Ads Module API communication error: {e}") from e
