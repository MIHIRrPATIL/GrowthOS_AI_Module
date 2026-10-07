"""
OpenRouter Decision Provider Adapter
Implements DecisionPort and benchmark evaluation using live frontier models on OpenRouter
(e.g., Google Gemini 2.0 Flash, Anthropic Claude 3.5 Sonnet, Llama 3.3 70B).
"""

from typing import List, Dict, Any, Optional
import json

from domain.actions import (
    ActionType,
    WaiveFeeParams,
    RecoveryMessageParams,
    ReportBugParams,
    SyncAudienceParams,
    DenseTelemetryParams
)
from domain.evaluation import DecisionBenchmarkCase, ProviderPrediction
from ports.decision import DecisionPort, DecisionContext, DecisionCandidate
from adapters.openrouter_client import OpenRouterClient


class OpenRouterDecisionProvider(DecisionPort):
    """
    Live LLM Decision Provider powered by OpenRouter API.
    Interprets telemetry signals, produces fact-grounded action candidates with confidence scores,
    and runs benchmark evaluations with real network latency and token pricing.
    """

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        model: Optional[str] = None
    ):
        self.client = client or OpenRouterClient(model=model)

    def propose_candidates(self, context: DecisionContext) -> List[DecisionCandidate]:
        """
        Dispatches signal context to OpenRouter model for candidate action generation.
        """
        system_prompt = (
            "You are an AI decision engine for GrowthOS eCommerce & retail operations.\n"
            "Given an operational signal (idle cart or metric digest anomaly), determine the single best action.\n"
            "AVAILABLE ACTIONS:\n"
            "- 'WAIVE_DELIVERY_FEE': For identified customer carts with high value (>= INR 500) idle for >= 30 mins.\n"
            "- 'SEND_RECOVERY_WHATSAPP': For mid-value carts (>= INR 300).\n"
            "- 'FLAG_UI_FRICTION_BUG': For severe spike in funnel checkout drop-off or rage clicks.\n"
            "- 'SYNC_AUDIENCE_SEGMENT': For high cart abandonment spikes requiring ad suppression/retargeting.\n"
            "- 'DO_NOTHING': If anonymous visitor, insignificant noise, low value cart, or favorable trend.\n"
            "RULES:\n"
            "- Anonymous visitors CANNOT receive fee waivers or WhatsApp outreach (return DO_NOTHING).\n"
            "- When proposing WAIVE_DELIVERY_FEE, explicitly state policy conditions in reasoning_summary (including subject to 10% randomized holdout control and frequency limit).\n"
            "- Return strictly a JSON object matching the schema."
        )

        user_prompt = f"""
Tenant ID: {context.tenant_id}
Signal Type: {context.signal_type}
Signal Payload:
{json.dumps(context.signal_payload, indent=2)}

Tenant Config:
{json.dumps(context.tenant_config, indent=2)}

JSON Output Schema:
{{
  "action_type": "WAIVE_DELIVERY_FEE" | "SEND_RECOVERY_WHATSAPP" | "FLAG_UI_FRICTION_BUG" | "SYNC_AUDIENCE_SEGMENT" | "DO_NOTHING",
  "priority_score": <float between 0.0 and 1.0>,
  "confidence_probability": <float between 0.0 and 1.0>,
  "reasoning_summary": "<fact-based explanation>",
  "evidence_citations": ["<fact 1>", "<fact 2>"]
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        resp = self.client.chat_completion(messages, json_mode=True, temperature=0.0)
        data = resp.get("json") or {}

        action_str = data.get("action_type", "DO_NOTHING").upper()
        if action_str in ("DO_NOTHING", "NONE"):
            return []

        priority = float(data.get("priority_score", 0.80))
        confidence = float(data.get("confidence_probability", 0.85))
        reasoning = data.get("reasoning_summary", "Action proposed by OpenRouter decision provider.")
        evidence = data.get("evidence_citations", [])

        payload = context.signal_payload
        customer_id = payload.get("customer_id")
        anonymous_id = payload.get("anonymous_id")

        if action_str == "WAIVE_DELIVERY_FEE":
            if not customer_id:
                return []
            fee_paise = context.tenant_config.get("fee_waiver_amount_paise", 5000)
            return [
                DecisionCandidate(
                    action_type=ActionType.WAIVE_DELIVERY_FEE,
                    target_module="module_1_loyalty",
                    target_type="customer",
                    target_id=customer_id,
                    customer_id=customer_id,
                    anonymous_id=anonymous_id,
                    parameters=WaiveFeeParams(
                        fee_amount_paise=fee_paise,
                        points_deducted=0,
                        customer_id=customer_id
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=priority,
                    calibrated_probability=None,
                    llm_self_reported_confidence=confidence,
                    is_holdout=False
                )
            ]

        elif action_str == "SEND_RECOVERY_WHATSAPP":
            if not customer_id:
                return []
            cart_total_paise = int(float(payload.get("cart_value", 0)) * 100)
            return [
                DecisionCandidate(
                    action_type=ActionType.SEND_RECOVERY_WHATSAPP,
                    target_module="notification",
                    target_type="customer",
                    target_id=customer_id,
                    customer_id=customer_id,
                    anonymous_id=anonymous_id,
                    parameters=RecoveryMessageParams(
                        recipient=customer_id,
                        channel="whatsapp",
                        template_name="cart_recovery_v1",
                        parameters={"cart_value": str(payload.get("cart_value", "0"))},
                        recipient_type="customer_id",
                        cart_total_paise=max(100, cart_total_paise)
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=priority,
                    calibrated_probability=None,
                    llm_self_reported_confidence=confidence,
                    is_holdout=False
                )
            ]

        elif action_str == "FLAG_UI_FRICTION_BUG":
            m_name = payload.get("metric_name", "checkout_funnel")
            return [
                DecisionCandidate(
                    action_type=ActionType.FLAG_UI_FRICTION_BUG,
                    target_module="module_2_behavior",
                    target_type="system",
                    target_id="checkout_funnel_step_2",
                    customer_id=None,
                    anonymous_id=None,
                    parameters=ReportBugParams(
                        component_selector="checkout_funnel_step_2",
                        friction_type="drop_off_spike",
                        session_count=int(payload.get("current_sample_size", payload.get("sample_size", 50))),
                        evidence={"metric_name": m_name, "details": reasoning}
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=priority,
                    calibrated_probability=None,
                    llm_self_reported_confidence=confidence,
                    is_holdout=False
                )
            ]

        elif action_str == "SYNC_AUDIENCE_SEGMENT":
            return [
                DecisionCandidate(
                    action_type=ActionType.SYNC_AUDIENCE_SEGMENT,
                    target_module="module_3_ads",
                    target_type="audience",
                    target_id="cart_abandoners_segment",
                    customer_id=None,
                    anonymous_id=None,
                    parameters=SyncAudienceParams(
                        segment_name="cart_abandoners_segment",
                        customer_identifiers=["cohort_cart_abandoners"],
                        target_platform="meta"
                    ),
                    reasoning_summary=reasoning,
                    evidence_citations=evidence,
                    priority_score=priority,
                    calibrated_probability=None,
                    llm_self_reported_confidence=confidence,
                    is_holdout=False
                )
            ]

        return []

    def predict_benchmark_case(self, case: DecisionBenchmarkCase) -> ProviderPrediction:
        """
        Directly prompts OpenRouter model on a labeled benchmark test case.
        Captures real latency and exact token cost.
        """
        task_guidelines = ""
        if case.task_type == "action_routing":
            task_guidelines = (
                "DOMAIN RULES FOR ACTION ROUTING:\n"
                "- 'waive_delivery_fee': signal_type is 'idle_cart', identified customer (customer_id present), cart_value >= 500, idle_minutes >= 30.\n"
                "- 'flag_ui_friction_bug': severe spike in drop-off rate or rage clicks on checkout step 2 with significant sample.\n"
                "- 'sync_audience_segment': high cart abandonment spike or exit intent spike requiring retargeting.\n"
                "- 'do_nothing': anonymous visitor (no customer_id), cart_value < 500, idle < 30 min, or non-statistically significant noise / low severity.\n"
            )
        elif case.task_type == "query_classification":
            task_guidelines = (
                "DOMAIN RULES FOR QUERY CLASSIFICATION:\n"
                "- 'checkout_step_2_drop_off_rate': questions about drop-off in checkout, step 2 friction, or delivery fee charges at checkout.\n"
                "- 'cart_abandonment_rate': questions about items added to cart but abandoned before checkout.\n"
                "- 'overall_conversion_rate': questions about store overall conversion rate or visitor-to-order ratio.\n"
                "- 'trial_to_paid_conversion_rate': questions about SaaS trial conversion or subscription upgrades.\n"
                "- 'unsupported': questions unrelated to retail metric telemetry (weather, general trivia, system commands).\n"
            )
        elif case.task_type == "evidence_support":
            task_guidelines = (
                "DOMAIN RULES FOR EVIDENCE SUPPORT:\n"
                "- 'supported': Claim percentage matches the computed metric value (within 1.0%), trend direction matches, and sample is sufficient.\n"
                "- 'hallucinated_number': Stated percentage number in claim differs significantly from the computed metric value.\n"
                "- 'inverted_polarity': Claim asserts an increase when delta was negative, or claims a drop when delta was positive.\n"
                "- 'insufficient_sample': Claim makes definitive conclusion while min_sample_met is false or sample is too low.\n"
            )

        system_prompt = (
            f"You are an expert benchmark classification model evaluating the task: '{case.task_type}'.\n"
            f"{task_guidelines}"
            f"Allowed Options: {json.dumps(case.allowed_options)}\n"
            "RULES:\n"
            "1. You MUST select exactly ONE option strictly from the Allowed Options list.\n"
            "2. Provide your stated probability (confidence) between 0.0 and 1.0.\n"
            "3. Return strictly a JSON object: {\"selected_option\": \"<option>\", \"confidence\": <float>}"
        )

        user_prompt = f"""
Task Description: {case.description}
Input Context:
{json.dumps(case.input_context, indent=2)}

Select option from: {case.allowed_options}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        resp = self.client.chat_completion(messages, json_mode=True, temperature=0.0)
        data = resp.get("json") or {}

        raw_choice = (
            data.get("selected_option")
            or data.get("action_type")
            or data.get("prediction")
            or data.get("option")
            or ""
        )
        selected_clean = str(raw_choice).lower().strip().replace(" ", "_")

        # Match case-insensitively against allowed options
        matched_option = None
        for opt in case.allowed_options:
            if opt.lower() == selected_clean:
                matched_option = opt
                break
        if not matched_option:
            for opt in case.allowed_options:
                if opt.lower() in selected_clean or selected_clean in opt.lower():
                    matched_option = opt
                    break
        if not matched_option:
            matched_option = case.allowed_options[-1]

        confidence = float(data.get("confidence", data.get("confidence_probability", 0.85)))
        confidence = max(0.01, min(0.99, confidence))

        is_correct = (matched_option == case.ground_truth)

        return ProviderPrediction(
            case_id=case.case_id,
            selected_option=matched_option,
            stated_probability=round(confidence, 3),
            is_correct=is_correct,
            latency_ms=round(resp["latency_ms"], 2),
            cost_usd=round(resp["cost_usd"], 6)
        )
