"""
Event Ingestion and Identity Pipeline Service
Orchestrates event validation, idempotent storage, and automatic reversible identity resolution.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ports.inbound import EventIngestionPort
from ports.storage import EventStoragePort
from ports.identity import IdentityResolutionPort
from ports.outbound import AuditLedgerPort
from domain.events import EventEnvelope
from domain.identity import IngestionBatchResult


class EventIngestionService(EventIngestionPort):
    """
    Core ingestion service coordinating storage and identity resolution.
    """

    def __init__(
        self,
        storage: EventStoragePort,
        identity_resolver: Optional[IdentityResolutionPort] = None,
        audit_ledger: Optional[AuditLedgerPort] = None
    ):
        self.storage = storage
        self.identity_resolver = identity_resolver
        self.audit_ledger = audit_ledger

    def ingest_event(self, envelope: EventEnvelope) -> Dict[str, Any]:
        """
        Ingests a single event envelope.
        Performs idempotent storage and identity transition detection.
        """
        inserted = self.storage.store_event(envelope)
        link_created = False

        # Identity resolution check: merge anonymous session into customer
        if self.identity_resolver and envelope.customer_id and envelope.anonymous_id:
            link_reason = "auth_event" if "login" in envelope.event_name or "purchase" in envelope.event_name else "event_transition"
            link = self.identity_resolver.link_identities(
                tenant_id=envelope.tenant_id,
                source_type="anonymous_id",
                source_id=envelope.anonymous_id,
                target_type="customer_id",
                target_id=envelope.customer_id,
                link_reason=link_reason,
                evidence_event_id=envelope.event_id,
                confidence_score=1.0
            )
            link_created = (link.status == "active")

        return {
            "status": "inserted" if inserted else "deduplicated",
            "tenant_id": envelope.tenant_id,
            "event_id": envelope.event_id,
            "link_created": link_created,
            "canonical_customer_id": envelope.customer_id or envelope.anonymous_id
        }

    def ingest_batch(self, events: List[EventEnvelope]) -> Dict[str, Any]:
        """
        Ingests a batch of events with deduplication and identity resolution.
        """
        if not events:
            return {
                "status": "empty_batch",
                "total_received": 0,
                "inserted_count": 0,
                "deduplicated_count": 0,
                "identity_links_created": 0
            }

        batch_result = self.storage.store_batch(events)
        links_created = 0

        if self.identity_resolver:
            for event in events:
                if event.customer_id and event.anonymous_id:
                    self.identity_resolver.link_identities(
                        tenant_id=event.tenant_id,
                        source_type="anonymous_id",
                        source_id=event.anonymous_id,
                        target_type="customer_id",
                        target_id=event.customer_id,
                        link_reason="batch_transition",
                        evidence_event_id=event.event_id,
                        confidence_score=1.0
                    )
                    links_created += 1

        return {
            "status": "success",
            "tenant_id": batch_result.tenant_id,
            "total_received": batch_result.total_received,
            "inserted_count": batch_result.inserted_count,
            "deduplicated_count": batch_result.deduplicated_count,
            "identity_links_created": links_created,
            "processed_at": batch_result.processed_at.isoformat()
        }
