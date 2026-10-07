"""
Identity Resolution Port Interface (Hexagonal Architecture)
Defines abstract contracts for managing reversible links between anonymous visitors and customers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from domain.identity import IdentityLink, IdentityType


class IdentityResolutionPort(ABC):
    """
    Port for managing reversible identity linkages and canonical customer identity resolution.
    Raw events remain immutable; links can be established, traversed, and reversed at any time.
    """

    @abstractmethod
    def link_identities(
        self,
        tenant_id: str,
        source_type: IdentityType,
        source_id: str,
        target_type: IdentityType,
        target_id: str,
        link_reason: str,
        evidence_event_id: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> IdentityLink:
        """
        Establishes an active reversible link between two identifiers.
        """
        pass

    @abstractmethod
    def reverse_link(
        self,
        tenant_id: str,
        link_id: str,
        reversed_by: str,
        reversal_reason: str
    ) -> IdentityLink:
        """
        Reverses an existing active link, uncoupling the associated identities.
        """
        pass

    @abstractmethod
    def get_canonical_customer_id(self, tenant_id: str, identifier: str) -> Optional[str]:
        """
        Resolves any identifier (e.g. anonymous_id, phone) to its canonical customer_id
        by traversing active identity links.
        """
        pass

    @abstractmethod
    def get_linked_identifiers(self, tenant_id: str, canonical_customer_id: str) -> Set[str]:
        """
        Returns all active alias identifiers currently linked to this customer_id.
        """
        pass

    @abstractmethod
    def get_links_for_identifier(
        self,
        tenant_id: str,
        identifier: str,
        include_reversed: bool = False
    ) -> List[IdentityLink]:
        """
        Returns the audit trail of identity links touching this identifier.
        """
        pass
