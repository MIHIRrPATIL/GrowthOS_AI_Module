"""
Domain models and contracts package for GrowthOS Module 4 (AI Growth Brain)
"""

from .events import (
    EventEnvelope,
    PageMetadata,
    UTMMetadata,
    DeviceMetadata,
    NetworkMetadata,
    ConsentState,
)
from .metrics import (
    MetricResult,
    DigestFlag,
    DigestReport,
    IdleCartAnomaly,
    TimeWindow,
    Unit,
    Period,
    Severity,
    Polarity,
)
from .actions import (
    ActionType,
    ExecutionMode,
    PolicyRule,
    ActionPlan,
    AuditRecord,
)
from .identity import (
    IdentityLink,
    ResolvedIdentity,
    IngestionBatchResult,
    IdentityType,
    LinkReason,
    LinkStatus,
)

__all__ = [
    "EventEnvelope",
    "PageMetadata",
    "UTMMetadata",
    "DeviceMetadata",
    "NetworkMetadata",
    "ConsentState",
    "MetricResult",
    "DigestFlag",
    "DigestReport",
    "IdleCartAnomaly",
    "TimeWindow",
    "Unit",
    "Period",
    "Severity",
    "Polarity",
    "ActionType",
    "ExecutionMode",
    "PolicyRule",
    "ActionPlan",
    "AuditRecord",
    "IdentityLink",
    "ResolvedIdentity",
    "IngestionBatchResult",
    "IdentityType",
    "LinkReason",
    "LinkStatus",
]
