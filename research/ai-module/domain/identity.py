"""
Reversible Identity Resolution and Storage Domain Models
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md
- Ingestion, Storage & Reversible Identity Resolution Plan
"""

from datetime import datetime, timezone
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


IdentityType = Literal["anonymous_id", "customer_id", "phone", "email", "device_id", "cookie_id"]
LinkReason = Literal["login", "checkout_phone_match", "magic_link", "manual_merge", "cart_profile"]
LinkStatus = Literal["active", "reversed", "superseded"]


class IdentityLink(_Strict):
    """
    First-class edge representing a reversible link between two identities.
    Raw events remain immutable; linkage can be audited and reversed at any time.
    """
    link_id: str = Field(default_factory=lambda: f"link_{uuid.uuid4().hex[:12]}")
    tenant_id: str
    source_type: IdentityType
    source_id: str
    target_type: IdentityType
    target_id: str
    link_reason: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_event_id: Optional[str] = None
    status: LinkStatus = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reversed_at: Optional[datetime] = None
    reversed_by: Optional[str] = None
    reversal_reason: Optional[str] = None


class ResolvedIdentity(_Strict):
    """
    Aggregated view of a canonical customer identity and all associated aliases.
    """
    tenant_id: str
    canonical_customer_id: str
    linked_identifiers: List[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    active_link_count: int = 0


class IngestionBatchResult(_Strict):
    """
    Detailed audit result for an ingested event batch.
    """
    tenant_id: str
    total_received: int = Field(ge=0)
    inserted_count: int = Field(ge=0)
    deduplicated_count: int = Field(ge=0)
    identity_links_created: int = Field(default=0, ge=0)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
