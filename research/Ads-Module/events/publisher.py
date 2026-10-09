"""
Event Publisher for GrowthOS Ads Module
Emits ads.metrics.updated events to in-memory listeners and HTTP webhooks.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Callable, Optional, Dict, Any
import logging
import httpx

from domain.events import MetricsUpdatedEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes domain events from Ads Module to downstream consumers (Module 4 AI Brain).
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self._subscribers: List[Callable[[MetricsUpdatedEvent], None]] = []

    def subscribe(self, callback: Callable[[MetricsUpdatedEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish_metrics_updated(self, event: MetricsUpdatedEvent) -> None:
        logger.info(
            f"Emitting {event.event_name}: workspace={event.workspace_id}, "
            f"account={event.account_id}, range={event.date_start}..{event.date_end}, "
            f"records={event.record_count}"
        )

        # Notify in-memory subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Error in event subscriber ({e})")

        # Notify external webhook if configured
        if self.webhook_url:
            self._post_webhook(event)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        logger.info(f"Emitting domain event '{event_type}': {payload}")
        for subscriber in self._subscribers:
            try:
                subscriber(payload)
            except Exception as e:
                logger.error(f"Error in event subscriber ({e})")

        if self.webhook_url:
            try:
                with httpx.Client(timeout=3.0) as client:
                    client.post(
                        self.webhook_url,
                        json={"event_name": event_type, "payload": payload},
                        headers={"Content-Type": "application/json"}
                    )
            except Exception as e:
                logger.debug(f"Webhook dispatch failed ({e}); ignored in offline/disconnected environments.")

    def _post_webhook(self, event: MetricsUpdatedEvent) -> None:
        try:
            with httpx.Client(timeout=3.0) as client:
                client.post(
                    self.webhook_url,
                    json=event.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            logger.debug(f"Webhook dispatch failed ({e}); ignored in offline/disconnected environments.")
