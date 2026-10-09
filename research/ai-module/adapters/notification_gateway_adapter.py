"""
Notification Gateway Outbound Adapter (WhatsApp & Messaging)
GrowthOS Module 4: AI Growth Brain

Provides HTTP client for external Notification Gateway (WhatsApp, SMS, Email):
- Endpoint: POST /v1/whatsapp (WhatsApp template messaging)
- Endpoint: POST /v1/messages (Omnichannel notifications)

Features:
- DPDP compliance: SHA-256 recipient phone hashing in logs
- HMAC-SHA256 request authentication
- Strict idempotency key propagation
- Resilient timeout handling
- In-memory circuit breaker (trips after N consecutive failures)
- Seamless mock/offline execution when no gateway URL is configured
"""

import hmac
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

from ports.outbound import NotificationPort


class HttpNotificationGatewayAdapter(NotificationPort):
    """
    HTTP client adapter for Notification Gateway.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_secret: str = "growthos_notification_secret_key",
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

        # Offline / in-memory execution records
        self.offline_records: Dict[str, Dict[str, Any]] = {}

    def _is_circuit_open(self) -> bool:
        if self.circuit_open_until > 0.0:
            if time.time() < self.circuit_open_until:
                return True
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

    def _hash_recipient(self, recipient: str) -> str:
        return hashlib.sha256(recipient.encode("utf-8")).hexdigest()[:16]

    def _sign_payload(self, body_bytes: bytes, timestamp_str: str) -> str:
        message = f"v1:{timestamp_str}:".encode("utf-8") + body_bytes
        return hmac.new(self.api_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def send_recovery_message(
        self,
        recipient: str,
        channel: str,
        template_name: str,
        parameters: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Dispatches recovery message via POST /v1/whatsapp or POST /v1/messages.
        """
        if self._is_circuit_open():
            raise RuntimeError("Circuit breaker OPEN for Notification Gateway")

        masked_recipient = f"***{recipient[-4:]}" if len(recipient) >= 4 else "***"
        recipient_hash = self._hash_recipient(recipient)

        payload = {
            "channel": channel,
            "recipient": recipient,
            "recipient_hash": recipient_hash,
            "template_name": template_name,
            "parameters": parameters,
            "idempotency_key": idempotency_key,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }

        # Offline execution mode
        if not self.base_url:
            if idempotency_key in self.offline_records:
                return self.offline_records[idempotency_key]
            receipt = {
                "status": "delivered",
                "message_id": f"msg_{hashlib.md5(idempotency_key.encode()).hexdigest()[:12]}",
                "channel": channel,
                "recipient_masked": masked_recipient,
                "recipient_hash": recipient_hash,
                "template_name": template_name,
                "idempotency_key": idempotency_key,
                "delivered_at": datetime.now(timezone.utc).isoformat()
            }
            self.offline_records[idempotency_key] = receipt
            return receipt

        # Live HTTP dispatch
        endpoint = "/v1/whatsapp" if channel.lower() == "whatsapp" else "/v1/messages"
        url = f"{self.base_url}{endpoint}"
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
                if resp.status_code in (200, 201, 202, 409):
                    self._record_success()
                    return resp.json()
                else:
                    self._record_failure()
                    raise RuntimeError(f"Notification Gateway HTTP {resp.status_code}: {resp.text}")
        except httpx.TimeoutException as te:
            self._record_failure()
            raise TimeoutError(f"Notification Gateway timeout after {self.timeout_seconds}s") from te
        except Exception:
            self._record_failure()
            raise
