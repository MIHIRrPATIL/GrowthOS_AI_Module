"""
Google Gemini API Client
GrowthOS Module 4: AI Growth Brain

Provides direct HTTP client integration with Google AI Studio / Gemini API
(https://generativelanguage.googleapis.com/v1beta)
supporting generateContent, JSON schema enforcement via responseMimeType,
token usage tracking, and latency profiling without external heavyweight SDKs.

Strictly NO emojis used in logs or output.
"""

from typing import Dict, Any, List, Optional
import os
import time
import json
import re
import httpx

import logging

from adapters.openrouter_client import load_dotenv_if_present

logger = logging.getLogger(__name__)


class RateLimitCircuitOpenError(RuntimeError):
    """Raised when an API request is attempted while rate limit circuit breaker cooldown is active."""
    pass


class GeminiClient:
    """
    Direct HTTP client for interacting with Google Gemini models via the Generative Language API.
    Supports system instructions, JSON mode, token tracking, exponential backoff,
    and automatic 429 Circuit Breaker.
    """

    DEFAULT_MODEL = "gemini-3.5-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    # Free tier model pool for automatic quota rotation (100% free tier)
    FREE_TIER_MODEL_POOL = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash"
    ]
    _exhausted_free_models: set = set()

    # Circuit breaker state shared across client instances
    _circuit_open_until: float = 0.0
    _last_retry_delay: float = 0.0

    # Known cost estimates per 1,000,000 tokens (USD)
    # [prompt_cost, completion_cost]
    MODEL_COSTS = {
        "gemini-2.5-flash": (0.075, 0.30),
        "gemini-2.5-flash-lite": (0.0375, 0.15),
        "gemini-2.5-pro": (1.25, 5.00),
        "gemini-2.0-flash": (0.10, 0.40),
        "gemini-2.0-flash-lite": (0.075, 0.30)
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 35.0
    ):
        if api_key is None:
            load_dotenv_if_present()
            self.api_key = (
                os.environ.get("GEMINI_API_KEY", "") or
                os.environ.get("GOOGLE_API_KEY", "")
            ).strip()
        else:
            self.api_key = api_key.strip()

        if model is None:
            self.model = os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL).strip()
        else:
            self.model = model.strip()

        # Normalize model slug (strip 'models/' or 'google/' if passed)
        self.model = self._normalize_model_name(self.model)

        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """Strips OpenRouter or Google prefixes if user specified them."""
        clean = model_name
        if clean.startswith("google/"):
            clean = clean[len("google/"):]
        if clean.startswith("models/"):
            clean = clean[len("models/"):]
        if clean.endswith(":free"):
            clean = clean[:-len(":free")]
        return clean

    def is_configured(self) -> bool:
        """Returns True if a Google API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured():
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

    def get_model_rates(self, model: str) -> tuple[float, float]:
        """Returns (prompt_cost_per_1M, completion_cost_per_1M) in USD."""
        normalized = self._normalize_model_name(model)
        if normalized in self.MODEL_COSTS:
            return self.MODEL_COSTS[normalized]
        for key in sorted(self.MODEL_COSTS.keys(), key=len, reverse=True):
            if normalized.startswith(key):
                return self.MODEL_COSTS[key]
        return (0.075, 0.30)

    def generate_content(
        self,
        contents: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
        override_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a generateContent request to Google's Generative Language API.

        Args:
            contents: List of message content dictionaries formatted for Gemini:
                      [{'role': 'user'|'model', 'parts': [{'text': ...}]}]
            system_instruction: Optional system instruction prompt.
            json_mode: When True, enforces responseMimeType="application/json".
            temperature: Sampling temperature (default 0.0 for deterministic output).
            max_output_tokens: Maximum tokens in generated completion.
            override_model: Optional model override.

        Returns a dict containing:
            - 'text': raw model string
            - 'json': parsed json dict if json_mode and valid, else None
            - 'latency_ms': measured wall-clock roundtrip
            - 'prompt_tokens': int
            - 'completion_tokens': int
            - 'cost_usd': estimated cost in USD
            - 'model': resolved model name
        """
        headers = self._get_headers()
        model_name = self._normalize_model_name(override_model or self.model)

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        endpoint = f"{self.base_url}/models/{model_name}:generateContent"

        # Check Circuit Breaker Cooldown
        now_ts = time.time()
        if now_ts < GeminiClient._circuit_open_until:
            rem = int(GeminiClient._circuit_open_until - now_ts)
            raise RateLimitCircuitOpenError(
                f"Rate limit cooldown active ({rem}s remaining). Skipping provider."
            )

        start_time = time.perf_counter()
        data = None
        last_error = None
        max_attempts = 3

        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(max_attempts):
                try:
                    resp = client.post(endpoint, headers=headers, json=payload)

                    if resp.status_code == 429:
                        delay_secs = 30.0
                        quota_type = "rate_limit_per_minute"
                        try:
                            err_body = resp.json().get("error", {})
                            err_msg = err_body.get("message", "")
                            err_details = err_body.get("details", [])
                            for item in err_details:
                                if "retryDelay" in item:
                                    raw_delay = item["retryDelay"].rstrip("s")
                                    delay_secs = max(1.0, float(raw_delay))
                                    break
                            if delay_secs > 3600 or "daily" in err_msg.lower() or "quota" in err_msg.lower():
                                quota_type = "daily_quota_exhausted"
                        except Exception:
                            pass

                        if quota_type == "daily_quota_exhausted":
                            GeminiClient._exhausted_free_models.add(model_name)
                            # Find next unexhausted free model from pool
                            candidate_model = None
                            for m in GeminiClient.FREE_TIER_MODEL_POOL:
                                if m not in GeminiClient._exhausted_free_models and m != model_name:
                                    candidate_model = m
                                    break
                            if candidate_model and attempt < max_attempts - 1:
                                logger.warning(
                                    "[Free-Tier Pool Rotation] Daily quota exhausted on '%s'. "
                                    "Rotating to free-tier model '%s'...",
                                    model_name, candidate_model
                                )
                                print(f"  [FREE TIER ROTATION] Daily quota exhausted on '{model_name}'. Rotating to '{candidate_model}'...")
                                model_name = candidate_model
                                endpoint = f"{self.base_url}/models/{model_name}:generateContent"
                                continue

                        cooldown_secs = min(delay_secs, 60.0) if quota_type != "daily_quota_exhausted" else min(delay_secs, 300.0)
                        GeminiClient._circuit_open_until = time.time() + cooldown_secs
                        GeminiClient._last_retry_delay = delay_secs
                        clean_msg = f"HTTP 429 [{quota_type}]: retryDelay={delay_secs:.1f}s. Circuit breaker opened for {int(cooldown_secs)}s."
                        logger.warning("[Gemini Circuit Breaker] %s", clean_msg)
                        raise RateLimitCircuitOpenError(clean_msg)

                    if resp.status_code in (502, 503, 504):
                        last_error = f"HTTP {resp.status_code}: {resp.text.splitlines()[0]}"
                        if attempt < max_attempts - 1:
                            time.sleep(2.0 * (attempt + 1))
                            continue

                    if resp.status_code != 200:
                        first_line = resp.text.splitlines()[0] if resp.text else ""
                        raise RuntimeError(
                            f"Google Gemini API request failed with status {resp.status_code}: {first_line}"
                        )

                    parsed_body = resp.json()
                    data = parsed_body
                    # Canary probe succeeded: reset circuit breaker
                    GeminiClient._circuit_open_until = 0.0
                    break
                except httpx.RequestError as exc:
                    last_error = str(exc)
                    if attempt < max_attempts - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise RuntimeError(f"Google Gemini network error: {exc}")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if data is None:
            raise RuntimeError(f"Google Gemini request failed after {max_attempts} attempts: {last_error}")

        candidates = data.get("candidates", [])
        if not candidates:
            # Check for content filter blocks
            prompt_feedback = data.get("promptFeedback", {})
            raise RuntimeError(f"Google Gemini response contained no candidates: {data} (Feedback: {prompt_feedback})")

        candidate = candidates[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        raw_text = "".join(part.get("text", "") for part in content_parts).strip()

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        # Estimate cost
        cost_rates = self.get_model_rates(model_name)
        cost_usd = (prompt_tokens * cost_rates[0] + completion_tokens * cost_rates[1]) / 1_000_000.0

        parsed_json: Optional[Dict[str, Any]] = None
        if json_mode:
            parsed_json = self._extract_json(raw_text)

        return {
            "text": raw_text,
            "json": parsed_json,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "model": model_name
        }

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Extracts and parses JSON object from model output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_substr = cleaned[start:end+1]
            try:
                return json.loads(json_substr)
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
