"""
Inbound Port Interfaces (Hexagonal Architecture)
Defines how external systems communicate into the AI Growth Brain.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.events import EventEnvelope
from domain.actions import ActionPlan


class EventIngestionPort(ABC):
    """
    Inbound port for streaming and batch event telemetry.
    """
    @abstractmethod
    def ingest_event(self, envelope: EventEnvelope) -> Dict[str, Any]:
        """Ingest a single normalized event envelope."""
        pass

    @abstractmethod
    def ingest_batch(self, events: List[EventEnvelope]) -> Dict[str, Any]:
        """Ingest and deduplicate an event batch."""
        pass


class MerchantQueryPort(ABC):
    """
    Inbound port for merchant natural-language business questions.
    """
    @abstractmethod
    def execute_query(self, query: str, tenant_id: str, timeframe: str = "7d") -> Dict[str, Any]:
        """Translates and executes a natural language merchant query."""
        pass


class ApprovalPort(ABC):
    """
    Inbound port for human decision reviews on pending ActionPlans.
    """
    @abstractmethod
    def approve_plan(self, plan_id: str, approver_id: str) -> ActionPlan:
        """Approves a plan and queues/dispatches it to target outbound ports."""
        pass

    @abstractmethod
    def reject_plan(self, plan_id: str, approver_id: str, reason: str) -> ActionPlan:
        """Rejects a proposed action plan with audited justification."""
        pass
