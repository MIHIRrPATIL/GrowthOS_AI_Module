"""
Click Tracking Service for GrowthOS Ads Module
Captures Google Click IDs (gclid) and UTM parameters from merchant web storefronts.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from domain.attribution import ClickRecord, IngestClickRequest
from storage.ads_storage import SqlAdsStorageAdapter

logger = logging.getLogger(__name__)


class ClickTracker:
    """
    Ingests and persists click tracking events from the Behavior SDK and storefront sessions.
    Maintains visitor journey links across anonymous sessions and identified accounts.
    """

    def __init__(self, storage: SqlAdsStorageAdapter):
        self.storage = storage

    def record_click(self, req: IngestClickRequest) -> ClickRecord:
        clicked_at = req.clicked_at or datetime.now(timezone.utc).isoformat()

        record = ClickRecord(
            workspace_id=req.workspace_id,
            gclid=req.gclid,
            utm_source=req.utm_source,
            utm_campaign=req.utm_campaign,
            utm_medium=req.utm_medium,
            utm_term=req.utm_term,
            utm_content=req.utm_content,
            anonymous_id=req.anonymous_id,
            user_id=req.user_id,
            landing_page=req.landing_page,
            clicked_at=clicked_at
        )

        self.storage.save_click(record)
        logger.debug(
            f"Recorded ad click {record.click_id} (gclid={record.gclid}) "
            f"for visitor {record.anonymous_id}"
        )
        return record

    def get_visitor_history(
        self,
        workspace_id: str,
        anonymous_id: str,
        user_id: Optional[str] = None
    ) -> List[ClickRecord]:
        return self.storage.get_clicks_for_visitor(
            workspace_id=workspace_id,
            anonymous_id=anonymous_id,
            user_id=user_id
        )
