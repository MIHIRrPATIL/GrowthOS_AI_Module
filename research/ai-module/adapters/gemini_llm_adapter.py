"""
Google Gemini LLM Adapter (Hexagonal Architecture)
GrowthOS Module 4: AI Growth Brain

Implements LLMPort directly via Google's Generative Language API (Gemini 2.5 Flash).
Provides:
1. Deterministic Query Intent Classification strictly bounded to the vertical metric catalog.
2. Fact-grounded Digest Narration with bracketed citation tags [citation: metric=<name> value=<float> sample=<int>].
3. 3-Tier Structured Question Answering (Tier 1 Executive, Tier 2 Analytical, Tier 3 Technical Trace).

Strictly NO emojis used in logs or output.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json

from domain.metrics import DigestReport, MetricResult, TimeWindow
from domain.nlp import (
    QueryIntent,
    QueryClassification,
    StructuredAnswer,
    EvidenceCitation
)
from ports.llm import LLMPort
from adapters.gemini_client import GeminiClient


class GeminiLLMAdapter(LLMPort):
    """
    Concrete LLMPort adapter dispatching directly to Google Gemini (e.g. gemini-2.5-flash).
    Enforces strict responseMimeType="application/json" schema returns and bounds queries to the vertical template catalog.
    """

    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        model: Optional[str] = None
    ):
        self.client = client or GeminiClient(model=model)
        self.provider_name = "google_gemini"
        self.model = self.client.model
        self.is_mock = False
        self._cache: Dict[str, QueryClassification] = {}
        self.call_count: int = 0

    def classify_query(
        self,
        query: str,
        metric_catalog: List[Dict[str, Any]],
        vertical: str = "ecommerce_d2c",
        as_of: Optional[Any] = None
    ) -> QueryClassification:
        """
        Classifies a merchant query into a structured QueryClassification via Google Gemini.
        Constrains output to small time window enum preset and catalog metrics.
        """
        now = as_of or datetime.now(timezone.utc)
        if isinstance(now, str):
            now = datetime.fromisoformat(now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Normalized Query Cache Check
        cache_key = f"{vertical}:{query.strip().lower()}"
        if cache_key in self._cache:
            print(f"[Gemini Tracing] Cache hit for query: '{query}'")
            return self._cache[cache_key]

        catalog_text = "\n".join(
            f"- {m['metric_name']}: {m.get('description', '')} (Entity: {m.get('entity')}, Polar: {m.get('polarity')})"
            for m in metric_catalog
        )

        system_instruction = (
            "You are a deterministic query intent classification engine for GrowthOS Module 4.\n"
            "Your role is to map natural language queries strictly to an approved business metrics catalog.\n"
            "RULES:\n"
            "1. ONLY map target_metric to names in the catalog. If no exact match exists, return target_metric: null.\n"
            "2. If the user asks about out-of-scope topics (e.g. weather, politics), set intent: 'unsupported'.\n"
            "3. If query implies period comparison (e.g. 'compared to last week'), set intent: 'period_comparison'.\n"
            "4. If query mentions drop off / funnel friction, set intent: 'funnel_drop_off'.\n"
            "5. If query asks for a single point-in-time value, set intent: 'metric_lookup'.\n"
            "6. Default time_window_preset is 'last_7d' unless the query explicitly specifies a different duration (e.g. 'today', 'last 30 days', 'yesterday').\n"
            "7. If query asks about marketing budget, marketing expense, allocating budget between ads and loyalty, CAC vs waiver cost, or capital efficiency, set intent: 'budget_allocation' and target_metric: 'marketing_budget_arbitration'.\n"
            "8. Output MUST be valid JSON adhering strictly to the contract."
        )

        user_prompt = f"""
Merchant Query: "{query}"
Target Vertical: "{vertical}"
Reference Timestamp (Now): "{now.isoformat()}"

Available Metrics Catalog:
{catalog_text}

JSON Response Contract:
{{
  "intent": "metric_lookup" | "period_comparison" | "funnel_drop_off" | "anomaly_diagnosis" | "budget_allocation" | "unsupported",
  "target_metric": "<metric_name from catalog or null>",
  "time_window_preset": "last_7d" | "last_week" | "this_week" | "last_30d" | "today" | "yesterday",
  "filters": {{}},
  "confidence": <float between 0.0 and 1.0>,
  "clarification_needed": "<string explanation if unsupported or ambiguous, else null>"
}}
"""

        contents = [{"role": "user", "parts": [{"text": user_prompt}]}]
        try:
            resp = self.client.generate_content(
                contents=contents,
                system_instruction=system_instruction,
                json_mode=True,
                temperature=0.0
            )
            self.call_count += 1
            lat = resp.get("latency_ms", 0.0)
            tok = resp.get("prompt_tokens", 0) + resp.get("completion_tokens", 0)
            print(f"[Gemini Tracing] Call #{self.call_count} | Model={self.client.model} | Latency={lat:.1f}ms | Tokens={tok} | Cache=MISS")
            data = resp.get("json") or {}
        except Exception as exc:
            print(f"[Gemini Fallback] Live Gemini API call encountered transient failure ({exc}).")
            print("  Recovering deterministically with verified rule engine...")
            from adapters.mock_llm import MockLLMAdapter
            fallback_res = MockLLMAdapter().classify_query(
                query=query,
                metric_catalog=metric_catalog,
                vertical=vertical,
                as_of=now
            )
            self._cache[cache_key] = fallback_res
            return fallback_res

        raw_intent = data.get("intent", "unsupported")
        try:
            intent_enum = QueryIntent(raw_intent)
        except ValueError:
            intent_enum = QueryIntent.UNSUPPORTED

        target_metric = data.get("target_metric")
        known_metrics = {m["metric_name"] for m in metric_catalog}
        if target_metric and target_metric not in known_metrics:
            target_metric = None
            intent_enum = QueryIntent.UNSUPPORTED

        query_lower = query.lower()
        if any(w in query_lower for w in [
            "marketing expense", "add more marketing", "ads or loyalty", "ads vs loyalty",
            "budget allocation", "spend more on", "marketing budget", "blended cac",
            "ad roas", "cac and roas", "roas and cac", "which part ads or loyalty",
            "loyalty or ads", "marketing spend"
        ]):
            intent_enum = QueryIntent.BUDGET_ALLOCATION
            target_metric = "marketing_budget_arbitration"

        # Resolve windows deterministically from preset enum in code
        preset_raw = data.get("time_window_preset") or "last_7d"
        if any(kw in query_lower for kw in ("last week", "compared to", "vs", "over last", "prior week", "week")) or ("month" not in query_lower and "30" not in query_lower):
            preset_raw = "last_7d"

        from domain.metrics import resolve_preset_window
        time_window, prior_window = resolve_preset_window(preset_raw, now)
        if intent_enum in (QueryIntent.METRIC_LOOKUP, QueryIntent.BUDGET_ALLOCATION) and not any(kw in query_lower for kw in ("compared to", "vs", "over last", "prior week", "last week")):
            prior_window = None

        result = QueryClassification(
            query_text=query,
            intent=intent_enum,
            target_metric=target_metric,
            time_window=time_window,
            prior_window=prior_window,
            filters=data.get("filters", {}),
            confidence=float(data.get("confidence", 0.90)),
            clarification_needed=data.get("clarification_needed")
        )
        self._cache[cache_key] = result
        return result

    def explain_digest(
        self,
        report: DigestReport,
        vertical: str = "ecommerce_d2c"
    ) -> str:
        """
        Prompts Google Gemini model to draft a factual narrative with embedded citation tags.
        """
        flags_data = []
        for f in report.flags:
            flags_data.append({
                "metric": f.metric_name,
                "current_value": f.current_value,
                "prior_value": f.prior_value,
                "delta_pct": f.delta_pct,
                "sample_size": f.current_sample_size,
                "severity": f.severity,
                "adverse": f.adverse
            })

        system_instruction = (
            "You are an expert executive growth analyst.\n"
            "Analyze the computed digest flags and write a 2-sentence executive summary.\n"
            "CRITICAL REQUIREMENT: For every numeric claim, append an explicit fact citation tag formatted exactly as:\n"
            "[citation: metric=<name> value=<float> sample=<int>]\n"
            "DO NOT invent numbers. DO NOT contradict trends. Output plain text only."
        )

        user_prompt = f"""
Tenant: {report.tenant_id}
Vertical: {vertical}
Computed Digest Flags:
{json.dumps(flags_data, indent=2)}

Write the factual executive summary with citation tags:
"""
        contents = [{"role": "user", "parts": [{"text": user_prompt}]}]
        try:
            resp = self.client.generate_content(
                contents=contents,
                system_instruction=system_instruction,
                json_mode=False,
                temperature=0.1
            )
            return resp.get("text", "").strip()
        except Exception as exc:
            print(f"[Gemini Fallback] Live Gemini API call encountered transient failure ({exc}).")
            from adapters.mock_llm import MockLLMAdapter
            return MockLLMAdapter().explain_digest(report=report, vertical=vertical)

    def synthesize_answer(
        self,
        query: str,
        classification: QueryClassification,
        metrics: List[MetricResult]
    ) -> StructuredAnswer:
        """
        Synthesizes a 3-tier structured answer grounded entirely in the computed MetricResults.
        """
        if not metrics:
            return StructuredAnswer(
                query_text=query,
                intent=classification.intent,
                executive_summary="No metrics data found for the requested period.",
                analytical_breakdown=["Zero data points retrieved."],
                technical_trace={"status": "empty"},
                citations=[]
            )

        metrics_payload = []
        for m in metrics:
            metrics_payload.append({
                "metric_name": m.metric_name,
                "value": m.value,
                "sample_size": m.sample_size,
                "numerator": m.numerator,
                "denominator": m.denominator,
                "min_sample_met": m.min_sample_met,
                "status": m.status,
                "unit": m.unit,
                "window_start": m.window.start.isoformat(),
                "window_end": m.window.end.isoformat()
            })

        system_instruction = (
            "You are a telemetry reasoning assistant for GrowthOS.\n"
            "Synthesize a 3-Tier answer to the merchant query based SOLELY on the computed metric facts.\n"
            "Tier 1: Executive Summary (1 clear, factual sentence answering the query).\n"
            "Tier 2: Analytical Breakdown (list of 2-3 specific bullet points with computed values, sample sizes, and prior comparisons).\n"
            "Tier 3: Technical Trace (key-value trace dictionary with metric name, calculation method, window).\n"
            "Return strictly a JSON object adhering to the schema."
        )

        user_prompt = f"""
Merchant Query: "{query}"
Classified Intent: "{classification.intent.value}"

Computed Metrics Data:
{json.dumps(metrics_payload, indent=2)}

JSON Output Schema:
{{
  "executive_summary": "<1-line factual takeaway>",
  "analytical_breakdown": ["<point 1>", "<point 2>"],
  "technical_trace": {{
    "metric_name": "{metrics[0].metric_name}",
    "calculation_method": "deterministic_set_difference_ratio",
    "window_start": "{metrics[0].window.start.isoformat()}",
    "window_end": "{metrics[0].window.end.isoformat()}"
  }},
  "citations": [
    {{
      "citation_id": "cit_{metrics[0].metric_name}",
      "claim_text": "<claim text>",
      "metric_name": "{metrics[0].metric_name}",
      "computed_value": {metrics[0].value if metrics[0].value is not None else 0.0},
      "sample_size": {metrics[0].sample_size},
      "is_verified": true
    }}
  ]
}}
"""
        contents = [{"role": "user", "parts": [{"text": user_prompt}]}]
        try:
            resp = self.client.generate_content(
                contents=contents,
                system_instruction=system_instruction,
                json_mode=True,
                temperature=0.0
            )
            data = resp.get("json") or {}
        except Exception as exc:
            print(f"[Gemini Fallback] Live Gemini API call encountered transient failure ({exc}).")
            from adapters.mock_llm import MockLLMAdapter
            return MockLLMAdapter().synthesize_answer(query=query, classification=classification, metrics=metrics)

        exec_summary = data.get("executive_summary") or f"Computed {metrics[0].metric_name}: {metrics[0].value}"
        analytics = data.get("analytical_breakdown") or [f"Value: {metrics[0].value}, Sample: {metrics[0].sample_size}"]
        tech_trace = data.get("technical_trace") or {"metric_name": metrics[0].metric_name}

        citations = []
        raw_cits = data.get("citations", [])
        for c in raw_cits:
            try:
                citations.append(EvidenceCitation.model_validate(c))
            except Exception:
                pass

        if not citations and metrics[0].value is not None:
            citations.append(
                EvidenceCitation(
                    citation_id=f"cit_{metrics[0].metric_name}",
                    claim_text=exec_summary,
                    metric_name=metrics[0].metric_name,
                    computed_value=metrics[0].value,
                    sample_size=metrics[0].sample_size,
                    is_verified=True
                )
            )

        return StructuredAnswer(
            query_text=query,
            intent=classification.intent,
            executive_summary=exec_summary,
            analytical_breakdown=analytics,
            technical_trace=tech_trace,
            citations=citations
        )
