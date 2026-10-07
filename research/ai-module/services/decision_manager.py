"""
Decision Manager Service
Multi-provider orchestrator behind DecisionPort.
Manages primary provider selection based on benchmark scorecards (Accuracy, Calibration, Latency, Cost),
enforces autonomous eligibility gating, and executes seamless fallback to deterministic rules.
"""

from typing import List, Dict, Any, Optional
import logging

from domain.evaluation import ProviderPerformanceSummary
from ports.decision import DecisionPort, DecisionContext, DecisionCandidate
from engines.rule_decision_provider import RuleDecisionProvider

logger = logging.getLogger(__name__)


class DecisionManager(DecisionPort):
    """
    Provider-agnostic DecisionPort manager.
    Routes candidate generation through the selected primary provider (e.g. Jev or LLM)
    and automatically falls back to RuleDecisionProvider upon API failure or latency breach.
    """

    def __init__(
        self,
        primary_provider: DecisionPort,
        fallback_provider: Optional[DecisionPort] = None,
        performance_summary: Optional[ProviderPerformanceSummary] = None
    ):
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider or RuleDecisionProvider()
        self.performance_summary = performance_summary
        self.fallback_invocation_count = 0
        self.primary_invocation_count = 0
        self.last_rejection_code: Optional[str] = None

    def propose_candidates(self, context: DecisionContext) -> List[DecisionCandidate]:
        """
        Proposes candidates via primary provider, falling back to deterministic rules if primary fails.
        Enforces deterministic rule pre-filtering for cart eligibility before invoking LLM.
        """
        self.last_rejection_code = None

        # 1. Deterministic Rule Pre-filtering for Idle Carts
        if context.signal_type == "idle_cart":
            payload = context.signal_payload
            customer_id = payload.get("customer_id")
            if not customer_id:
                # Anonymous visitors cannot receive outreach or waivers
                self.last_rejection_code = "ANONYMOUS_NO_CONTACT"
                return []

            idle_minutes = payload.get("idle_minutes", 0)
            idle_threshold = context.tenant_config.get("idle_threshold_minutes")
            if idle_threshold is not None and idle_minutes < idle_threshold:
                # Under-threshold idle time is not actionable
                self.last_rejection_code = "UNDER_IDLE_THRESHOLD"
                return []

            cart_val = float(payload.get("cart_value") or (payload.get("cart_total_paise", 0) / 100.0))
            min_val = context.tenant_config.get("min_cart_value_inr")
            if min_val is not None and cart_val < float(min_val):
                # Low-value carts below policy threshold do not qualify for incentives
                self.last_rejection_code = "BELOW_MIN_CART_VALUE"
                return []

        # 2. Invoke Primary Provider with Circuit & Fallback Protection
        self.primary_invocation_count += 1
        try:
            candidates = self.primary_provider.propose_candidates(context)

            # Autonomy Gating:
            # 1. If provider self-reported confidence is present, ensure calibrated_probability is None
            # 2. If primary provider has not achieved empirical calibration qualification, strip calibrated_probability
            sanitized_candidates = []
            for cand in candidates:
                cand_data = cand.model_dump()
                if cand.llm_self_reported_confidence is not None:
                    cand_data["calibrated_probability"] = None
                elif self.performance_summary and not self.performance_summary.is_eligible_for_autonomous:
                    cand_data["calibrated_probability"] = None
                sanitized_candidates.append(DecisionCandidate.model_validate(cand_data))

            return sanitized_candidates

        except Exception as e:
            # Clean 1-line failure log and seamless fallback
            self.fallback_invocation_count += 1
            first_err_line = str(e).splitlines()[0].rstrip(".")
            logger.warning(
                "Primary decision provider fallback triggered: %s. Deterministic rules active.",
                first_err_line
            )
            return self.fallback_provider.propose_candidates(context)

    @classmethod
    def select_best_provider(
        cls,
        summaries: List[ProviderPerformanceSummary],
        provider_instances: Dict[str, DecisionPort],
        fallback_provider: Optional[DecisionPort] = None
    ) -> "DecisionManager":
        """
        Selects the winning primary provider based on multi-criteria optimization:
        1. Must meet qualification: accuracy >= 0.90 and ECE <= 0.10.
        2. From qualified providers, minimizes cost and p95 latency.
        3. If no provider qualifies, defaults to RuleDecisionProvider.
        """
        rules_provider = fallback_provider or RuleDecisionProvider()

        # Filter qualified candidate primary providers (AI/probabilistic models)
        qualified = [
            s for s in summaries 
            if s.provider_name not in ("rules", "rule", "rule_based") and s.is_eligible_for_autonomous
        ]

        if not qualified:
            # If no AI model qualifies, default primary to the deterministic rules provider
            return cls(primary_provider=rules_provider, fallback_provider=rules_provider, performance_summary=None)

        # Multi-objective score: minimize cost and latency
        # Score = (p95_latency / 100.0) + (cost_per_1000 * 2.0) - (accuracy * 10.0)
        best = min(qualified, key=lambda s: (s.p95_latency_ms / 100.0) + (s.cost_per_1000_usd * 2.0) - (s.accuracy * 10.0))
        primary = provider_instances.get(best.provider_name, rules_provider)

        return cls(primary_provider=primary, fallback_provider=rules_provider, performance_summary=best)
