"""
Ports package for GrowthOS Module 4 (Hexagonal Architecture)
"""

from .inbound import (
    EventIngestionPort,
    MerchantQueryPort,
    ApprovalPort,
)
from .outbound import (
    LoyaltyPort,
    BehaviorPort,
    AdsPort,
    NotificationPort,
    AuditLedgerPort,
)
from .storage import EventStoragePort
from .identity import IdentityResolutionPort

__all__ = [
    "EventIngestionPort",
    "MerchantQueryPort",
    "ApprovalPort",
    "LoyaltyPort",
    "BehaviorPort",
    "AdsPort",
    "NotificationPort",
    "AuditLedgerPort",
    "EventStoragePort",
    "IdentityResolutionPort",
]
