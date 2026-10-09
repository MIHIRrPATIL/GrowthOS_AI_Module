"""
Unit and Integration Tests for Phase 3:
Campaign Planning, Validation, State Machine Deployment, and REST Endpoints.
Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from fastapi.testclient import TestClient

from domain.plans import (
    CampaignPlan,
    PlanGenerationRequest,
    PlanStatus,
    BiddingStrategyType,
    ObjectiveType,
    AdCopy
)
from engines.planning_engine import CampaignPlanningEngine
from engines.validation_engine import CampaignValidationEngine
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.playback_client import PlaybackAdsConnector
from services.deployment_service import CampaignDeploymentService
from api.main import create_app
from config import AdsModuleConfig


@pytest.fixture
def storage():
    return SqlAdsStorageAdapter(":memory:")


@pytest.fixture
def connector():
    return PlaybackAdsConnector()


@pytest.fixture
def planning_engine():
    return CampaignPlanningEngine()


@pytest.fixture
def validation_engine():
    return CampaignValidationEngine()


@pytest.fixture
def deployment_service(storage, connector, validation_engine):
    return CampaignDeploymentService(
        storage=storage,
        connector=connector,
        validation_engine=validation_engine
    )


@pytest.fixture
def client(storage, connector):
    config = AdsModuleConfig(
        db_url="sqlite:///:memory:",
        workspace_id="ws_dominos_test"
    )
    app = create_app(config=config, storage=storage, connector=connector)
    return TestClient(app)


# =============================================================================
# 1. Planning Engine Tests
# =============================================================================

def test_planning_engine_generates_valid_plan(planning_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_dominos_test",
        account_id="8023466278",
        goal_prompt="Increase weekend pizza delivery orders from students in Mumbai",
        store_name="Domino's Pizza",
        store_url="https://dominos.co.in",
        daily_budget_inr=2500.0,
        target_cpa_inr=180.0,
        target_cities=["Mumbai"],
        product_category="Pizza"
    )

    plan = planning_engine.generate_plan(req)

    assert plan.workspace_id == "ws_dominos_test"
    assert plan.account_id == "8023466278"
    assert plan.daily_budget_inr == 2500.0
    assert plan.daily_budget_paise == 250000
    assert plan.target_cpa_inr == 180.0
    assert plan.target_cpa_paise == 18000
    assert plan.status == PlanStatus.DRAFT
    assert len(plan.keyword_clusters) >= 2
    assert len(plan.negative_keywords) >= 5

    # Check RSA ad copy bounds
    assert len(plan.ad_copies) == 1
    copy = plan.ad_copies[0]
    assert len(copy.headlines) >= 3
    for h in copy.headlines:
        assert len(h) <= 30
        assert len(h.strip()) > 0
    assert len(copy.descriptions) >= 2
    for d in copy.descriptions:
        assert len(d) <= 90
        assert len(d.strip()) > 0
    assert copy.final_url.startswith("https://")


# =============================================================================
# 2. Validation Engine Guardrail Tests
# =============================================================================

def test_validation_engine_passes_good_plan(planning_engine, validation_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_dominos_test",
        account_id="8023466278",
        goal_prompt="Order fresh burger online",
        store_name="Burger House",
        store_url="https://burgerhouse.com",
        daily_budget_inr=1500.0,
        target_cpa_inr=200.0,
        target_cities=["Bengaluru"],
        product_category="Burgers"
    )
    plan = planning_engine.generate_plan(req)
    res = validation_engine.validate(plan)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_validation_engine_flags_under_budget(planning_engine, validation_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_dominos_test",
        account_id="8023466278",
        goal_prompt="Order fresh pizza",
        store_name="Pizza House",
        store_url="https://pizzahouse.com",
        daily_budget_inr=100.0,  # Below 500 INR minimum
        target_cities=["Mumbai"]
    )
    plan = planning_engine.generate_plan(req)
    res = validation_engine.validate(plan)
    assert res.is_valid is False
    assert any("below the platform minimum" in err for err in res.errors)


def test_validation_engine_flags_cpa_exceeding_daily_budget(planning_engine, validation_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_dominos_test",
        account_id="8023466278",
        goal_prompt="Order fresh pizza",
        store_name="Pizza House",
        store_url="https://pizzahouse.com",
        daily_budget_inr=1000.0,
        target_cpa_inr=2000.0,  # Exceeds daily budget of 1000
        target_cities=["Mumbai"]
    )
    plan = planning_engine.generate_plan(req)
    res = validation_engine.validate(plan)
    assert res.is_valid is False
    assert any("exceeds total daily budget" in err for err in res.errors)


def test_validation_engine_flags_policy_violations(planning_engine, validation_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_dominos_test",
        account_id="8023466278",
        goal_prompt="Order food",
        store_name="Pizza",
        store_url="https://pizza.com",
        daily_budget_inr=1000.0
    )
    plan = planning_engine.generate_plan(req)

    # Inject policy violations
    plan.ad_copies[0].headlines[0] = "Order Online!!"  # Double exclamation mark
    res = validation_engine.validate(plan)
    assert res.is_valid is False
    assert any("repeated punctuation" in err for err in res.errors)


# =============================================================================
# 3. Storage Roundtrip Tests
# =============================================================================

def test_storage_campaign_plan_crud(storage, planning_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_crud_test",
        account_id="8023466278",
        goal_prompt="Quick delivery",
        store_name="Domino's",
        store_url="https://dominos.co.in",
        daily_budget_inr=3000.0
    )
    plan = planning_engine.generate_plan(req)
    storage.save_campaign_plan(plan)

    fetched = storage.get_campaign_plan(plan.plan_id)
    assert fetched is not None
    assert fetched.plan_id == plan.plan_id
    assert fetched.daily_budget_paise == 300000
    assert fetched.status == PlanStatus.DRAFT

    # Update status
    updated = storage.update_plan_status(plan.plan_id, PlanStatus.APPROVED, approved_by="admin_user")
    assert updated.status == PlanStatus.APPROVED
    assert updated.approved_by == "admin_user"

    # List
    plans = storage.list_campaign_plans("ws_crud_test")
    assert len(plans) == 1
    assert plans[0].plan_id == plan.plan_id


# =============================================================================
# 4. State Machine Deployment Service Tests
# =============================================================================

def test_state_machine_full_lifecycle(storage, deployment_service, planning_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_lifecycle_test",
        account_id="8023466278",
        goal_prompt="Order pizza delivery in Mumbai",
        store_name="Domino's Mumbai",
        store_url="https://dominos.co.in",
        daily_budget_inr=2000.0,
        target_cpa_inr=200.0,
        target_cities=["Mumbai"]
    )
    plan = planning_engine.generate_plan(req)
    storage.save_campaign_plan(plan)
    assert plan.status == PlanStatus.DRAFT

    # Step 1: Validate
    validated_plan = deployment_service.validate_plan(plan.plan_id)
    assert validated_plan.status == PlanStatus.AWAITING_APPROVAL
    assert len(validated_plan.validation_errors) == 0

    # Step 2: Cannot deploy directly before approval
    with pytest.raises(ValueError, match="must be approved prior to deployment"):
        deployment_service.deploy_plan(plan.plan_id)

    # Step 3: Approve
    approved_plan = deployment_service.approve_plan(
        plan.plan_id,
        approved_by="merchant_manager",
        approval_notes="Budget verified against merchant monthly limit"
    )
    assert approved_plan.status == PlanStatus.APPROVED
    assert approved_plan.approved_by == "merchant_manager"

    # Step 4: Dry-run deploy (validate_only=True)
    dry_run_plan = deployment_service.deploy_plan(plan.plan_id, validate_only=True)
    assert dry_run_plan.status == PlanStatus.APPROVED  # Stays approved in dry run

    # Step 5: Full deploy
    deployed_plan = deployment_service.deploy_plan(plan.plan_id, validate_only=False)
    assert deployed_plan.status == PlanStatus.ACTIVE
    assert deployed_plan.deployed_campaign_id is not None
    assert deployed_plan.deployed_campaign_id.startswith("sim_camp_")


def test_state_machine_validation_failure_handling(storage, deployment_service, planning_engine):
    req = PlanGenerationRequest(
        workspace_id="ws_fail_test",
        account_id="8023466278",
        goal_prompt="Order pizza delivery",
        store_name="Domino's",
        store_url="https://dominos.co.in",
        daily_budget_inr=100.0  # Invalid budget
    )
    plan = planning_engine.generate_plan(req)
    storage.save_campaign_plan(plan)

    failed_plan = deployment_service.validate_plan(plan.plan_id)
    assert failed_plan.status == PlanStatus.VALIDATION_FAILED
    assert len(failed_plan.validation_errors) > 0

    # Cannot approve a plan in VALIDATION_FAILED status
    with pytest.raises(ValueError, match="must be in 'AWAITING_APPROVAL' state"):
        deployment_service.approve_plan(plan.plan_id, approved_by="admin")


# =============================================================================
# 5. REST API Integration Tests
# =============================================================================

def test_api_campaign_planning_and_lifecycle_flow(client):
    # 1. Plan creation
    plan_payload = {
        "workspace_id": "ws_api_test",
        "account_id": "8023466278",
        "goal_prompt": "Boost weekend pizza delivery orders in Mumbai",
        "store_name": "Domino's Mumbai Store",
        "store_url": "https://dominos.co.in",
        "daily_budget_inr": 2000.0,
        "target_cpa_inr": 220.0,
        "target_cities": ["Mumbai"],
        "product_category": "Pizza"
    }

    res = client.post("/api/v1/ads/campaigns/plan", json=plan_payload)
    assert res.status_code == 200
    plan_data = res.json()
    plan_id = plan_data["plan_id"]
    assert plan_data["status"] == "DRAFT"
    assert plan_data["daily_budget_paise"] == 200000

    # 2. Get plan by ID
    get_res = client.get(f"/api/v1/ads/campaigns/plans/{plan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["plan_id"] == plan_id

    # 3. List plans
    list_res = client.get("/api/v1/ads/campaigns/plans?workspace_id=ws_api_test")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Validate plan
    val_res = client.post(f"/api/v1/ads/campaigns/plans/{plan_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["status"] == "AWAITING_APPROVAL"

    # 5. Approve plan
    approve_res = client.post(
        f"/api/v1/ads/campaigns/plans/{plan_id}/approve",
        json={"approved_by": "marketing_lead", "approval_notes": "Looks good"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["approved_by"] == "marketing_lead"

    # 6. Dry run deploy
    dry_res = client.post(f"/api/v1/ads/campaigns/plans/{plan_id}/deploy?validate_only=true")
    assert dry_res.status_code == 200
    assert dry_res.json()["status"] == "APPROVED"

    # 7. Real deploy
    deploy_res = client.post(f"/api/v1/ads/campaigns/plans/{plan_id}/deploy?validate_only=false")
    assert deploy_res.status_code == 200
    deployed = deploy_res.json()
    assert deployed["status"] == "ACTIVE"
    assert deployed["deployed_campaign_id"] is not None
