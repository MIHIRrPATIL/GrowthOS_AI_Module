"""
OpenRouter API Client
Provides HTTP client integration with OpenRouter (https://openrouter.ai/api/v1)
supporting chat completions, JSON schema enforcement, token usage tracking, and latency profiling.
"""

from typing import Dict, Any, List, Optional
import os
import time
import json
import re
import httpx


def load_dotenv_if_present() -> None:
    """Zero-dependency loader that searches for .env files in nearby directories."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(current_dir, ".env"),
        os.path.join(os.path.dirname(current_dir), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(current_dir)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), ".env"),
    ]
    for env_path in candidates:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
            except Exception:
                pass
            break


import logging

logger = logging.getLogger(__name__)


class RateLimitCircuitOpenError(RuntimeError):
    """Raised when an API request is attempted while rate limit circuit breaker cooldown is active."""
    pass


class OpenRouterClient:
    """
    Robust HTTP client for interacting with OpenRouter models.
    Supports OpenAI-compatible chat completion endpoints with automatic JSON parsing
    and 429 Circuit Breaker.
    """

    DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
    BASE_URL = "https://openrouter.ai/api/v1"

    # Circuit breaker state shared across client instances
    _circuit_open_until: float = 0.0
    _last_retry_delay: float = 0.0

    # Known cost estimates per 1,000,000 tokens (USD)
    # [prompt_cost, completion_cost]
    MODEL_COSTS = {
        # Free MoE models (>=27B parameters, >=32k context)
        "nvidia/nemotron-3-ultra-550b-a55b:free": (0.0, 0.0),
        "nvidia/nemotron-3-super-120b-a12b:free": (0.0, 0.0),
        "nvidia/nemotron-3.5-lightning:free": (0.0, 0.0),
        "dots-studio/dots-3-note-preview:free": (0.0, 0.0),
        "poolside/laguna-s-2.1:free": (0.0, 0.0),
        "poolside/laguna-xs-2.1:free": (0.0, 0.0),
        "cohere/north-mini-code:free": (0.0, 0.0),
        "inclusionai/ling-3.0-flash-sante:free": (0.0, 0.0),
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": (0.0, 0.0),
        "google/gemma-4-31b-it:free": (0.0, 0.0),
        "google/gemma-4-26b-a4b-it:free": (0.0, 0.0),
        # Frontier commercial models
        "google/gemini-2.5-flash": (0.075, 0.30),
        "google/gemini-2.0-flash-001": (0.10, 0.40),
        "anthropic/claude-3.5-haiku": (0.80, 4.00),
        "anthropic/claude-3.5-sonnet": (3.00, 15.00),
        "meta-llama/llama-3.3-70b-instruct": (0.12, 0.30),
        "openai/gpt-4o-mini": (0.15, 0.60),
        "deepseek/deepseek-chat": (0.14, 0.28)
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 35.0,
        app_name: str = "GrowthOS AI Brain",
        site_url: str = "https://growthos.ai"
    ):
        if api_key is None:
            load_dotenv_if_present()
            self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        else:
            self.api_key = api_key

        if model is None:
            self.model = os.environ.get("OPENROUTER_MODEL", self.DEFAULT_MODEL)
        else:
            self.model = model

        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.app_name = app_name
        self.site_url = site_url

    def is_configured(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured():
            raise ValueError(
                "OPENROUTER_API_KEY is not configured. "
                "Please export OPENROUTER_API_KEY in your environment before invoking real LLM requests."
            )
        return {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

    def get_model_rates(self, model_name: str) -> tuple[float, float]:
        """Resolves prompt and completion token costs per 1,000,000 tokens in USD."""
        base_name = model_name.split(":")[0].strip()
        if model_name in self.MODEL_COSTS:
            return self.MODEL_COSTS[model_name]
        if base_name in self.MODEL_COSTS:
            return self.MODEL_COSTS[base_name]
        for k, v in self.MODEL_COSTS.items():
            if k in model_name:
                return v
        return (0.20, 0.80)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = True,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        override_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a chat completion request to OpenRouter.
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
        model_name = override_model or self.model

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # For free models, configure automatic fallback priority routing
        if ":free" in model_name:
            fallback_candidates = [
                model_name,
                "nvidia/nemotron-3-super-120b-a12b:free",
                "nvidia/nemotron-3.5-lightning:free"
            ]
            payload["models"] = list(dict.fromkeys(fallback_candidates))

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{self.base_url}/chat/completions"

        # Check Circuit Breaker Cooldown
        now_ts = time.time()
        if now_ts < OpenRouterClient._circuit_open_until:
            rem = int(OpenRouterClient._circuit_open_until - now_ts)
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
                    # Fallback if specific model does not support response_format json_object
                    if resp.status_code == 400 and json_mode and "response_format" in resp.text:
                        payload.pop("response_format", None)
                        resp = client.post(endpoint, headers=headers, json=payload)

                    if resp.status_code == 429:
                        delay_secs = 30.0
                        OpenRouterClient._circuit_open_until = time.time() + delay_secs
                        OpenRouterClient._last_retry_delay = delay_secs
                        clean_msg = f"HTTP 429 Too Many Requests. Circuit breaker opened for {int(delay_secs)}s."
                        logger.warning("[OpenRouter Circuit Breaker] %s", clean_msg)
                        raise RateLimitCircuitOpenError(clean_msg)

                    if resp.status_code in (502, 503, 504):
                        last_error = f"HTTP {resp.status_code}: {resp.text.splitlines()[0]}"
                        if attempt < max_attempts - 1:
                            time.sleep(2.0 * (attempt + 1))
                            continue

                    if resp.status_code != 200:
                        first_line = resp.text.splitlines()[0] if resp.text else ""
                        raise RuntimeError(
                            f"OpenRouter API request failed with status {resp.status_code}: {first_line}"
                        )

                    parsed_body = resp.json()
                    # Check for upstream error within 200 OK body
                    if "error" in parsed_body and not parsed_body.get("choices"):
                        err_msg = parsed_body.get("error", {})
                        last_error = f"Upstream error: {err_msg}"
                        if attempt < max_attempts - 1:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        raise RuntimeError(f"OpenRouter response contained error: {err_msg}")

                    data = parsed_body
                    break
                except httpx.RequestError as exc:
                    last_error = str(exc)
                    if attempt < max_attempts - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise RuntimeError(f"OpenRouter network error: {exc}")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if data is None:
            raise RuntimeError(f"OpenRouter request failed after {max_attempts} attempts: {last_error}")

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenRouter response contained no choices: {data}")

        msg_obj = choices[0].get("message", {})
        raw_text = (msg_obj.get("content") or msg_obj.get("reasoning") or "").strip()
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        resolved_model = data.get("model", model_name)

        # Estimate cost
        cost_rates = self.get_model_rates(resolved_model)
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
            "model": resolved_model
        }

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Extracts and parses JSON object from model output, handling potential markdown fences."""
        cleaned = text.strip()
        # Remove markdown code block if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Find outer braces
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = cleaned[start:end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
