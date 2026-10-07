"""
Unit tests for Decision Provider and Action Proposer
Validates:
- Rule-based proposal generation from idle carts and digest flags.
- Dropping anonymous visitors.
- Splitting drop-off spikes into bug triage + dense telemetry candidates.
- Pure fact-grounded reasoning without speculative narratives.
- Calibrated probability is None while priority score is preserved.
- 10% causal control holdout group suppression.
- Deterministic plan ID generation and cron rerun deduplication.
"""

import pytest
from datetime import datetime, timezone

from domain.actions import ActionType, ActionPlan
from domain.metrics import DigestReport, DigestFlag
from ports.decision import DecisionContext
from engines.rule_decision_provider import RuleDecisionProvider
from services.action_proposer import ActionProposer
from adapters.sql_action_storage import SqlActionStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter


@pytest.fixture
def decision_provider():
    return RuleDecisionProvider()


@pytest.fixture
def storage():
    return SqlActionStorageAdapter(db_path=":memory:")


@pytest.fixture
def audit_ledger():
    return SqlAuditLedgerAdapter(db_path=":memory:")


def test_idle_cart_high_value_proposes_fee_waiver(decision_provider):
    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={
            "session_id": "sess_100",
            "customer_id": "cust_high_val",
            "cart_total_paise": 65000,  # INR 650
            "idle_minutes": 45
        },
        signal_dedupe_key="idle_cart_sess_100_cust_high_val"
    )
    candidates = decision_provider.propose_candidates(context)
    assert len(candidates) == 1
    cand = candidates[0]

    assert cand.action_type == ActionType.WAIVE_DELIVERY_FEE
    assert cand.target_module == "module_1_loyalty"
    assert cand.target_id == "cust_high_val"
    assert cand.parameters.fee_amount_paise == 5000
    assert cand.priority_score == 0.90
    assert cand.calibrated_probability is None  # Pure rule, uncalibrated

    # Fact-grounded reasoning check
    assert "INR 650.00" in cand.reasoning_summary
    assert "45 minutes" in cand.reasoning_summary
    assert any("cart_total_paise=65000" in ev for ev in cand.evidence_citations)


def test_idle_cart_mid_value_proposes_whatsapp_recovery(decision_provider):
    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={
            "session_id": "sess_101",
            "customer_id": "cust_mid_val",
            "cart_total_paise": 35000,  # INR 350
            "idle_minutes": 30
        },
        signal_dedupe_key="idle_cart_sess_101_cust_mid_val"
    )
    candidates = decision_provider.propose_candidates(context)
    assert len(candidates) == 1
    cand = candidates[0]

    assert cand.action_type == ActionType.SEND_RECOVERY_WHATSAPP
    assert cand.target_module == "notification"
    assert cand.parameters.channel == "whatsapp"
    assert cand.parameters.template_name == "cart_recovery_v1"
    assert cand.calibrated_probability is None


def test_idle_cart_anonymous_visitor_dropped(decision_provider):
    # Review point 14: Anonymous visitors cannot receive fee waivers or WhatsApp
    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={
            "session_id": "sess_anon",
            "customer_id": None,
            "anonymous_id": "anon_999",
            "cart_total_paise": 70000,
            "idle_minutes": 30
        },
        signal_dedupe_key="idle_cart_anon_999"
    )
    candidates = decision_provider.propose_candidates(context)
    assert len(candidates) == 0


def test_checkout_step_2_drop_off_emits_two_separate_candidates(decision_provider):
    # Review point 17: Emit two separate candidates (Bug ticket + Dense telemetry)
    context = DecisionContext(
        tenant_id="tenant_dominos",
        signal_type="digest_flag",
        signal_payload={
            "metric_name": "checkout_step_2_drop_off_rate",
            "prior_value": 0.15,
            "current_value": 0.45,
            "pct_change": 200.0,
            "sample_size": 240,
            "min_sample_met": True,
            "is_significant": True,
            "adverse": True,
            "severity": "critical"
        },
        signal_dedupe_key="digest_step2_drop_off_20261005"
    )
    candidates = decision_provider.propose_candidates(context)
    assert len(candidates) == 2

    # Candidate 1: Bug report
    c1 = candidates[0]
    assert c1.action_type == ActionType.FLAG_UI_FRICTION_BUG
    assert c1.target_module == "module_2_behavior"
    assert c1.parameters.component_selector == "checkout_step_2_fee_section"
    # Grounded fact check
    assert "Checkout step drop-off increased from 15.0% to 45.0% (+200.0%)" in c1.reasoning_summary

    # Candidate 2: Dense telemetry
    c2 = candidates[1]
    assert c2.action_type == ActionType.REQUEST_DENSE_TELEMETRY
    assert c2.parameters.duration_minutes == 120
    assert c2.parameters.sample_rate == 0.5


def test_holdout_suppression_in_action_proposer(storage, audit_ledger):
    # Find a customer_id that deterministically lands in the 10% holdout
    provider = RuleDecisionProvider()
    holdout_customer = None
    for i in range(100):
        cid = f"cust_{i}"
        if provider._is_in_holdout("tenant_dominos", cid, holdout_pct=10):
            holdout_customer = cid
            break

    assert holdout_customer is not None

    proposer = ActionProposer(
        decision_provider=provider,
        action_storage=storage,
        audit_ledger=audit_ledger
    )

    plans = proposer.propose_action_from_signal(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload={
            "session_id": "sess_holdout",
            "customer_id": holdout_customer,
            "cart_total_paise": 60000,
            "idle_minutes": 40
        },
        signal_dedupe_key=f"idle_cart_{holdout_customer}"
    )

    # In holdout -> No plan generated!
    assert len(plans) == 0

    # Audit ledger records holdout suppression
    trail = audit_ledger.get_audit_trail("tenant_dominos")
    assert any(r.event_type == "candidate_holdout_suppressed" for r in trail)


def test_cron_rerun_creates_no_duplicate_plans(storage, audit_ledger):
    # Review point 2: Reruns must not create duplicate plans or duplicate dispatches
    provider = RuleDecisionProvider()
    proposer = ActionProposer(
        decision_provider=provider,
        action_storage=storage,
        audit_ledger=audit_ledger
    )

    # Non-holdout customer
    regular_customer = None
    for i in range(100):
        cid = f"cust_reg_{i}"
        if not provider._is_in_holdout("tenant_dominos", cid, holdout_pct=10):
            regular_customer = cid
            break

    signal_payload = {
        "session_id": "sess_regular",
        "customer_id": regular_customer,
        "cart_total_paise": 60000,
        "idle_minutes": 40
    }
    dedupe_key = f"idle_cart_sess_regular_{regular_customer}"

    # First run: Generates plan
    first_plans = proposer.propose_action_from_signal(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload=signal_payload,
        signal_dedupe_key=dedupe_key
    )
    assert len(first_plans) == 1
    plan_id = first_plans[0].plan_id

    # Second run (simulating next cron execution with exact same signal dedupe key):
    second_plans = proposer.propose_action_from_signal(
        tenant_id="tenant_dominos",
        signal_type="idle_cart",
        signal_payload=signal_payload,
        signal_dedupe_key=dedupe_key
    )
    # Must be empty! No duplicate plan drafted!
    assert len(second_plans) == 0

    # Plan in storage is still unique
    stored = storage.get_plan("tenant_dominos", plan_id)
    assert stored is not None
    assert stored.status == "drafted"
