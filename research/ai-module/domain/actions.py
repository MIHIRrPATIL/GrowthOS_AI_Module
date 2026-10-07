"""
Action Plan, Governance Policy, and Audit Record Schemas
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Components 6, 7 & 8)
- Hardened Architectural Specification (Revision 2)

Invariants:
1. Strict integer paise for all monetary limits and spend to eliminate float rounding errors.
2. Purpose-specific, channel-specific consent enforcement.
3. Cryptographically chained append-only audit trail with tamper-evident record hashing.
4. Deterministic plan ID generation from signal dedupe key to prevent rerun duplication.
5. Fail-closed financial limit checks and cumulative daily spend tracking.
"""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import json
import uuid
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ActionType(str, Enum):
    # Module 1 Loyalty Actions
    WAIVE_DELIVERY_FEE = "waive_delivery_fee"
    GRANT_BONUS_POINTS = "grant_bonus_points"
    ISSUE_DISCOUNT_COUPON = "issue_discount_coupon"
    UPGRADE_TIER = "upgrade_tier"

    # Module 2 Behavior Actions
    REQUEST_DENSE_TELEMETRY = "request_dense_telemetry"
    FLAG_UI_FRICTION_BUG = "flag_ui_friction_bug"

    # Module 3 Ads Actions
    SYNC_AUDIENCE_SEGMENT = "sync_audience_segment"
    SHIFT_CAMPAIGN_BUDGET = "shift_campaign_budget"
    PAUSE_UNDERPERFORMING_AD = "pause_underperforming_ad"

    # Direct Notification Actions
    SEND_RECOVERY_WHATSAPP = "send_recovery_whatsapp"
    SEND_RECOVERY_EMAIL = "send_recovery_email"

    # Fallback / Non-action
    DO_NOTHING = "do_nothing"


class ExecutionMode(str, Enum):
    MANUAL = "manual"            # Intelligence only; human operates
    APPROVAL = "approval"        # Default: Proposes action, awaits human confirmation
    AUTONOMOUS = "autonomous"    # Executes automatically if confidence and policies permit


# Strongly Typed Action Parameters (Strict bounds, zero NaN/Negative amounts)
class WaiveFeeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fee_amount_paise: int = Field(..., gt=0, description="Delivery fee in integer paise")
    points_deducted: int = Field(default=0, ge=0)
    customer_id: str = Field(..., min_length=1)


class BonusPointsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)


class DiscountCouponParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coupon_code: str = Field(..., min_length=3)
    discount_amount_paise: int = Field(..., gt=0)
    order_subtotal_paise: int = Field(..., gt=0)
    customer_id: str = Field(..., min_length=1)


class ShiftBudgetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_campaign_id: str = Field(..., min_length=1)
    to_campaign_id: str = Field(..., min_length=1)
    delta_amount_paise: int = Field(..., gt=0)
    current_daily_budget_paise: int = Field(..., gt=0)


class RecoveryMessageParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient: str = Field(..., min_length=3)
    channel: Literal["whatsapp", "email", "sms"]
    template_name: str = Field(..., min_length=1)
    parameters: Dict[str, str] = Field(default_factory=dict)
    recipient_type: Literal["customer_id", "anonymous_id"]
    cart_total_paise: int = Field(..., gt=0)


class ReportBugParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_selector: str = Field(..., min_length=1)
    friction_type: str = Field(..., min_length=1)
    session_count: int = Field(..., gt=0)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class DenseTelemetryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_selector: str = Field(..., min_length=1)
    duration_minutes: int = Field(..., gt=0, le=1440)
    sample_rate: float = Field(default=1.0, gt=0.0, le=1.0)


class SyncAudienceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segment_name: str = Field(..., min_length=1)
    customer_identifiers: List[str] = Field(..., min_length=1)
    target_platform: str = Field(default="all")


class PolicyRule(BaseModel):
    """
    Deterministic governance limits and guardrails that AI reasoning CANNOT bypass.
    Monetary values are stored in integer paise (1 INR = 100 paise).
    """
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(default_factory=lambda: f"pol_{uuid.uuid4().hex[:8]}")
    tenant_id: str = Field(..., description="Tenant / Workspace ID")
    version: int = Field(default=1, ge=1)
    name: str = Field(default="Standard Merchant Guardrails")

    # Financial & Discount Boundaries in Integer Paise (e.g. 15000 paise = 150 INR)
    max_discount_value_paise: int = Field(default=15000, gt=0, description="Max absolute discount in paise")
    max_discount_value_inr: float = Field(default=150.0, gt=0.0, description="Convenience property for float INR")
    max_discount_pct: float = Field(default=25.0, gt=0.0, le=100.0, description="Max percentage discount on subtotal")
    max_daily_budget_shift_pct: float = Field(default=15.0, gt=0.0, le=100.0, description="Max daily ad budget shift")
    max_daily_discount_budget_paise: int = Field(default=5000000, gt=0, description="Max total discount paise per day (INR 50k)")

    # Outreach & Frequency Boundaries
    contact_cooldown_hours: int = Field(default=48, ge=0, description="Minimum hours between outreach to same customer")
    max_incentives_per_customer_30d: int = Field(default=1, ge=0, description="Max incentive actions per customer in 30 days")
    require_customer_consent: bool = Field(default=True, description="Enforce DPDP / GDPR consent flags (platform invariant)")

    # Confidence Threshold & Allowlist for Autonomous Execution
    autonomous_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    autonomous_action_allowlist: List[str] = Field(
        default_factory=lambda: ["flag_ui_friction_bug", "request_dense_telemetry"],
        description="Action types permitted to execute autonomously if confidence threshold is met"
    )
    emergency_kill_switch_active: bool = Field(default=False, description="Emergency tenant halt for all autonomy")

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def sync_paise_and_inr(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "max_discount_value_inr" in values and "max_discount_value_paise" not in values:
                values["max_discount_value_paise"] = int(round(float(values["max_discount_value_inr"]) * 100))
            elif "max_discount_value_paise" in values and "max_discount_value_inr" not in values:
                values["max_discount_value_inr"] = float(values["max_discount_value_paise"]) / 100.0
        return values


class PolicyEvaluationResult(BaseModel):
    """
    Result of evaluating an ActionPlan against a PolicyRule.
    """
    model_config = ConfigDict(extra="forbid")

    passed: bool
    violations: List[str] = Field(default_factory=list)
    rule_id: str
    rule_version: int = 1
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluated_limits: Dict[str, Any] = Field(default_factory=dict)


ActionStatus = Literal[
    "drafted",
    "pending_approval",
    "approved",
    "dispatching",
    "dispatched",
    "rejected",
    "failed",
    "expired",
    "reconciliation_needed"
]


class ActionPlan(BaseModel):
    """
    Structured action proposal generated by the AI Growth Brain.
    """
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    tenant_id: str = Field(..., description="Tenant / Workspace ID")
    signal_dedupe_key: str = Field(default="", description="Originating signal dedupe key for idempotent plan derivation")
    customer_id: Optional[str] = Field(default=None)
    anonymous_id: Optional[str] = Field(default=None)
    action_type: ActionType = Field(..., description="Action category from fixed menu")
    target_module: Literal["module_1_loyalty", "module_2_behavior", "module_3_ads", "notification"] = Field(...)

    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters payload")
    reasoning_summary: str = Field(..., description="Plain-language justification for why this action is recommended")
    evidence_citations: List[str] = Field(default_factory=list, description="Grounding facts from metrics and graph")

    priority_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Heuristic priority for ranking (0.0 to 1.0)")
    calibrated_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Calibrated outcome probability")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Convenience confidence score")

    policy_check_passed: bool = Field(default=False)
    policy_violations: List[str] = Field(default_factory=list)
    rule_version: int = Field(default=1)
    execution_mode: ExecutionMode = Field(default=ExecutionMode.APPROVAL)

    status: ActionStatus = Field(default="drafted")
    version: int = Field(default=1, description="Optimistic locking version counter")
    is_holdout: bool = Field(default=False, description="True if allocated to 10% causal control holdout group")

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = Field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat())
    approved_at: Optional[str] = Field(default=None)
    approved_by: Optional[str] = Field(default=None)
    dispatched_at: Optional[str] = Field(default=None)
    execution_receipt: Optional[Dict[str, Any]] = Field(default=None)

    @classmethod
    def generate_plan_id(cls, tenant_id: str, signal_dedupe_key: str, action_type: str, target_id: str) -> str:
        """
        Derives a deterministic plan_id from the signal and target to prevent rerun duplicates.
        """
        raw = f"{tenant_id}:{signal_dedupe_key}:{action_type}:{target_id}".encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()[:12]
        return f"plan_{h}"


class AuditRecord(BaseModel):
    """
    Append-only ledger entry tracking every reasoning, policy check, decision, and dispatch.
    Chained cryptographically via prev_record_hash and record_hash.
    """
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    tenant_id: str = Field(..., description="Tenant / Workspace ID")
    plan_id: str = Field(...)
    actor: str = Field(..., description="ai_growth_brain, human_merchant:id, policy_gate, outbound_adapter")
    event_type: str = Field(..., description="e.g. plan_drafted, policy_evaluated, plan_approved, dispatch_attempted, dispatch_succeeded")
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_record_hash: str = Field(default="GENESIS")
    record_hash: str = Field(default="")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def calculate_hash(self) -> str:
        payload = {
            "prev_record_hash": self.prev_record_hash,
            "audit_id": self.audit_id,
            "tenant_id": self.tenant_id,
            "plan_id": self.plan_id,
            "actor": self.actor,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "details": self.details
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def compute_record_hash(self) -> "AuditRecord":
        if not self.record_hash:
            self.record_hash = self.calculate_hash()
        return self
