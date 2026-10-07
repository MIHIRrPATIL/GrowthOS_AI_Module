"""
In-Memory / SQLite Consent Store Adapter
Implements ConsentPort for purpose- and channel-specific customer consent tracking.
"""

from typing import Dict, Optional
from ports.consent import ConsentPort


class MemoryConsentStore(ConsentPort):
    """
    In-memory consent store for testing and pipeline orchestration.
    """

    def __init__(self):
        # (tenant_id, customer_id) -> Dict[purpose, bool]
        self._store: Dict[tuple, Dict[str, bool]] = {}

    def get_consent(self, tenant_id: str, customer_id: str) -> Dict[str, bool]:
        key = (tenant_id, customer_id)
        return self._store.get(key, {})

    def record_consent(
        self,
        tenant_id: str,
        customer_id: str,
        consent_flags: Dict[str, bool],
        evidence_event_id: Optional[str] = None
    ) -> None:
        key = (tenant_id, customer_id)
        current = self._store.setdefault(key, {})
        current.update(consent_flags)
