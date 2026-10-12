"""
Customer Consent Port Interface (DPDP / GDPR Compliance)
Defines contracts for purpose-specific and channel-specific customer consent storage and retrieval.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List


class ConsentPort(ABC):
    """
    Port for querying customer consent flags.
    Enforces purpose-specific checks (marketing, whatsapp, email, ad_tracking, profiling).
    """

    @abstractmethod
    def get_consent(self, tenant_id: str, customer_id: str) -> Dict[str, bool]:
        """
        Retrieves active consent flags for a given customer.
        Returns a dict e.g. {"marketing": True, "whatsapp": True, "email": False, "ad_tracking": True}
        """
        pass

    @abstractmethod
    def record_consent(
        self,
        tenant_id: str,
        customer_id: str,
        consent_flags: Dict[str, bool],
        evidence_event_id: Optional[str] = None
    ) -> None:
        """
        Records or updates customer consent with audit metadata.
        """
        pass

    def has_consent(self, tenant_id: str, customer_id: str, purpose: str) -> bool:
        """
        Returns True if customer has active, unrevoked consent for the specified purpose.
        Defaults to False (fail-closed) if absent.
        """
        return bool(self.get_consent(tenant_id, customer_id).get(purpose, False))
