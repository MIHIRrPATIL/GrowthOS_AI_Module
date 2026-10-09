"""
Event Storage Port Interface (Hexagonal Architecture)
Defines abstract contracts for multi-tenant event ingestion, deduplication, and window-based queries.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from domain.events import EventEnvelope
from domain.metrics import TimeWindow
from domain.identity import IngestionBatchResult


class EventStoragePort(ABC):
    """
    Outbound port for multi-tenant telemetry event persistence.
    Guarantees strict tenant isolation and idempotent deduplication by event_id.
    """

    @abstractmethod
    def store_event(self, envelope: EventEnvelope) -> bool:
        """
        Stores a single event.
        Returns True if the event was inserted, or False if it was deduplicated.
        """
        pass

    @abstractmethod
    def store_batch(self, events: List[EventEnvelope]) -> IngestionBatchResult:
        """
        Batch inserts events using idempotent deduplication.
        Returns IngestionBatchResult with exact inserted and deduplicated counts.
        """
        pass

    @abstractmethod
    def get_event(self, tenant_id: str, event_id: str) -> Optional[EventEnvelope]:
        """
        Retrieves a single event scoped strictly to the given tenant_id.
        """
        pass

    @abstractmethod
    def query_events(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        event_names: Optional[List[str]] = None,
        customer_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        session_id: Optional[str] = None,
        exclude_test_traffic: bool = True,
        limit: int = 1000
    ) -> List[EventEnvelope]:
        """
        Queries events scoped strictly by tenant_id within the given UTC TimeWindow.
        Filters out late-arriving events via received_at <= as_of and excludes bot/test traffic.
        """
        pass

    def get_event_time_range(self, tenant_id: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Returns (min_occurred_at, max_occurred_at) for events stored for the tenant,
        or (None, None) if no events exist.
        """
        return None, None

    @abstractmethod
    def count_events(
        self,
        tenant_id: str,
        window: TimeWindow,
        as_of: Optional[datetime] = None,
        event_names: Optional[List[str]] = None,
        exclude_test_traffic: bool = True
    ) -> int:
        """
        Returns exact event count within window for metric denominator calculations.
        """
        pass

    def query_idle_sessions(
        self,
        tenant_id: str,
        as_of: datetime,
        idle_threshold_minutes: float = 15.0
    ) -> List[dict]:
        """
        Queries sessions with unpurchased cart activity idle for at least idle_threshold_minutes.
        """
        return []
