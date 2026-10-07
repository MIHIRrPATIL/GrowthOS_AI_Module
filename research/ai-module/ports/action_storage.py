"""
Action Storage Port Interface (Hexagonal Architecture)
Defines contracts for ActionPlan persistence, PolicyRule retrieval, Outbound Claims,
Dedicated Outreach Logs, and Cumulative Daily Budget tracking.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from domain.actions import ActionPlan, PolicyRule


class ActionStoragePort(ABC):
    """
    Port for managing durable persistence of action plans, policy rules, claims, and limits.
    """

    @abstractmethod
    def save_plan(self, plan: ActionPlan) -> None:
        """Inserts or updates an ActionPlan."""
        pass

    @abstractmethod
    def get_plan(self, tenant_id: str, plan_id: str) -> Optional[ActionPlan]:
        """Retrieves an ActionPlan by tenant and plan ID."""
        pass

    @abstractmethod
    def get_plan_by_signal(self, tenant_id: str, signal_dedupe_key: str, action_type: str) -> Optional[ActionPlan]:
        """Retrieves an active ActionPlan for the given signal and action type."""
        pass

    @abstractmethod
    def list_plans(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ActionPlan]:
        """Lists ActionPlans matching criteria."""
        pass

    @abstractmethod
    def update_plan_status_atomic(
        self,
        tenant_id: str,
        plan_id: str,
        expected_status: str,
        new_status: str,
        expected_version: int,
        approved_by: Optional[str] = None,
        dispatched_at: Optional[str] = None,
        execution_receipt: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atomically updates plan status with optimistic concurrency control.
        Returns True if successful, False if expected_status or expected_version did not match.
        """
        pass

    @abstractmethod
    def get_policy_rule(self, tenant_id: str) -> Optional[PolicyRule]:
        """Retrieves the active policy rule for a tenant."""
        pass

    @abstractmethod
    def save_policy_rule(self, rule: PolicyRule) -> None:
        """Saves or updates a tenant's policy rule."""
        pass

    @abstractmethod
    def reserve_outbound_claim(
        self,
        tenant_id: str,
        idempotency_key: str,
        plan_id: str,
        action_type: str,
        reserved_at: datetime
    ) -> bool:
        """
        Atomically reserves an outbound dispatch claim.
        Returns True if reserved, False if already claimed.
        """
        pass

    @abstractmethod
    def update_outbound_claim(
        self,
        tenant_id: str,
        idempotency_key: str,
        status: str,
        receipt: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """Updates claim status (succeeded, failed, reconciliation_needed)."""
        pass

    @abstractmethod
    def get_outbound_claim(self, tenant_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves claim details for idempotent replay check."""
        pass

    @abstractmethod
    def record_outreach(
        self,
        tenant_id: str,
        log_id: str,
        recipient_type: str,
        recipient_id: str,
        channel: str,
        template_name: str,
        sent_at: datetime,
        status: str = "sent"
    ) -> None:
        """Appends an entry to the dedicated outreach log."""
        pass

    @abstractmethod
    def get_last_outreach(
        self,
        tenant_id: str,
        recipient_type: str,
        recipient_id: str,
        channel: Optional[str] = None
    ) -> Optional[datetime]:
        """Returns timestamp of most recent outreach to recipient."""
        pass

    @abstractmethod
    def record_daily_spend(
        self,
        tenant_id: str,
        date_key: str,
        discount_paise: int,
        budget_shifted_paise: int,
        timestamp: datetime
    ) -> None:
        """Increments cumulative daily discount spend and budget shifts."""
        pass

    @abstractmethod
    def get_daily_spend(self, tenant_id: str, date_key: str) -> Dict[str, Any]:
        """Returns total discount and budget shifted for date."""
        pass

    @abstractmethod
    def count_customer_incentives(self, tenant_id: str, customer_id: str, since: datetime) -> int:
        """Returns number of incentive dispatches (fee waivers, coupons) for customer since timestamp."""
        pass
