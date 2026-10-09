"""
Synchronization Service for Google Ads Data
Orchestrates pull, normalization, storage upsert, and event publishing.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
import logging
from pydantic import BaseModel, Field

from domain.models import AccountConnection, AccountStatus
from domain.events import MetricsUpdatedEvent
from connectors.base import AdsConnectorBase
from normalization.normalizer import AdsNormalizer
from storage.ads_storage import SqlAdsStorageAdapter
from events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    workspace_id: str
    account_id: str
    date_start: str
    date_end: str
    records_synced: int
    success: bool
    error_message: Optional[str] = None
    synced_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdsSyncService:
    """
    Idempotent sync service pulling Google Ads reports and publishing normalized metrics.
    """

    def __init__(
        self,
        connector: AdsConnectorBase,
        normalizer: AdsNormalizer,
        storage: SqlAdsStorageAdapter,
        publisher: EventPublisher
    ):
        self.connector = connector
        self.normalizer = normalizer
        self.storage = storage
        self.publisher = publisher

    def sync_account(
        self,
        workspace_id: str,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lookback_days: int = 3
    ) -> SyncResult:
        # Determine date boundaries (pinned to ISO YYYY-MM-DD)
        today = date.today()
        if not end_date:
            end_date = today.isoformat()
        if not start_date:
            start_date = (today - timedelta(days=lookback_days)).isoformat()

        logger.info(
            f"Initiating Google Ads sync for workspace={workspace_id}, "
            f"account={account_id}, range={start_date}..{end_date}"
        )

        try:
            # 1. Fetch raw GAQL rows from connector
            raw_rows = self.connector.fetch_campaign_metrics(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date
            )

            # 2. Normalize rows into canonical AdsCampaignDaily
            normalized_records = self.normalizer.normalize_batch(
                raw_rows=raw_rows,
                workspace_id=workspace_id,
                account_id=account_id
            )

            # 3. Idempotently upsert into storage
            count_saved = self.storage.upsert_daily_metrics(normalized_records)

            # 4. Publish metrics updated event
            event = MetricsUpdatedEvent(
                workspace_id=workspace_id,
                account_id=account_id,
                platform="google_ads",
                date_start=start_date,
                date_end=end_date,
                record_count=count_saved
            )
            self.publisher.publish_metrics_updated(event)

            # 5. Update account connection timestamp
            existing_conn = self.storage.get_account_connection(workspace_id, account_id)
            if existing_conn:
                existing_conn.updated_at = datetime.now(timezone.utc).isoformat()
                existing_conn.status = AccountStatus.ACTIVE
                self.storage.save_account_connection(existing_conn)

            logger.info(f"Sync complete. Successfully persisted {count_saved} records.")
            return SyncResult(
                workspace_id=workspace_id,
                account_id=account_id,
                date_start=start_date,
                date_end=end_date,
                records_synced=count_saved,
                success=True
            )

        except PermissionError as pe:
            logger.error(f"Authentication failure syncing account {account_id}: {pe}")
            existing_conn = self.storage.get_account_connection(workspace_id, account_id)
            if existing_conn:
                existing_conn.status = AccountStatus.AUTHENTICATION_FAILED
                self.storage.save_account_connection(existing_conn)

            return SyncResult(
                workspace_id=workspace_id,
                account_id=account_id,
                date_start=start_date,
                date_end=end_date,
                records_synced=0,
                success=False,
                error_message=str(pe)
            )

        except Exception as e:
            logger.error(f"Failed to sync account {account_id}: {e}")
            return SyncResult(
                workspace_id=workspace_id,
                account_id=account_id,
                date_start=start_date,
                date_end=end_date,
                records_synced=0,
                success=False,
                error_message=str(e)
            )
