"""
Contract Test Suite for Inbound Telemetry HTTP Adapter
GrowthOS Module 4: AI Growth Brain

Verifies contract specification between Module 2 Behavior SDK and Module 4 Ingestion:
1. Valid batch ingestion (200 OK)
2. HMAC signature verification & anti-replay protection (401 Unauthorized)
3. Replay attack rejection for timestamp drift > 300s (401 Unauthorized)
4. Idempotent deduplication on identical event_ids
5. Automatic reversible identity resolution on authenticated events
6. Partial batch failures with per-event rejection codes (207 Multi-Status)
7. Global consent enforcement under DPDP (dropped when analytics=false)
8. End-to-end HTTP client integration via WSGI transport

Strictly NO emojis in code, docstrings, or logs.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import pytest
import httpx

from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_identity_resolver import SqlIdentityResolver
from adapters.http_telemetry_adapter import (
    HttpTelemetryAdapter,
    generate_hmac_signature,
    verify_hmac_signature
)
from services.ingestion_service import EventIngestionService
from domain.metrics import TimeWindow


@pytest.fixture
def test_setup():
    """Sets up an isolated in-memory storage, identity resolver, and HTTP adapter."""
    storage = SqlEventStorageAdapter(db_path=":memory:")
    resolver = SqlIdentityResolver(db_path=":memory:")
    service = EventIngestionService(storage=storage, identity_resolver=resolver)
    
    tenant_id = "tenant_test_merchant"
    secret_key = "test_super_secret_signing_key_123"
    
    adapter = HttpTelemetryAdapter(
        ingestion_service=service,
        tenant_secrets={tenant_id: secret_key},
        default_secret="fallback_secret",
        max_drift_seconds=300.0,
        enforce_signatures=True
    )
    
    return {
        "storage": storage,
        "resolver": resolver,
        "service": service,
        "adapter": adapter,
        "tenant_id": tenant_id,
        "secret_key": secret_key
    }


def make_signed_headers(
    payload_bytes: bytes,
    tenant_id: str,
    secret_key: str,
    timestamp: Optional[str] = None
) -> dict:
    """Helper to produce valid signature and timestamp headers."""
    ts_str = timestamp or datetime.now(timezone.utc).isoformat()
    signature = generate_hmac_signature(payload_bytes, ts_str, secret_key)
    return {
        "X-Tenant-ID": tenant_id,
        "X-GrowthOS-Signature": signature,
        "X-GrowthOS-Timestamp": ts_str,
        "Content-Type": "application/json"
    }


# ==============================================================================
# Contract Test Cases
# ==============================================================================

def test_health_check_endpoint(test_setup):
    adapter = test_setup["adapter"]
    status_code, headers, body = adapter.handle_request(
        method="GET",
        path="/v1/health",
        headers={},
        body_bytes=b""
    )
    assert status_code == 200
    assert body["status"] == "healthy"
    assert body["service"] == "growthos-telemetry-ingest"


def test_valid_batch_ingestion_success(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    storage = test_setup["storage"]

    batch_payload = {
        "batch_id": "batch_uuid_001",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.2.0",
        "consent": {"analytics": True, "marketing": True},
        "events": [
            {
                "event_id": "evt_client_101",
                "session_id": "sess_user_99",
                "anonymous_id": "anon_guest_99",
                "event_name": "product.viewed",
                "timestamp": "2026-10-09T10:00:00Z",
                "properties": {"product_id": "pizza_margherita", "price_paise": 45000}
            },
            {
                "event_id": "evt_client_102",
                "session_id": "sess_user_99",
                "anonymous_id": "anon_guest_99",
                "event_name": "cart.item_added",
                "timestamp": "2026-10-09T10:02:00Z",
                "properties": {"product_id": "pizza_margherita", "quantity": 1}
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    status_code, _, body = adapter.handle_request(
        method="POST",
        path="/v1/telemetry/events",
        headers=headers,
        body_bytes=body_bytes
    )

    assert status_code == 200
    assert body["status"] == "success"
    assert body["batch_id"] == "batch_uuid_001"
    assert body["total_received"] == 2
    assert body["accepted"] == 2
    assert body["inserted"] == 2
    assert body["rejected"] == 0
    assert len(body["errors"]) == 0

    # Verify rows stored in database
    window = TimeWindow(
        start=datetime(2026, 10, 9, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 9, 23, 59, tzinfo=timezone.utc)
    )
    events = storage.query_events(tenant_id=tenant_id, window=window)
    assert len(events) == 2
    event_names = [e.event_name for e in events]
    assert "product.viewed" in event_names
    assert "cart.item_added" in event_names


def test_invalid_hmac_signature_rejected(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]

    batch_payload = {"batch_id": "batch_tampered", "events": []}
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = {
        "X-Tenant-ID": tenant_id,
        "X-GrowthOS-Signature": "v1=tampered_signature_hex_000000000000",
        "X-GrowthOS-Timestamp": datetime.now(timezone.utc).isoformat(),
        "Content-Type": "application/json"
    }

    status_code, _, body = adapter.handle_request(
        method="POST",
        path="/v1/telemetry/events",
        headers=headers,
        body_bytes=body_bytes
    )

    assert status_code == 401
    assert body["error"] == "Unauthorized"
    assert "Invalid HMAC signature" in body["message"]


def test_timestamp_drift_replay_protection(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]

    batch_payload = {"batch_id": "batch_old_replay", "events": []}
    body_bytes = json.dumps(batch_payload).encode("utf-8")

    # Stale timestamp: 400 seconds in the past (> 300s limit)
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
    headers = make_signed_headers(body_bytes, tenant_id, secret_key, timestamp=old_time)

    status_code, _, body = adapter.handle_request(
        method="POST",
        path="/v1/telemetry/events",
        headers=headers,
        body_bytes=body_bytes
    )

    assert status_code == 401
    assert body["error"] == "Unauthorized"
    assert "Timestamp drift exceeds 300 seconds" in body["message"]


def test_missing_tenant_id_header_returns_400(test_setup):
    adapter = test_setup["adapter"]
    status_code, _, body = adapter.handle_request(
        method="POST",
        path="/v1/telemetry/events",
        headers={"Content-Type": "application/json"},
        body_bytes=b'{"batch_id": "b1"}'
    )
    assert status_code == 400
    assert body["error"] == "Missing X-Tenant-ID"


def test_idempotent_deduplication(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    storage = test_setup["storage"]

    batch_payload = {
        "batch_id": "batch_dedupe_test",
        "events": [
            {
                "event_id": "evt_repeat_uuid_001",
                "session_id": "sess_repeat",
                "event_name": "checkout.started",
                "timestamp": "2026-10-09T11:00:00Z"
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    # First transmission: should insert
    code1, _, body1 = adapter.handle_request("POST", "/v1/telemetry/events", headers, body_bytes)
    assert code1 == 200
    assert body1["inserted"] == 1
    assert body1["deduplicated"] == 0

    # Second transmission (identical event_id): should deduplicate
    code2, _, body2 = adapter.handle_request("POST", "/v1/telemetry/events", headers, body_bytes)
    assert code2 == 200
    assert body2["inserted"] == 0
    assert body2["deduplicated"] == 1

    # Storage should contain exactly 1 row
    window = TimeWindow(
        start=datetime(2026, 10, 9, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 9, 23, 59, tzinfo=timezone.utc)
    )
    events = storage.query_events(tenant_id=tenant_id, window=window)
    assert len(events) == 1


def test_identity_resolution_on_checkout_event(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    resolver = test_setup["resolver"]

    batch_payload = {
        "batch_id": "batch_identity_link",
        "events": [
            {
                "event_id": "evt_auth_link_01",
                "session_id": "sess_guest_login",
                "anonymous_id": "anon_untracked_guest",
                "customer_id": "cust_authenticated_user_99",
                "event_name": "checkout.step_completed",
                "timestamp": "2026-10-09T11:30:00Z",
                "properties": {"step": 1}
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    code, _, _ = adapter.handle_request("POST", "/v1/telemetry/events", headers, body_bytes)
    assert code == 200

    # Verify identity link was established in resolver
    canonical = resolver.get_canonical_customer_id(tenant_id, "anon_untracked_guest")
    assert canonical == "cust_authenticated_user_99"


def test_partial_batch_multi_status_207(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    storage = test_setup["storage"]

    batch_payload = {
        "batch_id": "batch_partial_failures",
        "events": [
            {
                # Valid item
                "event_id": "evt_valid_item_01",
                "session_id": "sess_valid",
                "event_name": "product.viewed",
                "timestamp": "2026-10-09T12:00:00Z"
            },
            {
                # Invalid item: missing event_id
                "session_id": "sess_valid",
                "event_name": "product.viewed",
                "timestamp": "2026-10-09T12:00:00Z"
            },
            {
                # Invalid item: missing session_id
                "event_id": "evt_missing_session_02",
                "event_name": "product.viewed",
                "timestamp": "2026-10-09T12:00:00Z"
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    code, _, body = adapter.handle_request("POST", "/v1/telemetry/events", headers, body_bytes)

    # 207 Multi-Status for mixed results
    assert code == 207
    assert body["status"] == "partial_success"
    assert body["total_received"] == 3
    assert body["accepted"] == 1
    assert body["inserted"] == 1
    assert body["rejected"] == 2
    assert len(body["errors"]) == 2

    error_reasons = [e["reason"] for e in body["errors"]]
    assert "MISSING_EVENT_ID" in error_reasons
    assert "MISSING_SESSION_ID" in error_reasons

    # Verify only the valid item was saved in DB
    window = TimeWindow(
        start=datetime(2026, 10, 9, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 9, 23, 59, tzinfo=timezone.utc)
    )
    events = storage.query_events(tenant_id=tenant_id, window=window)
    assert len(events) == 1
    assert events[0].event_id == "evt_valid_item_01"


def test_consent_revocation_drops_events(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    storage = test_setup["storage"]

    batch_payload = {
        "batch_id": "batch_consent_false",
        "consent": {"analytics": False, "marketing": False},
        "events": [
            {
                "event_id": "evt_consent_revoked_01",
                "session_id": "sess_revoked",
                "event_name": "product.viewed",
                "timestamp": "2026-10-09T12:30:00Z"
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    code, _, body = adapter.handle_request("POST", "/v1/telemetry/events", headers, body_bytes)
    assert code == 200
    assert body["status"] == "dropped_by_consent"
    assert body["accepted"] == 0
    assert body["rejected"] == 1

    # Verify nothing was saved to storage
    window = TimeWindow(
        start=datetime(2026, 10, 9, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 9, 23, 59, tzinfo=timezone.utc)
    )
    events = storage.query_events(tenant_id=tenant_id, window=window)
    assert len(events) == 0


def test_httpx_wsgi_transport_end_to_end(test_setup):
    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]

    batch_payload = {
        "batch_id": "batch_wsgi_client",
        "events": [
            {
                "event_id": "evt_wsgi_uuid_99",
                "session_id": "sess_wsgi",
                "event_name": "checkout.started",
                "timestamp": "2026-10-09T13:00:00Z"
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")
    headers = make_signed_headers(body_bytes, tenant_id, secret_key)

    # Use HTTPX with in-process WSGI transport
    transport = httpx.WSGITransport(app=adapter.wsgi_app)
    with httpx.Client(transport=transport, base_url="http://growthos-gateway") as client:
        resp = client.post("/v1/telemetry/events", content=body_bytes, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["batch_id"] == "batch_wsgi_client"
        assert data["accepted"] == 1


def test_ephemeral_client_session_token_authentication(test_setup):
    from adapters.http_telemetry_adapter import generate_ephemeral_client_token

    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]
    session_id = "sess_browser_user_77"

    # Merchant backend issues short-lived token to browser without giving out secret_key
    client_token = generate_ephemeral_client_token(
        tenant_id=tenant_id,
        session_id=session_id,
        secret_key=secret_key,
        ttl_seconds=1800
    )

    batch_payload = {
        "batch_id": "batch_browser_token",
        "events": [
            {
                "event_id": "evt_browser_token_1",
                "session_id": session_id,
                "event_name": "page.viewed",
                "timestamp": "2026-10-09T14:00:00Z"
            }
        ]
    }
    body_bytes = json.dumps(batch_payload).encode("utf-8")

    # Ingest using Bearer Authorization header
    headers = {
        "X-Tenant-ID": tenant_id,
        "Authorization": f"Bearer {client_token}",
        "Content-Type": "application/json"
    }
    code, _, resp = adapter.handle_request(method="POST", path="/v1/telemetry/events", headers=headers, body_bytes=body_bytes)
    assert code == 200
    assert resp["status"] == "success"
    assert resp["accepted"] == 1


def test_ephemeral_client_token_rejection_on_expired_or_tampered(test_setup):
    from adapters.http_telemetry_adapter import generate_ephemeral_client_token

    adapter = test_setup["adapter"]
    tenant_id = test_setup["tenant_id"]
    secret_key = test_setup["secret_key"]

    # 1. Expired token (ttl = -10 seconds)
    expired_token = generate_ephemeral_client_token(
        tenant_id=tenant_id,
        session_id="sess_exp",
        secret_key=secret_key,
        ttl_seconds=-10
    )
    headers = {
        "X-Tenant-ID": tenant_id,
        "Authorization": f"Bearer {expired_token}",
        "Content-Type": "application/json"
    }
    code, _, resp = adapter.handle_request(
        method="POST", path="/v1/telemetry/events", headers=headers,
        body_bytes=json.dumps({"batch_id": "b1", "events": []}).encode("utf-8")
    )
    assert code == 401
    assert "expired" in resp["message"].lower()

    # 2. Tampered token
    tampered_token = expired_token[:-4] + "dead"
    headers["Authorization"] = f"Bearer {tampered_token}"
    code, _, resp = adapter.handle_request(
        method="POST", path="/v1/telemetry/events", headers=headers,
        body_bytes=json.dumps({"batch_id": "b2", "events": []}).encode("utf-8")
    )
    assert code == 401
