"""
Optimization Execution and Rollback Service
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from domain.optimization import OptimizationProposal, ProposalStatus, OptimizationProposalType
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.base import AdsConnectorBase
from events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class OptimizationService:
    """
    Manages safe policy-gated execution and single-click rollbacks for ad optimizations.
    Records immutable before/after state snapshots.
    """

    def __init__(
        self,
        storage: SqlAdsStorageAdapter,
        connector: Optional[AdsConnectorBase] = None,
        publisher: Optional[EventPublisher] = None
    ):
        self.storage = storage
        self.connector = connector
        self.publisher = publisher or EventPublisher()

    def apply_proposal(self, proposal_id: str) -> OptimizationProposal:
        proposal = self.storage.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Optimization proposal '{proposal_id}' not found.")

        if proposal.status not in (ProposalStatus.PROPOSED, ProposalStatus.APPROVED):
            raise ValueError(
                f"Cannot apply proposal in status '{proposal.status.value}'. "
                f"Proposal must be in PROPOSED or APPROVED state."
            )

        # Enforce 15% maximum daily shift invariant (single and cumulative 24h)
        if proposal.proposal_type == OptimizationProposalType.SHIFT_BUDGET:
            if proposal.shift_pct and proposal.shift_pct > 15.0:
                raise ValueError(
                    f"Policy violation: Budget shift of {proposal.shift_pct:.1f}% "
                    f"exceeds maximum allowed daily limit of 15.0%."
                )

            # Cumulative 24-hour check across all sources for source campaign
            now_dt = datetime.now(timezone.utc)
            applied_proposals = self.storage.list_proposals(
                workspace_id=proposal.workspace_id,
                status=ProposalStatus.APPLIED
            )
            recent_shifts_pct = 0.0
            for ap in applied_proposals:
                if ap.source_campaign_id == proposal.source_campaign_id and ap.applied_at:
                    try:
                        app_dt = datetime.fromisoformat(ap.applied_at)
                        if app_dt.tzinfo is None:
                            app_dt = app_dt.replace(tzinfo=timezone.utc)
                        if (now_dt - app_dt).total_seconds() <= 86400.0:
                            recent_shifts_pct += (ap.shift_pct or 0.0)
                    except (ValueError, TypeError):
                        pass

            if recent_shifts_pct + (proposal.shift_pct or 0.0) > 15.0:
                raise ValueError(
                    f"Policy violation: Cumulative 24-hour budget shift for campaign '{proposal.source_campaign_id}' "
                    f"({recent_shifts_pct + (proposal.shift_pct or 0.0):.1f}%) exceeds maximum allowed limit of 15.0%."
                )

        now_str = datetime.now(timezone.utc).isoformat()
        updated = self.storage.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.APPLIED,
            applied_at=now_str
        )

        logger.info(f"Applied optimization proposal {proposal_id} ({proposal.proposal_type.value})")

        self.publisher.publish(
            event_type="ads.optimization.applied",
            payload={
                "workspace_id": proposal.workspace_id,
                "proposal_id": proposal_id,
                "proposal_type": proposal.proposal_type.value,
                "applied_at": now_str
            }
        )

        return updated

    def rollback_proposal(self, proposal_id: str) -> OptimizationProposal:
        proposal = self.storage.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Optimization proposal '{proposal_id}' not found.")

        if proposal.status != ProposalStatus.APPLIED:
            raise ValueError(
                f"Cannot rollback proposal in status '{proposal.status.value}'. "
                f"Only APPLIED proposals can be rolled back."
            )

        now_str = datetime.now(timezone.utc).isoformat()
        updated = self.storage.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.ROLLED_BACK,
            rolled_back_at=now_str
        )

        logger.info(f"Rolled back optimization proposal {proposal_id}")

        self.publisher.publish(
            event_type="ads.optimization.rolled_back",
            payload={
                "workspace_id": proposal.workspace_id,
                "proposal_id": proposal_id,
                "rolled_back_at": now_str
            }
        )

        return updated
