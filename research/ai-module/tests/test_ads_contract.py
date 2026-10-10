"""
Contract and Integration Tests: Ads Layer (Module 3) to AI Growth Brain (Module 4)
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
import json
from datetime import datetime, timezone
import httpx

from domain.metrics import AdsCampaignDaily, BlendedAdMetrics, DigestFlag
from ports.ads_port import AdsPort
from adapters.http_ads_adapter import HttpAdsAdapter
from engines.metrics_engine import MetricsEngine
from engines.digest_engine import DigestEngine
from engines.evidence_linker import EvidenceLinker
from adapters.sql_event_storage import SqlEventStorageAdapter


def create_mock_ads_server_transport() -> httpx.MockTransport:
    """
    Creates an HTTP MockTransport simulating the GrowthOS Ads Module REST API (port 8001).
    Conforms to OpenAPI contract defined in research/Ads-Module/docs/Core_Idea.md and api/routes.py.
    """
    mock_campaigns = [
        {
            "workspace_id": "tenant_dominos_qsr",
            "platform": "google_ads",
            "account_id": "8023466278",
            "campaign_id": "10101",
            "campaign_name": "Domino's Weekend Pizza Delivery Search",
            "date": "2026-10-07",
            "spend_paise": 450000,       # INR 4,500
            "spend_inr": 4500.0,
            "impressions": 10000,
            "clicks": 500,
            "conversions": 45.0,
            "conversion_value_paise": 2250000, # INR 22,500
            "ctr": 0.05,
            "cpc_paise": 900,
            "cpa_paise": 10000,
            "roas": 5.0,
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "status": "ACTIVE",
            "synced_at": "2026-10-09T10:00:00Z"
        },
        {
            "workspace_id": "tenant_dominos_qsr",
            "platform": "google_ads",
            "account_id": "8023466278",
            "campaign_id": "10102",
            "campaign_name": "Domino's Late Night Pizza Search",
            "date": "2026-10-07",
            "spend_paise": 250000,       # INR 2,500
            "spend_inr": 2500.0,
            "impressions": 6000,
            "clicks": 250,
            "conversions": 20.0,
            "conversion_value_paise": 1000000, # INR 10,000
            "ctr": 0.0417,
            "cpc_paise": 1000,
            "cpa_paise": 12500,
            "roas": 4.0,
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "status": "ACTIVE",
            "synced_at": "2026-10-09T10:00:00Z"
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/api/v1/ads/campaigns/metrics/bulk":
            workspace_id = request.url.params.get("workspace_id")
            if not workspace_id:
                return httpx.Response(422, json={"detail": "Missing workspace_id"})
            filtered = [c for c in mock_campaigns if c["workspace_id"] == workspace_id]
            return httpx.Response(200, json=filtered)

        elif url_path.startswith("/api/v1/ads/campaigns/") and url_path.endswith("/metrics"):
            parts = url_path.strip("/").split("/")
            camp_id = parts[4]
            filtered = [c for c in mock_campaigns if c["campaign_id"] == camp_id]
            return httpx.Response(200, json=filtered)

        elif url_path == "/api/v1/ads/health":
            return httpx.Response(200, json={"status": "healthy", "service": "growthos-ads-module"})

        elif url_path == "/api/v1/ads/campaigns/plan" and request.method == "POST":
            body = json.loads(request.content)
            return httpx.Response(200, json={
                "plan_id": "plan_test123",
                "workspace_id": body.get("workspace_id", "ws_test"),
                "account_id": body.get("account_id", "8023466278"),
                "name": "Test Search Campaign",
                "status": "DRAFT",
                "daily_budget_paise": int(body.get("daily_budget_inr", 2000) * 100)
            })

        elif url_path == "/api/v1/ads/campaigns/plans/plan_test123/validate" and request.method == "POST":
            return httpx.Response(200, json={
                "plan_id": "plan_test123",
                "status": "AWAITING_APPROVAL",
                "validation_errors": []
            })

        elif url_path == "/api/v1/ads/campaigns/plans/plan_test123/approve" and request.method == "POST":
            body = json.loads(request.content)
            return httpx.Response(200, json={
                "plan_id": "plan_test123",
                "status": "APPROVED",
                "approved_by": body.get("approved_by", "admin")
            })

        elif url_path == "/api/v1/ads/campaigns/plans/plan_test123/deploy" and request.method == "POST":
            validate_only = request.url.params.get("validate_only", "false").lower() == "true"
            return httpx.Response(200, json={
                "plan_id": "plan_test123",
                "status": "APPROVED" if validate_only else "ACTIVE",
                "deployed_campaign_id": None if validate_only else "camp_998877"
            })

        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


def test_http_ads_adapter_contract():
    transport = create_mock_ads_server_transport()
    adapter = HttpAdsAdapter(base_url="http://localhost:8001", transport=transport)

    assert isinstance(adapter, AdsPort)

    # Fetch bulk metrics
    records = adapter.fetch_bulk_metrics(
        workspace_id="tenant_dominos_qsr",
        start_date="2026-10-06",
        end_date="2026-10-08"
    )

    assert len(records) == 2
    rec = records[0]
    assert rec.campaign_id == "10101"
    assert rec.spend_paise == 450000
    assert rec.spend_inr == 4500.0
    assert rec.currency == "INR"
    assert rec.status == "ACTIVE"

    # Fetch single campaign metrics
    single = adapter.fetch_campaign_metrics(
        campaign_id="10102",
        start_date="2026-10-06",
        end_date="2026-10-08"
    )
    assert len(single) == 1
    assert single[0].campaign_name == "Domino's Late Night Pizza Search"


def test_http_ads_adapter_network_error_raises_runtime_error():
    # Transport that always fails
    def error_handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused to port 8001")

    failing_adapter = HttpAdsAdapter(
        base_url="http://unreachable-host:8001",
        transport=httpx.MockTransport(error_handler)
    )

    with pytest.raises(RuntimeError) as exc_info:
        failing_adapter.fetch_bulk_metrics("tenant_1", "2026-10-01", "2026-10-08")
    assert "Ads Module API communication error" in str(exc_info.value)


def test_metrics_engine_calculates_blended_ad_metrics():
    storage = SqlEventStorageAdapter(":memory:")
    metrics_engine = MetricsEngine(storage=storage)

    ad_records = [
        AdsCampaignDaily(
            workspace_id="ws_1",
            account_id="acc_1",
            campaign_id="c1",
            campaign_name="Camp 1",
            date="2026-10-08",
            spend_paise=300000,       # INR 3,000
            spend_inr=3000.0,
            impressions=10000,
            clicks=400,
            conversions=30.0,
            conversion_value_paise=1500000,
            ctr=0.04,
            cpc_paise=750,
            cpa_paise=10000,
            roas=5.0
        ),
        AdsCampaignDaily(
            workspace_id="ws_1",
            account_id="acc_1",
            campaign_id="c2",
            campaign_name="Camp 2",
            date="2026-10-08",
            spend_paise=200000,       # INR 2,000
            spend_inr=2000.0,
            impressions=5000,
            clicks=200,
            conversions=10.0,
            conversion_value_paise=800000,
            ctr=0.04,
            cpc_paise=1000,
            cpa_paise=20000,
            roas=4.0
        )
    ]

    # Calculate blended metrics with 25 new customers acquired
    blended = metrics_engine.calculate_blended_ad_metrics(
        ad_records=ad_records,
        new_customers_count=25,
        attributed_revenue_paise=2300000
    )

    assert isinstance(blended, BlendedAdMetrics)
    assert blended.total_spend_paise == 500000  # INR 5,000
    assert blended.total_spend_inr == 5000.0
    assert blended.total_impressions == 15000
    assert blended.total_clicks == 600
    assert blended.total_conversions == 40.0
    assert blended.conversion_value_paise == 2300000

    # Rates
    assert blended.blended_ctr == 0.04  # 600 / 15000
    assert blended.blended_cpc_paise == 833  # 500000 / 600
    assert blended.blended_cpa_paise == 12500  # 500000 / 40 = 125.00 INR
    assert blended.blended_roas == 4.6  # 2300000 / 500000 = 4.60x

    # Blended CAC
    assert blended.blended_cac_paise == 20000  # 500000 / 25 = 200.00 INR
    assert blended.blended_cac_inr == 200.0
    assert blended.campaign_count == 2


def test_digest_engine_detects_cpa_spike_anomaly():
    storage = SqlEventStorageAdapter(":memory:")
    metrics_engine = MetricsEngine(storage=storage)
    digest_engine = DigestEngine(metrics_engine=metrics_engine, storage=storage)

    prior = [
        AdsCampaignDaily(
            workspace_id="ws_1",
            account_id="acc_1",
            campaign_id="camp_weekend",
            campaign_name="Weekend Pizza",
            date="2026-10-01",
            spend_paise=500000,
            spend_inr=5000.0,
            impressions=10000,
            clicks=500,
            conversions=50.0,
            conversion_value_paise=2500000,
            cpa_paise=10000  # INR 100
        )
    ]

    current = [
        AdsCampaignDaily(
            workspace_id="ws_1",
            account_id="acc_1",
            campaign_id="camp_weekend",
            campaign_name="Weekend Pizza",
            date="2026-10-08",
            spend_paise=700000,
            spend_inr=7000.0,
            impressions=10000,
            clicks=500,
            conversions=40.0,
            conversion_value_paise=2000000,
            cpa_paise=17500  # INR 175 (+75% spike!)
        )
    ]

    flags = digest_engine.detect_ad_anomalies(
        tenant_id="ws_1",
        current_records=current,
        prior_records=prior,
        cpa_drift_threshold_pct=25.0
    )

    assert len(flags) == 1
    flag = flags[0]
    assert flag.metric_name == "cpa_camp_weekend"
    assert flag.severity == "high"  # >= 50% spike
    assert flag.current_value == 175.0
    assert flag.prior_value == 100.0
    assert flag.adverse is True


def test_evidence_linker_grounds_ad_narrative_claim():
    linker = EvidenceLinker()

    narrative = (
        "The weekend pizza campaign ad cpa increased to 175.0 "
        "[citation: metric=ad_cpa value=175.0 prior=100.0 sample=40]."
    )
    flag = DigestFlag(
        dedupe_key="k1",
        tenant_id="t1",
        metric_name="ad_cpa",
        period="day_over_day",
        polarity="lower_is_better",
        current_value=175.0,
        prior_value=100.0,
        current_sample_size=40,
        prior_sample_size=50,
        unit="currency_inr",
        threshold_pct=25.0,
        severity="high",
        adverse=True,
        flagged_at=datetime.now(timezone.utc)
    )

    clean_text, citations, dropped = linker.verify_and_link(narrative, flags=[flag])
    assert len(dropped) == 0
    assert len(citations) == 1
    assert citations[0].metric_name == "ad_cpa"
    assert citations[0].is_verified is True
    assert "ad cpa increased to 175.0" in clean_text


def test_http_ads_adapter_campaign_lifecycle_contract():
    transport = create_mock_ads_server_transport()
    adapter = HttpAdsAdapter(base_url="http://localhost:8001", transport=transport)

    # 1. Plan campaign
    req = {
        "workspace_id": "tenant_dominos_qsr",
        "account_id": "8023466278",
        "goal_prompt": "Boost weekend pizza delivery orders in Mumbai",
        "daily_budget_inr": 2500.0
    }
    plan = adapter.plan_campaign(req)
    assert plan["plan_id"] == "plan_test123"
    assert plan["status"] == "DRAFT"

    # 2. Validate campaign
    val = adapter.validate_campaign_plan("plan_test123")
    assert val["status"] == "AWAITING_APPROVAL"

    # 3. Approve campaign
    appr = adapter.approve_campaign_plan("plan_test123", approved_by="ai_brain_policy")
    assert appr["status"] == "APPROVED"
    assert appr["approved_by"] == "ai_brain_policy"

    # 4. Dry-run deploy
    dry = adapter.deploy_campaign_plan("plan_test123", validate_only=True)
    assert dry["status"] == "APPROVED"

    # 5. Full deploy
    live = adapter.deploy_campaign_plan("plan_test123", validate_only=False)
    assert live["status"] == "ACTIVE"
    assert live["deployed_campaign_id"] == "camp_998877"
