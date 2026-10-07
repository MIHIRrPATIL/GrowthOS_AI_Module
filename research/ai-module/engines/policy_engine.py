"""
Deterministic Policy Engine for GrowthOS Module 4
Enforces hard limits, integer-paise financial boundaries, platform-level purpose-specific consent,
contact cooldowns, and TRAI/DPDP quiet hours. Zero LLM involvement.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from domain.actions import (
    ActionPlan,
    PolicyRule,
    PolicyEvaluationResult,
    ActionType,
    ExecutionMode
)
from ports.action_storage import ActionStoragePort
from ports.consent import ConsentPort


class PolicyEngine:
    """
    Evaluates ActionPlans against non-negotiable PolicyRules and platform compliance invariants.
    Pure deterministic logic — models and callers cannot bypass or alter checks.
    """

    def __init__(
        self,
        action_storage: ActionStoragePort,
        consent_store: Optional[ConsentPort] = None,
        consent_port: Optional[ConsentPort] = None
    ):
        self.action_storage = action_storage
        self.consent_store = consent_port or consent_store

    def evaluate(
        self,
        plan: ActionPlan,
        rule: PolicyRule,
        customer_consent: Optional[Dict[str, bool]] = None,
        clock: Optional[datetime] = None,
        as_of: Optional[datetime] = None,
        recipient_utc_offset_hours: float = 5.5  # Default IST (UTC+5:30)
    ) -> PolicyEvaluationResult:
        now = as_of or clock or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        violations: List[str] = []
        limits: Dict[str, Any] = {}

        # ---------------------------------------------------------------------
        # 1. Financial & Discount Hard Limits (Integer Paise, Fail-Closed)
        # ---------------------------------------------------------------------
        if plan.action_type == ActionType.WAIVE_DELIVERY_FEE:
            fee_paise = plan.parameters.get("fee_amount_paise")
            if fee_paise is None and "fee_amount" in plan.parameters:
                try:
                    fee_paise = int(round(float(plan.parameters["fee_amount"]) * 100))
                except (ValueError, TypeError):
                    fee_paise = None

            if fee_paise is None or fee_paise <= 0:
                violations.append("INVALID_FEE_AMOUNT: Fee amount must be a positive integer in paise")
            else:
                limits["fee_amount_paise"] = fee_paise
                limits["max_discount_value_paise"] = rule.max_discount_value_paise
                if fee_paise > rule.max_discount_value_paise:
                    violations.append(
                        f"MAX_DISCOUNT_EXCEEDED: Fee waiver {fee_paise} paise exceeds cap {rule.max_discount_value_paise} paise"
                    )

        elif plan.action_type == ActionType.ISSUE_DISCOUNT_COUPON:
            disc_paise = plan.parameters.get("discount_amount_paise")
            if disc_paise is None and "discount_amount" in plan.parameters:
                try:
                    disc_paise = int(round(float(plan.parameters["discount_amount"]) * 100))
                except (ValueError, TypeError):
                    disc_paise = None

            subtotal_paise = plan.parameters.get("order_subtotal_paise")
            if subtotal_paise is None and "order_subtotal" in plan.parameters:
                try:
                    subtotal_paise = int(round(float(plan.parameters["order_subtotal"]) * 100))
                except (ValueError, TypeError):
                    subtotal_paise = None

            if disc_paise is None or disc_paise <= 0:
                violations.append("INVALID_DISCOUNT_AMOUNT: Discount amount must be a positive integer in paise")
            else:
                limits["discount_amount_paise"] = disc_paise
                limits["max_discount_value_paise"] = rule.max_discount_value_paise
                if disc_paise > rule.max_discount_value_paise:
                    violations.append(
                        f"MAX_DISCOUNT_EXCEEDED: Discount coupon {disc_paise} paise exceeds cap {rule.max_discount_value_paise} paise"
                    )

            # Fail-closed percentage check: subtotal is required
            if subtotal_paise is None or subtotal_paise <= 0:
                violations.append("MISSING_ORDER_SUBTOTAL: Order subtotal required for discount percentage verification (fail-closed)")
            elif disc_paise is not None and disc_paise > 0:
                pct = (disc_paise / subtotal_paise) * 100.0
                limits["discount_pct"] = round(pct, 2)
                limits["max_discount_pct"] = rule.max_discount_pct
                if pct > rule.max_discount_pct:
                    violations.append(
                        f"MAX_DISCOUNT_PERCENT_EXCEEDED: Discount of {pct:.2f}% exceeds allowed {rule.max_discount_pct}%"
                    )

        elif plan.action_type == ActionType.SHIFT_CAMPAIGN_BUDGET:
            delta_paise = plan.parameters.get("delta_amount_paise")
            if delta_paise is None and "delta_amount_inr" in plan.parameters:
                try:
                    delta_paise = int(round(float(plan.parameters["delta_amount_inr"]) * 100))
                except (ValueError, TypeError):
                    delta_paise = None

            daily_budget_paise = plan.parameters.get("current_daily_budget_paise")
            if daily_budget_paise is None and "current_daily_budget_inr" in plan.parameters:
                try:
                    daily_budget_paise = int(round(float(plan.parameters["current_daily_budget_inr"]) * 100))
                except (ValueError, TypeError):
                    daily_budget_paise = None

            if delta_paise is None or delta_paise <= 0:
                violations.append("INVALID_BUDGET_DELTA: Budget shift amount must be a positive integer in paise")
            elif daily_budget_paise is None or daily_budget_paise <= 0:
                violations.append("MISSING_CAMPAIGN_BUDGET: Campaign daily budget required for budget shift limit verification (fail-closed)")
            else:
                shift_pct = (delta_paise / daily_budget_paise) * 100.0
                limits["shift_pct"] = round(shift_pct, 2)
                limits["max_daily_budget_shift_pct"] = rule.max_daily_budget_shift_pct
                if shift_pct > rule.max_daily_budget_shift_pct:
                    violations.append(
                        f"MAX_BUDGET_SHIFT_EXCEEDED: Budget shift {shift_pct:.2f}% exceeds allowed daily limit {rule.max_daily_budget_shift_pct}%"
                    )

        # ---------------------------------------------------------------------
        # 2. Cumulative Daily Spend Limits
        # ---------------------------------------------------------------------
        planned_incentive_paise = 0
        if plan.action_type == ActionType.WAIVE_DELIVERY_FEE:
            planned_incentive_paise = plan.parameters.get("fee_amount_paise") or 0
        elif plan.action_type == ActionType.ISSUE_DISCOUNT_COUPON:
            planned_incentive_paise = plan.parameters.get("discount_amount_paise") or 0

        if planned_incentive_paise > 0:
            date_key = now.strftime("%Y-%m-%d")
            spend_record = self.action_storage.get_daily_spend(plan.tenant_id, date_key)
            current_discount_paise = spend_record.get("total_discount_paise", 0)
            limits["cumulative_discount_today_paise"] = current_discount_paise
            limits["max_daily_discount_budget_paise"] = rule.max_daily_discount_budget_paise

            if current_discount_paise + planned_incentive_paise > rule.max_daily_discount_budget_paise:
                violations.append(
                    f"DAILY_DISCOUNT_BUDGET_EXCEEDED: Planned {planned_incentive_paise} paise would push daily total "
                    f"to {current_discount_paise + planned_incentive_paise} paise, exceeding daily budget {rule.max_daily_discount_budget_paise} paise"
                )

        # ---------------------------------------------------------------------
        # 3. Per-Customer Incentive Abuse Cap (e.g. Max 1 in 30 Days)
        # ---------------------------------------------------------------------
        if plan.customer_id and plan.action_type in (ActionType.WAIVE_DELIVERY_FEE, ActionType.ISSUE_DISCOUNT_COUPON):
            since_30d = now - timedelta(days=30)
            recent_cnt = self.action_storage.count_customer_incentives(plan.tenant_id, plan.customer_id, since_30d)
            limits["customer_recent_incentives_30d"] = recent_cnt
            limits["max_incentives_per_customer_30d"] = rule.max_incentives_per_customer_30d
            if recent_cnt >= rule.max_incentives_per_customer_30d:
                violations.append(
                    f"CUSTOMER_INCENTIVE_LIMIT_REACHED: Customer has already received {recent_cnt} incentives in the past 30 days (limit: {rule.max_incentives_per_customer_30d})"
                )

        # ---------------------------------------------------------------------
        # 4. Purpose-Specific Customer Consent (Platform Invariant)
        # ---------------------------------------------------------------------
        if rule.require_customer_consent:
            # Resolve active consent flags
            active_consent: Dict[str, bool] = {}
            if self.consent_store and plan.customer_id:
                active_consent = self.consent_store.get_consent(plan.tenant_id, plan.customer_id)
            elif customer_consent:
                active_consent = customer_consent

            if plan.action_type == ActionType.SEND_RECOVERY_WHATSAPP:
                has_whatsapp = (active_consent.get("whatsapp_marketing") is True) or (
                    active_consent.get("marketing") is True and active_consent.get("whatsapp") is True
                )
                if not has_whatsapp:
                    violations.append("MISSING_CUSTOMER_CONSENT: WhatsApp outreach requires explicit marketing and whatsapp consent")

            elif plan.action_type == ActionType.SEND_RECOVERY_EMAIL:
                has_email = (active_consent.get("email_marketing") is True) or (
                    active_consent.get("marketing") is True and active_consent.get("email") is True
                )
                if not has_email:
                    violations.append("MISSING_CUSTOMER_CONSENT: Email outreach requires explicit marketing and email consent")

            elif plan.action_type == ActionType.SYNC_AUDIENCE_SEGMENT:
                has_ads = (active_consent.get("ad_tracking") is True)
                if not has_ads:
                    violations.append("MISSING_CUSTOMER_CONSENT: Audience sync requires explicit ad_tracking consent")

        # ---------------------------------------------------------------------
        # 5. Dedicated Outreach Cooldown
        # ---------------------------------------------------------------------
        if plan.action_type in (ActionType.SEND_RECOVERY_WHATSAPP, ActionType.SEND_RECOVERY_EMAIL):
            recip_id = plan.customer_id or plan.anonymous_id or str(plan.parameters.get("recipient", ""))
            recip_type = "customer_id" if plan.customer_id else "anonymous_id"
            channel = "whatsapp" if plan.action_type == ActionType.SEND_RECOVERY_WHATSAPP else "email"

            last_outreach = self.action_storage.get_last_outreach(plan.tenant_id, recip_type, recip_id, channel)
            if last_outreach:
                elapsed_hours = (now - last_outreach).total_seconds() / 3600.0
                limits["hours_since_last_outreach"] = round(elapsed_hours, 2)
                limits["contact_cooldown_hours"] = rule.contact_cooldown_hours
                if elapsed_hours < rule.contact_cooldown_hours:
                    violations.append(
                        f"CONTACT_COOLDOWN_ACTIVE: Recipient received {channel} outreach {elapsed_hours:.1f}h ago (Cooldown: {rule.contact_cooldown_hours}h)"
                    )

        # ---------------------------------------------------------------------
        # 6. Quiet Hours Enforcement (TRAI / DPDP: 21:00 to 09:00 Blocked)
        # ---------------------------------------------------------------------
        if plan.action_type in (ActionType.SEND_RECOVERY_WHATSAPP, ActionType.SEND_RECOVERY_EMAIL):
            recipient_local_time = now + timedelta(hours=recipient_utc_offset_hours)
            local_hour = recipient_local_time.hour
            local_minute = recipient_local_time.minute
            limits["recipient_local_hour"] = local_hour

            if local_hour >= 21 or local_hour < 9:
                violations.append(
                    f"QUIET_HOURS_RESTRICTION: Outreach blocked between 21:00 and 09:00 local time (Attempted at {local_hour:02d}:{local_minute:02d})"
                )

        passed = (len(violations) == 0)

        return PolicyEvaluationResult(
            passed=passed,
            violations=violations,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            evaluated_at=now.isoformat(),
            evaluated_limits=limits
        )
