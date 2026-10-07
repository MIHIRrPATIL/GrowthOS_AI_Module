"""
Outbound Port Interfaces (Hexagonal Architecture)
Defines contracts for how Module 4 orchestrates actions across external modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from domain.actions import AuditRecord


class LoyaltyPort(ABC):
    """
    Outbound port to Module 1: Loyalty & Rewards Platform.
    """
    @abstractmethod
    def waive_delivery_fee(
        self,
        customer_id: str,
        fee_amount: float,
        points_deducted: int,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Waives delivery fee in exchange for customer loyalty points."""
        pass

    @abstractmethod
    def grant_bonus_points(
        self,
        customer_id: str,
        points: int,
        reason: str,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Credits customer account with retention bonus points."""
        pass

    @abstractmethod
    def issue_discount_coupon(
        self,
        customer_id: str,
        coupon_code: str,
        discount_amount: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Generates dynamic coupon restricted to customer."""
        pass


class BehaviorPort(ABC):
    """
    Outbound port to Module 2: Behavior Intelligence SDK & Pipeline.
    """
    @abstractmethod
    def request_dense_telemetry(
        self,
        component_selector: str,
        duration_minutes: int,
        sample_rate: float = 1.0
    ) -> Dict[str, Any]:
        """Instructs SDK to sample high-frequency micro-behaviors on friction element."""
        pass

    @abstractmethod
    def register_ui_friction_bug(
        self,
        component_selector: str,
        friction_type: str,
        session_count: int,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatches confirmed UX anomaly (e.g. rage click cluster) to issue tracker."""
        pass


class AdsPort(ABC):
    """
    Outbound port to Module 3: Ads Layer Manager.
    """
    @abstractmethod
    def sync_audience_segment(
        self,
        segment_name: str,
        customer_identifiers: List[str],
        target_platform: str = "all"
    ) -> Dict[str, Any]:
        """Pushes dynamic high-intent or churn-risk cohort to Google/Meta ad networks."""
        pass

    @abstractmethod
    def shift_campaign_budget(
        self,
        from_campaign_id: str,
        to_campaign_id: str,
        delta_amount_inr: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Reallocates budget from underperforming campaign to high-ROAS campaign."""
        pass


class NotificationPort(ABC):
    """
    Outbound port for direct customer communication (WhatsApp, Email, SMS).
    """
    @abstractmethod
    def send_recovery_message(
        self,
        recipient: str,
        channel: str,
        template_name: str,
        parameters: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Dispatches personalized recovery communication with 1-click cart link."""
        pass


class AuditLedgerPort(ABC):
    """
    Outbound port for immutable decision and execution record storage.
    """
    @abstractmethod
    def record_audit(self, entry: AuditRecord) -> None:
        """Appends an audit record to the permanent ledger."""
        pass

    @abstractmethod
    def get_audit_trail(
        self,
        tenant_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        limit: int = 50
    ) -> List[AuditRecord]:
        """Retrieves audit entries filtered by tenant, plan, or recent events."""
        pass

    @abstractmethod
    def get_last_hash(self, tenant_id: str) -> str:
        """Returns the record_hash of the most recent audit entry for the tenant, or 'GENESIS'."""
        pass

    @abstractmethod
    def verify_hash_chain(self, tenant_id: str) -> bool:
        """Verifies the cryptographic integrity of the tenant's append-only audit chain."""
        pass
