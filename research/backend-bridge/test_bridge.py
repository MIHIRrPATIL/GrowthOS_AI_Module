# pyrefly: ignore [missing-import]
import pytest
from fastapi.testclient import TestClient
from main import app, signal_processor, customer_graph

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "growthos-behavior-bridge"


def test_event_batch_ingestion_and_idempotency():
    sample_batch = {
        "events": [
            {
                "event_id": "evt_test_01",
                "event_name": "product.viewed",
                "timestamp": "2026-08-24T21:30:00Z",
                "workspace_id": "ws_dominos",
                "project_id": "proj_growth_01",
                "anonymous_id": "anon_user_123",
                "customer_id": "cust_48291",
                "session_id": "sess_001",
                "idempotency_key": "idemp_test_key_01",
                "page": {
                    "url": "https://dominos.co.in/menu/farmhouse",
                    "path": "/menu/farmhouse",
                    "title": "Farmhouse Pizza"
                },
                "utm": {
                    "source": "meta",
                    "medium": "cpc",
                    "campaign": "weekend_pizza"
                },
                "device": {
                    "screen_width": 390,
                    "screen_height": 844,
                    "viewport_width": 390,
                    "viewport_height": 664,
                    "device_type": "mobile"
                },
                "properties": {
                    "product_id": "PRD-PIZZA-FARMHOUSE",
                    "name": "Farmhouse Pizza",
                    "price": 459.00
                }
            }
        ]
    }

    # 1. First send: should process 1 event
    res1 = client.post("/api/v1/events/batch", json=sample_batch)
    assert res1.status_code == 200
    assert res1.json()["processed"] == 1
    assert res1.json()["duplicates_skipped"] == 0

    # 2. Duplicate send: should skip duplicate via idempotency key
    res2 = client.post("/api/v1/events/batch", json=sample_batch)
    assert res2.status_code == 200
    assert res2.json()["processed"] == 0
    assert res2.json()["duplicates_skipped"] == 1


def test_high_intent_and_checkout_abandonment_signals():
    # Simulate 3 product views and a checkout abandonment
    batch = {
        "events": [
            {
                "event_id": f"evt_intent_{i}",
                "event_name": "product.viewed",
                "timestamp": f"2026-08-24T21:3{i}:00Z",
                "project_id": "proj_growth_01",
                "anonymous_id": "anon_high_intent_user",
                "customer_id": "cust_high_intent",
                "session_id": f"sess_intent_{i}",
                "idempotency_key": f"idemp_intent_{i}",
                "page": {"url": "https://dominos.co.in/farmhouse", "path": "/farmhouse"},
                "utm": {},
                "device": {"screen_width": 1280, "screen_height": 720, "viewport_width": 1280, "viewport_height": 720, "device_type": "desktop"},
                "properties": {"product_id": "PRD-PIZZA-FARMHOUSE", "name": "Farmhouse Pizza", "price": 459.00}
            }
            for i in range(2, 5)
        ] + [
            {
                "event_id": "evt_abandon_01",
                "event_name": "checkout.abandoned",
                "timestamp": "2026-08-24T21:40:00Z",
                "project_id": "proj_growth_01",
                "anonymous_id": "anon_high_intent_user",
                "customer_id": "cust_high_intent",
                "session_id": "sess_intent_3",
                "idempotency_key": "idemp_abandon_01",
                "page": {"url": "https://dominos.co.in/checkout", "path": "/checkout"},
                "utm": {},
                "device": {"screen_width": 1280, "screen_height": 720, "viewport_width": 1280, "viewport_height": 720, "device_type": "desktop"},
                "properties": {"step_abandoned_at": 2, "cart_value": 918.00, "time_in_checkout_seconds": 40}
            }
        ]
    }

    res = client.post("/api/v1/events/batch", json=batch)
    assert res.status_code == 200
    assert res.json()["new_signals_generated"] >= 2

    # Query signals for user
    signals_res = client.get("/api/v1/behavior/signals?user_id=cust_high_intent")
    assert signals_res.status_code == 200
    signals = signals_res.json()["signals"]
    types = [s["signal_type"] for s in signals]
    assert "behavior.high_intent.detected" in types
    assert "behavior.checkout_friction.detected" in types

    # Query customer graph
    graph_res = client.get("/api/v1/customer-graph/cust_high_intent")
    assert graph_res.status_code == 200
    graph = graph_res.json()
    assert graph["total_nodes"] > 0
    assert graph["total_edges"] > 0
