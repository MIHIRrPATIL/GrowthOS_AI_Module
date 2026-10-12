"""
HTTP Inbound Telemetry Adapter (Module 2 to Module 4 Bridge)
GrowthOS Module 4: AI Growth Brain

Exposes POST /v1/telemetry/events conforming to proposed OpenAPI contract:
- HMAC-SHA256 signature verification (X-GrowthOS-Signature)
- Anti-replay timestamp drift protection (X-GrowthOS-Timestamp < 300s)
- Batch schema validation with mandatory client event_id
- Multi-status batch processing (200 OK, 207 Multi-Status, 401 Unauthorized, 422 Unprocessable Entity)
- Idempotent deduplication and identity resolution via EventIngestionService

Zero external web framework dependencies (standard library + Pydantic + WSGI compliant).
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
import json
import hmac
import hashlib
from datetime import datetime, timezone
import logging

from pydantic import BaseModel, Field, ConfigDict, ValidationError

from domain.events import EventEnvelope, PageMetadata, UTMMetadata, DeviceMetadata, NetworkMetadata, ConsentState
from services.ingestion_service import EventIngestionService

logger = logging.getLogger(__name__)


# ==============================================================================
# Helper Functions for HMAC Signature & Anti-Replay Verification
# ==============================================================================

def generate_hmac_signature(payload_bytes: bytes, timestamp_str: str, secret_key: str) -> str:
    """
    Computes an HMAC-SHA256 signature over timestamp and payload body.
    Format: v1=<hex_digest>
    """
    signed_data = f"{timestamp_str}.".encode("utf-8") + payload_bytes
    digest = hmac.new(secret_key.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def verify_hmac_signature(
    payload_bytes: bytes,
    signature_header: str,
    timestamp_header: str,
    secret_key: str,
    max_drift_seconds: float = 300.0,
    current_time: Optional[datetime] = None
) -> Tuple[bool, Optional[str]]:
    """
    Verifies the HMAC-SHA256 signature and validates timestamp drift for replay attack prevention.

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not timestamp_header:
        return False, "Missing X-GrowthOS-Timestamp header"
    if not signature_header:
        return False, "Missing X-GrowthOS-Signature header"

    # 1. Anti-Replay: Verify timestamp drift
    try:
        # Handle ISO-8601 string or numeric epoch seconds
        if timestamp_header.replace(".", "", 1).isdigit():
            ts_dt = datetime.fromtimestamp(float(timestamp_header), tz=timezone.utc)
        else:
            ts_dt = datetime.fromisoformat(timestamp_header.replace("Z", "+00:00"))
    except Exception:
        return False, f"Invalid X-GrowthOS-Timestamp format: '{timestamp_header}'"

    now = current_time or datetime.now(timezone.utc)
    drift = abs((now - ts_dt).total_seconds())
    if drift > max_drift_seconds:
        return False, f"Timestamp drift exceeds {int(max_drift_seconds)} seconds (drift={drift:.1f}s, replay protection)"

    # 2. Verify HMAC Signature
    expected_full = generate_hmac_signature(payload_bytes, timestamp_header, secret_key)
    expected_raw = expected_full.replace("v1=", "")

    # Compare with both v1=<hex> and raw <hex>
    clean_sig = signature_header.strip()
    match_v1 = hmac.compare_digest(clean_sig, expected_full)
    match_raw = hmac.compare_digest(clean_sig, expected_raw)

    if not (match_v1 or match_raw):
        return False, "Invalid HMAC signature"

    return True, None


def generate_ephemeral_client_token(
    tenant_id: str,
    session_id: str,
    secret_key: str,
    ttl_seconds: int = 3600,
    current_time: Optional[datetime] = None
) -> str:
    """
    Generates a short-lived token that a merchant's backend server can issue to a client browser.
    Allows the browser to authenticate telemetry batches without exposing the secret key.
    Format: <tenant_id>:<session_id>:<expiry_epoch>:<hmac_signature>
    """
    now = current_time or datetime.now(timezone.utc)
    expiry = int(now.timestamp()) + ttl_seconds
    token_body = f"{tenant_id}:{session_id}:{expiry}"
    digest = hmac.new(secret_key.encode("utf-8"), token_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{token_body}:{digest}"


def verify_ephemeral_client_token(
    token: str,
    tenant_id: str,
    secret_key: str,
    session_id: Optional[str] = None,
    current_time: Optional[datetime] = None
) -> Tuple[bool, Optional[str]]:
    """
    Verifies an ephemeral client session token.
    Checks signature, expiry, tenant matching, and optional session binding.
    """
    parts = token.strip().split(":")
    if len(parts) != 4:
        return False, "Invalid token format (expected tenant:session:expiry:signature)"

    tok_tenant, tok_session, tok_expiry_str, tok_sig = parts
    if tok_tenant != tenant_id:
        return False, f"Token tenant '{tok_tenant}' does not match request tenant '{tenant_id}'"

    if session_id and tok_session != session_id:
        return False, f"Token session '{tok_session}' does not match batch session '{session_id}'"

    try:
        expiry = int(tok_expiry_str)
    except ValueError:
        return False, "Invalid token expiry format"

    now = current_time or datetime.now(timezone.utc)
    if now.timestamp() > expiry:
        return False, "Ephemeral client token has expired"

    token_body = f"{tok_tenant}:{tok_session}:{tok_expiry_str}"
    expected_digest = hmac.new(secret_key.encode("utf-8"), token_body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(tok_sig, expected_digest):
        return False, "Invalid token signature"

    return True, None


# ==============================================================================
# Pydantic Schemas for Inbound Telemetry Payload
# ==============================================================================

class InboundEventItem(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event_id: str = Field(..., description="Client-generated unique UUID (required for deduplication)")
    session_id: str = Field(..., description="Active session identifier")
    event_name: str = Field(..., description="Canonical event name")
    
    timestamp: Optional[str] = Field(default=None, alias="occurred_at")
    anonymous_id: Optional[str] = Field(default=None)
    customer_id: Optional[str] = Field(default=None)
    
    properties: Dict[str, Any] = Field(default_factory=dict)
    page: Optional[Dict[str, Any]] = None
    utm: Optional[Dict[str, Any]] = None
    device: Optional[Dict[str, Any]] = None
    network: Optional[Dict[str, Any]] = None
    consent: Optional[Dict[str, Any]] = None


class InboundBatchPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    batch_id: str = Field(..., description="Unique client batch identifier")
    sent_at: Optional[str] = Field(default=None)
    schema_version: str = Field(default="1.2.0")
    consent: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"analytics": True, "marketing": True})
    events: List[Dict[str, Any]] = Field(..., description="List of raw event items")


# ==============================================================================
# HTTP Inbound Telemetry Adapter
# ==============================================================================

class HttpTelemetryAdapter:
    """
    HTTP Inbound Adapter for receiving and validating batch telemetry from Module 2 Behavior SDK.
    Supports standalone handling, WSGI embedding, HMAC signing, and partial batch returns.
    """

    SUPPORTED_PATHS = {
        "/v1/telemetry/events",
        "/telemetry/events",
        "/api/v1/telemetry/events"
    }

    def __init__(
        self,
        ingestion_service: EventIngestionService,
        tenant_secrets: Optional[Dict[str, str]] = None,
        default_secret: str = "growthos_telemetry_secret_v1",
        max_drift_seconds: float = 300.0,
        enforce_signatures: bool = True
    ):
        self.ingestion_service = ingestion_service
        self.tenant_secrets = tenant_secrets or {}
        self.default_secret = default_secret
        self.max_drift_seconds = max_drift_seconds
        self.enforce_signatures = enforce_signatures

    def get_tenant_secret(self, tenant_id: str) -> str:
        return self.tenant_secrets.get(tenant_id, self.default_secret)

    def handle_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        current_time: Optional[datetime] = None
    ) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """
        Pure HTTP request dispatcher.
        
        Args:
            method: HTTP verb (e.g. POST, GET)
            path: Target request path (e.g. /v1/telemetry/events)
            headers: Normalized headers dictionary (case-insensitive keys)
            body_bytes: Raw request body
            current_time: Optional override for time verification in tests

        Returns:
            (status_code: int, response_headers: dict, response_json: dict)
        """
        resp_headers = {"Content-Type": "application/json"}
        norm_headers = {k.lower(): v for k, v in headers.items()}

        # 1. Health check endpoint
        if method == "GET" and path in ("/health", "/v1/health"):
            return 200, resp_headers, {
                "status": "healthy",
                "service": "growthos-telemetry-ingest",
                "version": "1.2.0"
            }

        # 2. Path routing
        clean_path = path.rstrip("/")
        if clean_path not in self.SUPPORTED_PATHS:
            return 404, resp_headers, {
                "error": "Not Found",
                "message": f"Endpoint '{path}' not recognized. Use POST /v1/telemetry/events."
            }

        if method != "POST":
            return 405, resp_headers, {
                "error": "Method Not Allowed",
                "message": f"HTTP method '{method}' is not allowed on '{path}'. Use POST."
            }

        # 3. Tenant Identification
        tenant_id = norm_headers.get("x-tenant-id", "").strip()
        if not tenant_id:
            return 400, resp_headers, {
                "error": "Missing X-Tenant-ID",
                "message": "Header 'X-Tenant-ID' is required for all telemetry ingestion."
            }

        # 4. Ingestion Authentication: Server-to-Server HMAC OR Ephemeral Client Session Token
        if self.enforce_signatures:
            sig_header = norm_headers.get("x-growthos-signature", "").strip()
            ts_header = norm_headers.get("x-growthos-timestamp", "").strip()
            auth_header = norm_headers.get("authorization", "").strip()
            session_tok_header = norm_headers.get("x-growthos-session-token", "").strip()
            secret_key = self.get_tenant_secret(tenant_id)

            authenticated = False
            auth_error = None

            # Path A: First-Party Reverse Proxy / Server-to-Server HMAC Signature
            if sig_header and ts_header:
                is_valid, sig_err = verify_hmac_signature(
                    payload_bytes=body_bytes,
                    signature_header=sig_header,
                    timestamp_header=ts_header,
                    secret_key=secret_key,
                    max_drift_seconds=self.max_drift_seconds,
                    current_time=current_time
                )
                if is_valid:
                    authenticated = True
                else:
                    auth_error = sig_err

            # Path B: Direct Browser Ingestion via Ephemeral Session Token (no shared secret exposed)
            client_token = session_tok_header
            if not client_token and auth_header.startswith("Bearer "):
                client_token = auth_header[7:].strip()

            if not authenticated and client_token:
                is_valid, tok_err = verify_ephemeral_client_token(
                    token=client_token,
                    tenant_id=tenant_id,
                    secret_key=secret_key,
                    current_time=current_time
                )
                if is_valid:
                    authenticated = True
                    auth_error = None
                else:
                    auth_error = tok_err

            if not authenticated:
                return 401, resp_headers, {
                    "error": "Unauthorized",
                    "message": auth_error or "Authentication failed: Missing or invalid signature/token"
                }

        # 5. Payload JSON Parsing
        try:
            raw_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            return 400, resp_headers, {
                "error": "Malformed JSON",
                "message": f"Could not parse request body as JSON: {str(e)}"
            }

        try:
            batch = InboundBatchPayload.model_validate(raw_data)
        except ValidationError as val_err:
            return 422, resp_headers, {
                "error": "Unprocessable Entity",
                "message": "Batch payload failed schema validation",
                "details": val_err.errors()
            }

        # 6. Global Batch Consent Verification (DPDP / GDPR Guardrail)
        batch_consent = batch.consent or {}
        if batch_consent.get("analytics") is False:
            return 200, resp_headers, {
                "status": "dropped_by_consent",
                "batch_id": batch.batch_id,
                "tenant_id": tenant_id,
                "total_received": len(batch.events),
                "accepted": 0,
                "rejected": len(batch.events),
                "errors": [{"reason": "CONSENT_REVOKED", "message": "Analytics consent is false for this batch."}]
            }

        if not batch.events:
            return 200, resp_headers, {
                "status": "empty_batch",
                "batch_id": batch.batch_id,
                "tenant_id": tenant_id,
                "total_received": 0,
                "accepted": 0,
                "rejected": 0,
                "errors": []
            }

        # 7. Item-by-item Processing & Partial Batch Tracking
        accepted_envelopes: List[EventEnvelope] = []
        rejected_items: List[Dict[str, Any]] = []

        now_iso = (current_time or datetime.now(timezone.utc)).isoformat()

        for idx, item in enumerate(batch.events):
            if not isinstance(item, dict):
                rejected_items.append({
                    "index": idx,
                    "reason": "INVALID_ITEM_TYPE",
                    "message": "Event item must be a JSON object"
                })
                continue

            # Validate mandatory event identity fields
            event_id = str(item.get("event_id") or "").strip()
            session_id = str(item.get("session_id") or "").strip()
            event_name = str(item.get("event_name") or "").strip()

            if not event_id:
                rejected_items.append({
                    "index": idx,
                    "reason": "MISSING_EVENT_ID",
                    "message": "Field 'event_id' is required for idempotent deduplication"
                })
                continue

            if not session_id:
                rejected_items.append({
                    "index": idx,
                    "event_id": event_id,
                    "reason": "MISSING_SESSION_ID",
                    "message": "Field 'session_id' is required"
                })
                continue

            if not event_name:
                rejected_items.append({
                    "index": idx,
                    "event_id": event_id,
                    "reason": "MISSING_EVENT_NAME",
                    "message": "Field 'event_name' is required"
                })
                continue

            # Construct canonical EventEnvelope
            try:
                occurred_at = item.get("timestamp") or item.get("occurred_at") or now_iso
                envelope = EventEnvelope(
                    tenant_id=tenant_id,
                    event_id=event_id,
                    schema_version=batch.schema_version,
                    source_module="module_2_sdk",
                    event_name=event_name,
                    occurred_at=occurred_at,
                    received_at=now_iso,
                    session_id=session_id,
                    anonymous_id=item.get("anonymous_id") or f"anon_{session_id[:16]}",
                    customer_id=item.get("customer_id"),
                    properties=item.get("properties") or {},
                    page=PageMetadata(**(item.get("page") or {})),
                    utm=UTMMetadata(**(item.get("utm") or {})),
                    device=DeviceMetadata(**(item.get("device") or {})),
                    network=NetworkMetadata(**(item.get("network") or {})),
                    consent=ConsentState(**(item.get("consent") or batch_consent))
                )
                accepted_envelopes.append(envelope)
            except Exception as env_err:
                rejected_items.append({
                    "index": idx,
                    "event_id": event_id,
                    "reason": "ENVELOPE_VALIDATION_ERROR",
                    "message": str(env_err)
                })

        # 8. Persist Accepted Events via Ingestion Service
        ingestion_stats = {"inserted": 0, "deduplicated": 0}
        if accepted_envelopes:
            batch_result = self.ingestion_service.ingest_batch(accepted_envelopes)
            ingestion_stats["inserted"] = batch_result.get("inserted_count", 0)
            ingestion_stats["deduplicated"] = batch_result.get("deduplicated_count", 0)

        # 9. Formulate Multi-Status HTTP Response Contract
        total_received = len(batch.events)
        total_accepted = len(accepted_envelopes)
        total_rejected = len(rejected_items)

        response_body = {
            "batch_id": batch.batch_id,
            "tenant_id": tenant_id,
            "total_received": total_received,
            "accepted": total_accepted,
            "inserted": ingestion_stats["inserted"],
            "deduplicated": ingestion_stats["deduplicated"],
            "rejected": total_rejected,
            "errors": rejected_items
        }

        if total_rejected == 0:
            response_body["status"] = "success"
            return 200, resp_headers, response_body
        elif total_accepted > 0:
            response_body["status"] = "partial_success"
            return 207, resp_headers, response_body
        else:
            response_body["status"] = "rejected"
            return 422, resp_headers, response_body

    # ==========================================================================
    # WSGI Compatible Application Callable
    # ==========================================================================

    def wsgi_app(self, environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
        """
        WSGI 1.0 entrypoint for deployment behind Gunicorn, uWSGI, or in-process testing.
        """
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        headers: Dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-")
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-")
                headers[header_name] = value

        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body_bytes = environ["wsgi.input"].read(content_length) if content_length > 0 else b""

        status_code, resp_headers, resp_data = self.handle_request(
            method=method,
            path=path,
            headers=headers,
            body_bytes=body_bytes
        )

        status_messages = {
            200: "200 OK",
            207: "207 Multi-Status",
            400: "400 Bad Request",
            401: "401 Unauthorized",
            404: "404 Not Found",
            405: "405 Method Not Allowed",
            422: "422 Unprocessable Entity",
            500: "500 Internal Server Error"
        }
        status_line = status_messages.get(status_code, f"{status_code} Status")
        header_tuples = [(k, v) for k, v in resp_headers.items()]

        start_response(status_line, header_tuples)
        return [json.dumps(resp_data).encode("utf-8")]

    def __call__(self, environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
        return self.wsgi_app(environ, start_response)
