"""
Loyalty Platform Outbound Adapter (Module 1 Integration)
GrowthOS Module 4: AI Growth Brain

Provides HTTP client for Module 1 Loyalty & Rewards Platform:
- Endpoint: POST /v1/waivers (Delivery fee waivers)
- Endpoint: POST /v1/points (Bonus point grants)
- Endpoint: POST /v1/coupons (Dynamic discount coupons)

Features:
- HMAC-SHA256 request authentication
- Strict idempotency key propagation
- Resilient timeout handling
- In-memory circuit breaker (trips after N consecutive failures)
- Seamless mock/offline mode when no external service is configured

Strictly NO emojis in code, docstrings, or logs.
"""

import hmac
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

from ports.outbound import LoyaltyPort


class HttpLoyaltyAdapter(LoyaltyPort):
    """
    HTTP client adapter for Module 1 Loyalty & Rewards Platform.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_secret: str = "growthos_loyalty_secret_key",
        timeout_seconds: float = 3.0,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_reset_seconds: float = 60.0,
        transport: Optional[httpx.BaseTransport] = None
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_secret = api_secret
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_reset_seconds = circuit_breaker_reset_seconds
        self.transport = transport

        # Circuit breaker state
        self.consecutive_failures = 0
        self.circuit_open_until = 0.0

        # In-memory execution store for local/offline testing
        self.offline_records: Dict[str, Dict[str, Any]] = {}

    def _is_circuit_open(self) -> bool:
        if self.circuit_open_until > 0.0:
            if time.time() < self.circuit_open_until:
                return True
            # Circuit breaker cooldown elapsed -> HALF-OPEN
            self.circuit_open_until = 0.0
            self.consecutive_failures = 0
        return False

    def _record_success(self):
        self.consecutive_failures = 0
        self.circuit_open_until = 0.0

    def _record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.circuit_open_until = time.time() + self.circuit_breaker_reset_seconds

    def _sign_payload(self, body_bytes: bytes, timestamp_str: str) -> str:
        message = f"v1:{timestamp_str}:".encode("utf-8") + body_bytes
        return hmac.new(self.api_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def waive_delivery_fee(
        self,
        customer_id: str,
        fee_amount: float,
        points_deducted: int,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Dispatches POST /v1/waivers to Module 1 Loyalty Platform.
        """
        if self._is_circuit_open():
            raise RuntimeError("Circuit breaker OPEN for Module 1 Loyalty Platform")

        payload = {
            "action": "waive_delivery_fee",
            "customer_id": customer_id,
            "fee_amount": float(fee_amount),
            "points_deducted": int(points_deducted),
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Offline / In-memory execution fallback if no base_url configured
        if not self.base_url:
            if idempotency_key in self.offline_records:
                return self.offline_records[idempotency_key]
            receipt = {
                "status": "success",
                "waiver_id": f"wv_{hashlib.md5(idempotency_key.encode()).hexdigest()[:12]}",
                "customer_id": customer_id,
                "fee_amount": fee_amount,
                "points_deducted": points_deducted,
                "idempotency_key": idempotency_key,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            self.offline_records[idempotency_key] = receipt
            return receipt

        # Live HTTP dispatch
        url = f"{self.base_url}/v1/waivers"
        body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ts = str(int(time.time()))
        signature = self._sign_payload(body_bytes, ts)

        headers = {
            "Content-Type": "application/json",
            "X-GrowthOS-Signature": signature,
            "X-GrowthOS-Timestamp": ts,
            "X-Idempotency-Key": idempotency_key
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                resp = client.post(url, content=body_bytes, headers=headers)
                if resp.status_code in (200, 201):
                    self._record_success()
                    return resp.json()
                elif resp.status_code == 409:
                    # Idempotent re-submission
                    self._record_success()
                    return resp.json()
                else:
                    self._record_failure()
                    raise RuntimeError(f"Module 1 HTTP {resp.status_code}: {resp.text}")
        except httpx.TimeoutException as te:
            self._record_failure()
            raise TimeoutError(f"Module 1 request timed out after {self.timeout_seconds}s") from te
        except Exception as ex:
            self._record_failure()
            raise

    def grant_bonus_points(
        self,
        customer_id: str,
        points: int,
        reason: str,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Dispatches POST /v1/points to Module 1 Loyalty Platform.
        """
        if self._is_circuit_open():
            raise RuntimeError("Circuit breaker OPEN for Module 1 Loyalty Platform")

        payload = {
            "action": "grant_bonus_points",
            "customer_id": customer_id,
            "points": int(points),
            "reason": reason,
            "idempotency_key": idempotency_key
        }

        if not self.base_url:
            if idempotency_key in self.offline_records:
                return self.offline_records[idempotency_key]
            receipt = {
                "status": "success",
                "points_granted": points,
                "customer_id": customer_id,
                "idempotency_key": idempotency_key,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            self.offline_records[idempotency_key] = receipt
            return receipt

        url = f"{self.base_url}/v1/points"
        body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ts = str(int(time.time()))
        signature = self._sign_payload(body_bytes, ts)
        headers = {
            "Content-Type": "application/json",
            "X-GrowthOS-Signature": signature,
            "X-GrowthOS-Timestamp": ts,
            "X-Idempotency-Key": idempotency_key
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                resp = client.post(url, content=body_bytes, headers=headers)
                if resp.status_code in (200, 201, 409):
                    self._record_success()
                    return resp.json()
                else:
                    self._record_failure()
                    raise RuntimeError(f"Module 1 HTTP {resp.status_code}: {resp.text}")
        except httpx.TimeoutException as te:
            self._record_failure()
            raise TimeoutError(f"Module 1 timeout: {te}") from te
        except Exception:
            self._record_failure()
            raise

    def issue_discount_coupon(
        self,
        customer_id: str,
        coupon_code: str,
        discount_amount: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Dispatches POST /v1/coupons to Module 1 Loyalty Platform.
        """
        if self._is_circuit_open():
            raise RuntimeError("Circuit breaker OPEN for Module 1 Loyalty Platform")

        payload = {
            "action": "issue_discount_coupon",
            "customer_id": customer_id,
            "coupon_code": coupon_code,
            "discount_amount": float(discount_amount),
            "idempotency_key": idempotency_key
        }

        if not self.base_url:
            if idempotency_key in self.offline_records:
                return self.offline_records[idempotency_key]
            receipt = {
                "status": "success",
                "coupon_code": coupon_code,
                "discount_amount": discount_amount,
                "customer_id": customer_id,
                "idempotency_key": idempotency_key,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            self.offline_records[idempotency_key] = receipt
            return receipt

        url = f"{self.base_url}/v1/coupons"
        body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ts = str(int(time.time()))
        signature = self._sign_payload(body_bytes, ts)
        headers = {
            "Content-Type": "application/json",
            "X-GrowthOS-Signature": signature,
            "X-GrowthOS-Timestamp": ts,
            "X-Idempotency-Key": idempotency_key
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                resp = client.post(url, content=body_bytes, headers=headers)
                if resp.status_code in (200, 201, 409):
                    self._record_success()
                    return resp.json()
                else:
                    self._record_failure()
                    raise RuntimeError(f"Module 1 HTTP {resp.status_code}: {resp.text}")
        except httpx.TimeoutException as te:
            self._record_failure()
            raise TimeoutError(f"Module 1 timeout: {te}") from te
        except Exception:
            self._record_failure()
            raise
