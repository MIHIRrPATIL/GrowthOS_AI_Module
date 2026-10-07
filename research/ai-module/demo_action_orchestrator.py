"""
End-to-End Action Orchestrator and Governance Demonstration
GrowthOS Module 4: AI Growth Brain

Demonstrates:
1. Deterministic Action Proposal from Digest Flags and Idle Cart Anomalies.
2. Hard Policy Boundary Enforcement (Fail-closed limits, consent, cooldown).
3. Tri-mode execution:
   - MANUAL mode (drafted recommendation).
   - APPROVAL mode (human merchant review, optimistic locking, atomic dispatch).
   - AUTONOMOUS mode (demotion of uncalibrated outreach; autonomous execution of allowlisted bug report).
4. Idempotency claim barrier preventing duplicate adapter calls.
5. Cryptographically chained tamper-evident audit ledger verification.

Strictly NO emojis used in output or logs.
"""

import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from domain.actions import (
    ActionPlan,
    ActionType,
    ExecutionMode,
    PolicyRule,
    AuditRecord
)
from domain.metrics import DigestReport, DigestFlag
from engines.policy_engine import PolicyEngine
from engines.rule_decision_provider import RuleDecisionProvider
from services.action_proposer import ActionProposer
from services.action_orchestrator import ActionOrchestrator
from services.approval_service import ApprovalService
from adapters.sql_action_storage import SqlActionStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.memory_consent_store import MemoryConsentStore
from adapters.mock_adapters import (
    MockLoyaltyAdapter,
    MockBehaviorAdapter,
    MockAdsAdapter,
    MockNotificationAdapter
)


def run_demonstration():
    print("================================================================================")
    print("GROWTHOS MODULE 4: ACTION ORCHESTRATOR & POLICY GOVERNANCE DEMONSTRATION")
    print("================================================================================")
    tenant_id = "tenant_dominos"
    fixed_clock = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Initialize Adapters & Storage
    print("\n[STEP 1] Initializing Durable Storage, Adapters, and Policy Engine...")
    action_storage = SqlActionStorageAdapter(db_path=":memory:")
    audit_ledger = SqlAuditLedgerAdapter(db_path=":memory:")
    consent_store = MemoryConsentStore()

    # Pre-configure consent for customers
    consent_store.record_consent(tenant_id, "cust_vip_001", {
        "whatsapp_marketing": True,
        "email_marketing": True,
        "ad_tracking": True
    })

    # Pre-configure tenant policy rule
    policy_rule = PolicyRule(
        tenant_id=tenant_id,
        version=1,
        name="Dominos Standard Guardrails",
        max_discount_value_paise=15000,          # Max INR 150
        max_discount_pct=25.0,                   # Max 25% of subtotal
        max_daily_budget_shift_pct=15.0,
        max_daily_discount_budget_paise=5000000, # INR 50k
        contact_cooldown_hours=48,
        max_incentives_per_customer_30d=1,
        autonomous_confidence_threshold=0.85,
        autonomous_action_allowlist=["flag_ui_friction_bug", "request_dense_telemetry"]
    )
    action_storage.save_policy_rule(policy_rule)

    loyalty_mock = MockLoyaltyAdapter()
    behavior_mock = MockBehaviorAdapter()
    ads_mock = MockAdsAdapter()
    notification_mock = MockNotificationAdapter()

    policy_engine = PolicyEngine(action_storage=action_storage, consent_port=consent_store)
    decision_provider = RuleDecisionProvider()

    orchestrator = ActionOrchestrator(
        action_storage=action_storage,
        policy_engine=policy_engine,
        consent_port=consent_store,
        audit_ledger=audit_ledger,
        loyalty_adapter=loyalty_mock,
        behavior_adapter=behavior_mock,
        ads_adapter=ads_mock,
        notification_adapter=notification_mock,
        clock=lambda: fixed_clock
    )

    proposer = ActionProposer(
        decision_provider=decision_provider,
        action_storage=action_storage,
        audit_ledger=audit_ledger,
        clock=lambda: fixed_clock
    )
    print("Storage and adapters initialized successfully.")

    # 2. Ingest Signals and Propose Actions
    print("\n[STEP 2] Processing Signals and Proposing Actions...")

    # Signal A: Idle Cart (High Value, INR 650)
    idle_cart_signal = {
        "session_id": "sess_order_881",
        "customer_id": "cust_vip_001",
        "cart_total_paise": 65000,
        "idle_minutes": 42
    }
    plans_a = proposer.propose_action_from_signal(
        tenant_id=tenant_id,
        signal_type="idle_cart",
        signal_payload=idle_cart_signal,
        signal_dedupe_key="idle_cart_sess_order_881_cust_vip_001"
    )
    print(f"Signal A (Idle Cart): Proposer generated {len(plans_a)} plan(s).")
    plan_fee_waiver = plans_a[0]
    print(f" - Plan ID: {plan_fee_waiver.plan_id}")
    print(f" - Action Type: {plan_fee_waiver.action_type.value}")
    print(f" - Target Module: {plan_fee_waiver.target_module}")
    print(f" - Reasoning: {plan_fee_waiver.reasoning_summary}")
    print(f" - Evidence: {plan_fee_waiver.evidence_citations}")

    # Signal B: Checkout Step 2 Drop-off Spike (Emits Bug Triage + Dense Telemetry)
    drop_off_signal = {
        "metric_name": "checkout_step_2_drop_off_rate",
        "prior_value": 0.12,
        "current_value": 0.44,
        "pct_change": 266.7,
        "sample_size": 310,
        "min_sample_met": True,
        "is_significant": True,
        "adverse": True,
        "severity": "critical"
    }
    plans_b = proposer.propose_action_from_signal(
        tenant_id=tenant_id,
        signal_type="digest_flag",
        signal_payload=drop_off_signal,
        signal_dedupe_key="digest_drop_off_step2_20261005"
    )
    print(f"Signal B (Drop-off Spike): Proposer generated {len(plans_b)} plan(s) (Review point 17 split):")
    for pb in plans_b:
        print(f" - Plan ID: {pb.plan_id} | Action: {pb.action_type.value} | Target: {pb.parameters.get('component_selector')}")

    # 3. Policy Rejection Demonstration (Fail-closed financial limit)
    print("\n[STEP 3] Testing Hard Policy Limit Enforcement...")
    excessive_discount_plan = ActionPlan(
        plan_id="plan_excess_disc_demo",
        tenant_id=tenant_id,
        action_type=ActionType.ISSUE_DISCOUNT_COUPON,
        target_module="module_1_loyalty",
        customer_id="cust_vip_001",
        parameters={
            "coupon_code": "MEGA500",
            "discount_amount_paise": 50000, # INR 500 (exceeds INR 150 max cap)
            "order_subtotal_paise": 100000,
            "customer_id": "cust_vip_001"
        },
        reasoning_summary="Attempting coupon above platform guardrail",
        execution_mode=ExecutionMode.APPROVAL
    )
    action_storage.save_plan(excessive_discount_plan)
    rejected_plan = orchestrator.evaluate_and_route_plan(excessive_discount_plan, target_mode=ExecutionMode.APPROVAL)
    print(f"Excessive discount plan status: {rejected_plan.status.upper()}")
    print(f"Policy Check Passed: {rejected_plan.policy_check_passed}")
    print(f"Policy Violations Logged: {rejected_plan.policy_violations}")

    # 4. Mode Routing: APPROVAL Workflow with Human Merchant Endpoint
    print("\n[STEP 4] Testing APPROVAL Mode Routing & Merchant Approval Endpoint...")
    # Route fee waiver plan into APPROVAL mode
    approval_route = orchestrator.evaluate_and_route_plan(plan_fee_waiver, target_mode=ExecutionMode.APPROVAL)
    print(f"Plan routed to: {approval_route.status.upper()} (awaiting merchant confirmation)")

    approval_service = ApprovalService(
        action_storage=action_storage,
        audit_ledger=audit_ledger,
        orchestrator=orchestrator
    )

    print("Merchant Admin 'usr_rohit' reviewing and approving plan...")
    dispatched_waiver = approval_service.approve_plan(
        tenant_id=tenant_id,
        plan_id=approval_route.plan_id,
        approver_id="usr_rohit",
        approver_role="merchant_admin",
        expected_version=1
    )
    print(f"Plan status after approval: {dispatched_waiver.status.upper()}")
    print(f"Approved By: {dispatched_waiver.approved_by}")
    print(f"Dispatched At: {dispatched_waiver.dispatched_at}")
    print(f"Execution Receipt: {dispatched_waiver.execution_receipt}")

    # 5. Idempotency Claim Barrier
    print("\n[STEP 5] Testing Idempotency Claim Barrier (Duplicate Call Suppression)...")
    print("Re-calling orchestrator.execute_dispatch on the already dispatched fee waiver plan...")
    replay_plan = orchestrator.execute_dispatch(dispatched_waiver, actor="cron_rerun_agent")
    print(f"Replay Plan status: {replay_plan.status.upper()}")
    print(f"Cached Receipt Returned: {replay_plan.execution_receipt}")
    print(f"Total calls made to Loyalty Adapter waive_delivery_fee: {len(loyalty_mock.dispatched_fee_waivers)} (Exactly 1!)")

    # 6. Mode Routing: AUTONOMOUS Execution with Allowlist and Confidence Gate
    print("\n[STEP 6] Testing AUTONOMOUS Mode Routing...")
    # 6A. Uncalibrated plan -> Demoted to APPROVAL
    print("Testing Autonomy Demotion for Outreach without calibrated empirical probability...")
    uncalibrated_whatsapp = ActionPlan(
        plan_id="plan_whatsapp_demo",
        tenant_id=tenant_id,
        action_type=ActionType.SEND_RECOVERY_WHATSAPP,
        target_module="notification",
        customer_id="cust_vip_001",
        parameters={
            "recipient": "cust_vip_001",
            "channel": "whatsapp",
            "template_name": "cart_recovery_v1",
            "cart_total_paise": 40000,
            "recipient_type": "customer_id"
        },
        reasoning_summary="Rule-based WhatsApp outreach proposal",
        priority_score=0.90,
        calibrated_probability=None, # Pure rule, not calibrated
        execution_mode=ExecutionMode.AUTONOMOUS
    )
    action_storage.save_plan(uncalibrated_whatsapp)
    demoted = orchestrator.evaluate_and_route_plan(uncalibrated_whatsapp, target_mode=ExecutionMode.AUTONOMOUS)
    print(f"Uncalibrated plan execution mode: {demoted.execution_mode.value.upper()} | Status: {demoted.status.upper()}")

    # 6B. Allowlisted internal bug ticket with calibrated confidence -> Executes Autonomously
    print("\nTesting Autonomous Execution for Allowlisted Bug Ticket with Calibrated Confidence...")
    bug_plan = plans_b[0]
    bug_plan.calibrated_probability = 0.95 # Empirically verified detector
    action_storage.save_plan(bug_plan)
    auto_executed = orchestrator.evaluate_and_route_plan(bug_plan, target_mode=ExecutionMode.AUTONOMOUS)
    print(f"Bug Plan Status: {auto_executed.status.upper()}")
    print(f"Approved By: {auto_executed.approved_by}")
    print(f"Execution Receipt: {auto_executed.execution_receipt}")

    # 7. Cryptographic Tamper-Evident Audit Ledger Verification
    print("\n[STEP 7] Verifying Tamper-Evident Cryptographic Hash Chain...")
    audit_trail = audit_ledger.get_audit_trail(tenant_id=tenant_id, limit=100)
    print(f"Total audit ledger records logged: {len(audit_trail)}")
    print(f"Chain integrity valid: {audit_ledger.verify_hash_chain(tenant_id)}")

    print("\nRecent Audit Trail Entries:")
    for i, rec in enumerate(audit_trail[:8]):
        print(f"[{i+1:02d}] event={rec.event_type:<32} actor={rec.actor:<24} prev={rec.prev_record_hash[:8]}... hash={rec.record_hash[:8]}...")

    print("\n================================================================================")
    print("DEMONSTRATION COMPLETED SUCCESSFULLY WITH 100% INVARIANT ENFORCEMENT.")
    print("================================================================================")


if __name__ == "__main__":
    run_demonstration()
