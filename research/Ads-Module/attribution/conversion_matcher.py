"""
Deterministic Closed-Loop Conversion Matcher
Matches order completed transactions back to Google ad touchpoints.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone, timedelta

from domain.attribution import ConversionRecord, IngestConversionRequest, ClickRecord
from storage.ads_storage import SqlAdsStorageAdapter
from events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class ConversionMatcher:
    """
    Attributes completed purchases to Google Ads clicks using deterministic lookback matching:
    1. Direct GCLID touchpoint (Google Click Identifier present on session or visitor path).
    2. Last-touch UTM campaign touchpoint (Google / paid search campaign source).
    3. Organic fallback (no ad touchpoint detected in window).
    """

    def __init__(
        self,
        storage: SqlAdsStorageAdapter,
        publisher: Optional[EventPublisher] = None,
        lookback_days: int = 30
    ):
        self.storage = storage
        self.publisher = publisher or EventPublisher()
        self.lookback_days = lookback_days

    def match_and_record_conversion(self, req: IngestConversionRequest) -> ConversionRecord:
        converted_at = req.converted_at or datetime.now(timezone.utc).isoformat()
        amount_paise = int(round(req.amount_inr * 100))

        # Query prior clicks for anonymous device or customer profile
        clicks = self.storage.get_clicks_for_visitor(
            workspace_id=req.workspace_id,
            anonymous_id=req.anonymous_id,
            user_id=req.user_id,
            lookback_days=self.lookback_days
        )

        matched_gclid: Optional[str] = None
        matched_click_id: Optional[str] = None
        attribution_type = "ORGANIC"

        conv_dt = datetime.fromisoformat(converted_at.replace("Z", "+00:00"))
        cutoff_dt = conv_dt - timedelta(days=self.lookback_days)

        # Filter clicks strictly occurring prior to conversion and within lookback window
        valid_clicks: List[ClickRecord] = []
        for c in clicks:
            try:
                c_dt = datetime.fromisoformat(c.clicked_at.replace("Z", "+00:00"))
                if cutoff_dt <= c_dt <= conv_dt:
                    valid_clicks.append(c)
            except Exception:
                valid_clicks.append(c)

        # Step 1: Check for Direct GCLID match (priority 1)
        for c in valid_clicks:
            if c.gclid and c.gclid.strip():
                matched_gclid = c.gclid.strip()
                matched_click_id = c.click_id
                attribution_type = "DIRECT_GCLID"
                break

        # Step 2: Fallback to Last-Touch UTM if no GCLID
        if not matched_gclid and valid_clicks:
            for c in valid_clicks:
                if c.utm_source or c.utm_campaign:
                    matched_click_id = c.click_id
                    attribution_type = "LAST_TOUCH_UTM"
                    break

        conversion = ConversionRecord(
            workspace_id=req.workspace_id,
            account_id=req.account_id,
            order_id=req.order_id,
            anonymous_id=req.anonymous_id,
            user_id=req.user_id,
            amount_paise=amount_paise,
            amount_inr=req.amount_inr,
            currency=req.currency,
            converted_at=converted_at,
            matched_gclid=matched_gclid,
            matched_click_id=matched_click_id,
            attribution_type=attribution_type,
            conversion_action_name=req.conversion_action_name,
            uploaded_to_google=False
        )

        self.storage.save_conversion(conversion)
        logger.info(
            f"Attributed order {conversion.order_id} ({conversion.amount_inr} {conversion.currency}) "
            f"as {attribution_type} (gclid={matched_gclid})"
        )

        self.publisher.publish(
            event_type="ads.conversion.matched",
            payload={
                "workspace_id": conversion.workspace_id,
                "order_id": conversion.order_id,
                "attribution_type": conversion.attribution_type,
                "matched_gclid": conversion.matched_gclid,
                "amount_paise": conversion.amount_paise,
                "converted_at": conversion.converted_at
            }
        )

        return conversion
