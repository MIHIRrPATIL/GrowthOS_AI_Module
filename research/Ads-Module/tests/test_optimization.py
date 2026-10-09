"""
Unit and Integration Tests for Phase 5:
Autonomous Campaign Optimization, Policy-Gated Budget Shifts, and Rollback State Tracking.
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from domain.optimization import (
    OptimizationProposal,
    OptimizationProposalType,
    OptimizationRequest,
    ProposalStatus
)
from domain.models import AdsCampaignDaily
from engines.optimization_engine import CampaignOptimizationEngine
from services.optimization_service import OptimizationService
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.playback_client import PlaybackAdsConnector
from api.main import create_app
from config import AdsModuleConfig


@pytest.fixture
def storage():
    return SqlAdsStorageAdapter(":memory:")


@pytest.fixture
def optimization_engine(storage):
    return CampaignOptimizationEngine(storage=storage)


@pytest.fixture
def optimization_service(storage):
    connector = PlaybackAdsConnector()
    return OptimizationService(storage=storage, connector=connector)


@pytest.fixture
def client(storage):
    config = AdsModuleConfig(
        db_url="sqlite:///:memory:",
        workspace_id="ws_opt_test"
    )
    connector = PlaybackAdsConnector()
    app = create_app(config=config, storage=storage, connector=connector)
    return TestClient(app)


def seed_performance_data(storage: SqlAdsStorageAdapter, ws: str):
    today = date.today()
    records = []
    for i in range(5):
        d_str = (today - timedelta(days=i)).isoformat()
        # Campaign 1: Top performing winner (low CPA, high conversions)
        records.append(
            AdsCampaignDaily(
                workspace_id=ws,
                platform="google_ads",
                account_id="8023466278",
                campaign_id="camp_winner",
                campaign_name="Domino's Weekend Pizza Winner",
                date=d_str,
                spend_paise=150000,   # INR 1,500
                spend_inr=1500.0,
                impressions=8000,
                clicks=400,
                conversions=10.0,     # CPA = 150 INR
                conversion_value_paise=600000,
                ctr=0.05,
                cpc_paise=375,
                cpa_paise=15000,
                roas=4.0
            )
        )
        # Campaign 2: Bleeding campaign (high CPA, low conversions)
        records.append(
            AdsCampaignDaily(
                workspace_id=ws,
                platform="google_ads",
                account_id="8023466278",
                campaign_id="camp_bleeder",
                campaign_name="Domino's Broad Match Bleeder",
                date=d_str,
                spend_paise=250000,   # INR 2,500
                spend_inr=2500.0,
                impressions=5000,
                clicks=250,
                conversions=1.0,      # CPA = 2500 INR (> 10x target!)
                conversion_value_paise=50000,
                ctr=0.05,
                cpc_paise=1000,
                cpa_paise=250000,
                roas=0.2
            )
        )
    storage.upsert_daily_metrics(records)


# =============================================================================
# 1. Optimization Engine Tests
# =============================================================================

def test_optimization_engine_detects_opportunities(storage, optimization_engine):
    ws = "ws_opp_test"
    seed_performance_data(storage, ws)

    req = OptimizationRequest(
        workspace_id=ws,
        account_id="8023466278",
        lookback_days=7,
        target_cpa_inr=250.0,
        max_budget_shift_pct=15.0
    )

    proposals = optimization_engine.generate_proposals(req)
    assert len(proposals) >= 1

    # Find budget shift proposal
    shift_props = [p for p in proposals if p.proposal_type == OptimizationProposalType.SHIFT_BUDGET]
    assert len(shift_props) == 1
    shift = shift_props[0]
    assert shift.source_campaign_id == "camp_bleeder"
    assert shift.target_campaign_id == "camp_winner"
    assert shift.shift_pct <= 15.0  # Hard invariant
    assert shift.status == ProposalStatus.PROPOSED
    assert "Reallocate" in shift.rationale


# =============================================================================
# 2. Optimization Service Execution and Rollback Tests
# =============================================================================

def test_optimization_service_apply_and_rollback(storage, optimization_service):
    prop = OptimizationProposal(
        workspace_id="ws_roll_test",
        account_id="8023466278",
        proposal_type=OptimizationProposalType.SHIFT_BUDGET,
        source_campaign_id="camp_b",
        target_campaign_id="camp_w",
        shift_amount_paise=20000,
        shift_pct=10.0,
        rationale="Shift 10% daily budget",
        rollback_snapshot={"camp_b_budget": 200000}
    )
    storage.save_proposal(prop)

    # 1. Apply
    applied = optimization_service.apply_proposal(prop.proposal_id)
    assert applied.status == ProposalStatus.APPLIED
    assert applied.applied_at is not None

    # 2. Rollback
    rolled = optimization_service.rollback_proposal(prop.proposal_id)
    assert rolled.status == ProposalStatus.ROLLED_BACK
    assert rolled.rolled_back_at is not None


def test_optimization_policy_rejects_excessive_shift(storage, optimization_service):
    prop = OptimizationProposal(
        workspace_id="ws_excess_test",
        account_id="8023466278",
        proposal_type=OptimizationProposalType.SHIFT_BUDGET,
        source_campaign_id="camp_b",
        target_campaign_id="camp_w",
        shift_amount_paise=50000,
        shift_pct=25.0,  # Exceeds 15% policy invariant!
        rationale="Shift 25% daily budget"
    )
    storage.save_proposal(prop)

    with pytest.raises(ValueError, match="exceeds maximum allowed daily limit of 15.0%"):
        optimization_service.apply_proposal(prop.proposal_id)


# =============================================================================
# 3. REST API Integration Tests
# =============================================================================

def test_api_optimization_workflow(client, storage):
    ws = "ws_opt_api_test"
    seed_performance_data(storage, ws)

    # 1. Generate proposals
    gen_res = client.post("/api/v1/ads/optimizations/generate", json={
        "workspace_id": ws,
        "account_id": "8023466278",
        "lookback_days": 7,
        "target_cpa_inr": 250.0,
        "max_budget_shift_pct": 12.0
    })
    assert gen_res.status_code == 200
    props = gen_res.json()
    assert len(props) >= 1
    prop_id = props[0]["proposal_id"]

    # 2. List proposals
    list_res = client.get(f"/api/v1/ads/optimizations/proposals?workspace_id={ws}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Apply proposal
    apply_res = client.post(f"/api/v1/ads/optimizations/proposals/{prop_id}/apply")
    assert apply_res.status_code == 200
    assert apply_res.json()["status"] == "APPLIED"

    # 4. Rollback proposal
    roll_res = client.post(f"/api/v1/ads/optimizations/proposals/{prop_id}/rollback")
    assert roll_res.status_code == 200
    assert roll_res.json()["status"] == "ROLLED_BACK"
