"""
Optimization Engine Domain Models
Proposals for budget shifts, campaign pausing, and negative keyword additions.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field, ConfigDict


class OptimizationProposalType(str, Enum):
    SHIFT_BUDGET = "SHIFT_BUDGET"
    PAUSE_BLEEDING_CAMPAIGN = "PAUSE_BLEEDING_CAMPAIGN"
    ADD_NEGATIVE_KEYWORDS = "ADD_NEGATIVE_KEYWORDS"


class ProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class OptimizationProposal(BaseModel):
    """
    Structured optimization recommendation adhering to fail-safe policy constraints
    (e.g., maximum 15% budget shift per 24 hours, rollback state tracking).
    """
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(default_factory=lambda: f"opt_{uuid.uuid4().hex[:12]}")
    workspace_id: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1)
    proposal_type: OptimizationProposalType
    source_campaign_id: Optional[str] = Field(default=None, description="Campaign losing budget or getting paused")
    target_campaign_id: Optional[str] = Field(default=None, description="Winning campaign receiving budget")
    source_campaign_name: Optional[str] = None
    target_campaign_name: Optional[str] = None
    current_source_budget_paise: Optional[int] = None
    current_target_budget_paise: Optional[int] = None
    shift_amount_paise: Optional[int] = None
    shift_amount_inr: Optional[float] = None
    shift_pct: Optional[float] = None
    suggested_negative_keywords: List[str] = Field(default_factory=list)
    rationale: str = Field(..., min_length=5)
    metrics_evidence: Dict[str, Any] = Field(default_factory=dict)
    status: ProposalStatus = Field(default=ProposalStatus.PROPOSED)
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    rollback_snapshot: Dict[str, Any] = Field(default_factory=dict, description="State before execution for single-click rollback")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    account_id: str
    lookback_days: int = Field(default=7, ge=1, le=90)
    target_cpa_inr: float = Field(default=250.0, gt=0)
    max_budget_shift_pct: float = Field(default=15.0, ge=1.0, le=25.0, description="Hard cap on daily shift percentage")
