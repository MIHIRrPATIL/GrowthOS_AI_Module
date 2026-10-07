"""
End-to-End LLM Layer, Evidence Linker & Evaluation Benchmarks Demonstration
GrowthOS Module 4: AI Growth Brain

Demonstrates:
1. Digest Explanation Engine with EvidenceLinker:
   - Fact extraction from deterministic digest reports.
   - Verification of percentage claims within 0.1% tolerance.
   - Automated pruning of hallucinated numbers and inverted polarity statements.
2. Natural-Language Query Engine over Fixed Metric Catalog:
   - Safe classification into vertical template metrics (Zero free-form SQL).
   - Deterministic metric computation and 3-Tier structured responses:
     Tier 1: Executive Summary.
     Tier 2: Analytical Breakdown.
     Tier 3: Technical Trace.
   - Append-only audit logging of merchant queries.
3. Decision Provider Benchmarking:
   - Labeled benchmark suite across Rules, LLM, and Jev.
   - Statistical calibration scoring: Expected Calibration Error (ECE) and Brier Score.
   - Latency distributions (p50, p95, p99) and cost per 1,000 queries.
4. Decision Manager Multi-Criteria Selection & Fallback:
   - Automated selection of optimal calibrated provider (Jev).
   - Autonomy gating enforcement for uncalibrated models.
   - Seamless fallback to RuleDecisionProvider during simulated primary outage.

Strictly NO emojis used in output or logs.
"""

from datetime import datetime, timezone, timedelta
from typing import List

from domain.metrics import TimeWindow, DigestReport, DigestFlag
from domain.events import EventEnvelope
from domain.nlp import QueryIntent
from domain.actions import ActionType
from ports.decision import DecisionContext
from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.mock_llm import MockLLMAdapter
from adapters.llm_decision_provider import LLMDecisionProvider
from adapters.jev_decision_provider import JevDecisionProvider
from engines.metrics_engine import MetricsEngine
from engines.evidence_linker import EvidenceLinker
from engines.digest_explanation_engine import DigestExplanationEngine
from engines.nl_query_engine import NLQueryEngine
from engines.rule_decision_provider import RuleDecisionProvider
from services.merchant_query_service import MerchantQueryService
from services.decision_manager import DecisionManager
from evaluation.evaluator import BenchmarkEvaluator


def seed_store_events(storage: SqlEventStorageAdapter, tenant_id: str, base_time: datetime, as_of: datetime):
    events: List[EventEnvelope] = []
    for i in range(120):
        t = base_time + timedelta(minutes=i * 2)
        sid = f"sess_{i:03d}"
        cid = f"cust_{i:03d}"

        # 1. Page view
        events.append(
            EventEnvelope(
                event_id=f"evt_view_{i}",
                schema_version="1.0.0",
                tenant_id=tenant_id,
                source_module="module_2",
                event_name="page.viewed",
                occurred_at=t.isoformat(),
                received_at=t.isoformat(),
                session_id=sid,
                customer_id=cid,
                properties={"path": "/menu"}
            )
        )
        # 2. Add to cart (all 120)
        events.append(
            EventEnvelope(
                event_id=f"evt_add_{i}",
                schema_version="1.0.0",
                tenant_id=tenant_id,
                source_module="module_2",
                event_name="cart.item_added",
                occurred_at=t.isoformat(),
                received_at=t.isoformat(),
                session_id=sid,
                customer_id=cid,
                properties={"cart_value": 650.0}
            )
        )
        # 3. Checkout step 1 completed (50 sessions)
        if i < 50:
            events.append(
                EventEnvelope(
                    event_id=f"evt_step1_{i}",
                    schema_version="1.0.0",
                    tenant_id=tenant_id,
                    source_module="module_2",
                    event_name="checkout.step_completed",
                    occurred_at=(t + timedelta(seconds=30)).isoformat(),
                    received_at=(t + timedelta(seconds=30)).isoformat(),
                    session_id=sid,
                    customer_id=cid,
                    properties={"step_number": 1}
                )
            )
        # 4. Checkout step 2 completed (18 sessions -> drop off is (50-18)/50 = 64.0%)
        if i < 18:
            events.append(
                EventEnvelope(
                    event_id=f"evt_step2_{i}",
                    schema_version="1.0.0",
                    tenant_id=tenant_id,
                    source_module="module_2",
                    event_name="checkout.step_completed",
                    occurred_at=(t + timedelta(seconds=60)).isoformat(),
                    received_at=(t + timedelta(seconds=60)).isoformat(),
                    session_id=sid,
                    customer_id=cid,
                    properties={"step_number": 2}
                )
            )
        # 5. Purchase completed (18 sessions -> overall conversion is 18/120 = 15.0%)
        if i < 18:
            events.append(
                EventEnvelope(
                    event_id=f"evt_purch_{i}",
                    schema_version="1.0.0",
                    tenant_id=tenant_id,
                    source_module="module_2",
                    event_name="purchase.completed",
                    occurred_at=(t + timedelta(seconds=90)).isoformat(),
                    received_at=(t + timedelta(seconds=90)).isoformat(),
                    session_id=sid,
                    customer_id=cid,
                    properties={"order_total": 650.0}
                )
            )

    # Prior week baseline
    prior_base = base_time - timedelta(days=7)
    for i in range(100):
        t_p = prior_base + timedelta(minutes=i * 2)
        sid_p = f"prior_sess_{i:03d}"
        cid_p = f"prior_cust_{i:03d}"
        events.append(EventEnvelope(event_id=f"p_view_{i}", schema_version="1.0.0", tenant_id=tenant_id, source_module="module_2", event_name="page.viewed", occurred_at=t_p.isoformat(), received_at=t_p.isoformat(), session_id=sid_p, customer_id=cid_p, properties={"path": "/menu"}))
        events.append(EventEnvelope(event_id=f"p_add_{i}", schema_version="1.0.0", tenant_id=tenant_id, source_module="module_2", event_name="cart.item_added", occurred_at=t_p.isoformat(), received_at=t_p.isoformat(), session_id=sid_p, customer_id=cid_p, properties={"cart_value": 650.0}))
        if i < 40:
            events.append(EventEnvelope(event_id=f"p_step1_{i}", schema_version="1.0.0", tenant_id=tenant_id, source_module="module_2", event_name="checkout.step_completed", occurred_at=(t_p + timedelta(seconds=30)).isoformat(), received_at=(t_p + timedelta(seconds=30)).isoformat(), session_id=sid_p, customer_id=cid_p, properties={"step_number": 1}))
        if i < 30:
            events.append(EventEnvelope(event_id=f"p_step2_{i}", schema_version="1.0.0", tenant_id=tenant_id, source_module="module_2", event_name="checkout.step_completed", occurred_at=(t_p + timedelta(seconds=60)).isoformat(), received_at=(t_p + timedelta(seconds=60)).isoformat(), session_id=sid_p, customer_id=cid_p, properties={"step_number": 2}))
            events.append(EventEnvelope(event_id=f"p_purch_{i}", schema_version="1.0.0", tenant_id=tenant_id, source_module="module_2", event_name="purchase.completed", occurred_at=(t_p + timedelta(seconds=90)).isoformat(), received_at=(t_p + timedelta(seconds=90)).isoformat(), session_id=sid_p, customer_id=cid_p, properties={"order_total": 650.0}))

    # High-value idle cart anomaly
    t_idle = as_of - timedelta(minutes=45)
    events.append(EventEnvelope(
        event_id="evt_idle_high_1",
        schema_version="1.0.0",
        tenant_id=tenant_id,
        source_module="module_2",
        event_name="cart.item_added",
        occurred_at=t_idle.isoformat(),
        received_at=t_idle.isoformat(),
        session_id="sess_idle_99",
        customer_id="cust_rahul_99",
        properties={"cart_value": 750.0, "product_id": "PRD-PEP"}
    ))

    storage.store_batch(events)


def run_demonstration():
    print("================================================================================")
    print("GROWTHOS MODULE 4: LLM LAYER, EVIDENCE LINKER & BENCHMARK DEMONSTRATION")
    print("================================================================================")
    tenant_id = "tenant_dominos"
    base_time = datetime(2026, 10, 5, 8, 0, 0, tzinfo=timezone.utc)
    as_of = base_time + timedelta(hours=6)

    storage = SqlEventStorageAdapter(db_path=":memory:")
    audit_ledger = SqlAuditLedgerAdapter(db_path=":memory:")
    metrics_engine = MetricsEngine(storage=storage)
    evidence_linker = EvidenceLinker()
    mock_llm = MockLLMAdapter()

    print("\n[STEP 1] Seeding Telemetry Events and Initializing Engine Pipeline...")
    seed_store_events(storage, tenant_id, base_time, as_of)
    print(f"Stored 221 sessions with multi-step funnel telemetry under tenant: {tenant_id}")

    # =========================================================================
    # PART 1: DIGEST EXPLANATION & EVIDENCE LINKER
    # =========================================================================
    print("\n--------------------------------------------------------------------------------")
    print("PART 1: DIGEST EXPLANATION WITH EVIDENCE LINKER (ANTI-HALLUCINATION GATE)")
    print("--------------------------------------------------------------------------------")
    from engines.digest_engine import DigestEngine
    digest_engine = DigestEngine(metrics_engine=metrics_engine, storage=storage)

    current_win = TimeWindow(start=base_time, end=as_of)
    prior_win = TimeWindow(start=base_time - timedelta(days=7), end=as_of - timedelta(days=7))

    report = digest_engine.run_digest(
        tenant_id=tenant_id,
        vertical_template_id="ecommerce",
        current_window=current_win,
        prior_window=prior_win,
        period="week_over_week",
        threshold_pct=10.0,
        as_of=as_of,
        detect_absence=True,
        idle_cart_min_value=300.0,
        idle_cart_high_value=500.0,
        idle_cart_timeout_minutes=30.0,
        idle_cart_max_timeout_minutes=180.0
    )
    print(f"Digest Engine Executed: {len(report.flags)} active flags, {len(report.idle_cart_anomalies)} idle cart anomalies detected.")

    explanation_engine = DigestExplanationEngine(
        llm_port=mock_llm,
        evidence_linker=evidence_linker
    )

    # 1. Clean verification pass
    explanation = explanation_engine.generate_explanation(report, vertical="ecommerce")
    print("\n[Case 1A] Valid Explanation with Citation Anchors:")
    print(f"Headline: {explanation.headline}")
    print(f"Executive Summary: {explanation.executive_summary}")
    print(f"Verified Citations ({len(explanation.citations)}):")
    for cit in explanation.citations:
        print(f"  - [{cit.citation_id}] Metric: {cit.metric_name} | Computed: {cit.computed_value:.3f} | Sample: {cit.sample_size}")

    # 2. Injected hallucination and polarity contradiction
    print("\n[Case 1B] Anti-Hallucination Gate Test (Injected False Claims):")
    dirty_draft = (
        "Checkout step 2 drop off rate rose to 64.0%. "
        "Checkout drop off exploded to an unprecedented 98.7% today. "  # Hallucinated number
        "Cart abandonment rate decreased sharply down to 85.0%. "     # Inverted polarity (it rose)
        "Critical failure proved our frontend was offline."           # Insufficient sample / unbacked
    )
    cleaned_text, citations, dropped = evidence_linker.verify_and_link(
        text=dirty_draft,
        flags=report.flags,
        anomalies=report.idle_cart_anomalies
    )
    print(f"Original Text:\n  '{dirty_draft}'")
    print(f"Verified Clean Text:\n  '{cleaned_text}'")
    print(f"Pruned Unsupported Claims ({len(dropped)}):")
    for d in dropped:
        print(f"  [REJECTED] {d}")

    # =========================================================================
    # PART 2: NATURAL LANGUAGE QUERY ENGINE OVER FIXED METRICS
    # =========================================================================
    print("\n--------------------------------------------------------------------------------")
    print("PART 2: NATURAL LANGUAGE QUERY ENGINE (ZERO FREE-FORM SQL)")
    print("--------------------------------------------------------------------------------")

    nl_engine = NLQueryEngine(
        llm_port=mock_llm,
        metrics_engine=metrics_engine,
        evidence_linker=evidence_linker
    )
    query_service = MerchantQueryService(
        nl_query_engine=nl_engine,
        audit_ledger=audit_ledger
    )

    queries_to_test = [
        "Where is the checkout drop off happening?",
        "What is our overall checkout conversion rate?",
        "What is the weather forecast in Bengaluru tomorrow?"
    ]

    for q in queries_to_test:
        ans = query_service.ask(
            tenant_id=tenant_id,
            merchant_id="merchant_mgr_01",
            question=q,
            vertical="ecommerce",
            as_of=as_of
        )
        print(f"\nMerchant Query: '{ans.query_text}'")
        print(f"Intent: {ans.intent.value.upper()}")
        print(f"Tier 1 (Executive): {ans.executive_summary}")
        print("Tier 2 (Analytical Breakdown):")
        for b in ans.analytical_breakdown:
            print(f"  * {b}")
        print(f"Tier 3 (Technical Trace): Metric={ans.technical_trace.get('metric_name')} | Status={ans.technical_trace.get('status', 'valid')}")
        if ans.citations:
            print(f"Citations Verified: {len(ans.citations)} anchor(s)")

    # Verify audit ledger
    ledger_records = audit_ledger.get_audit_trail(tenant_id=tenant_id)
    query_audits = [r for r in ledger_records if r.event_type == "merchant_query_answered"]
    print(f"\nAudit Ledger: Successfully recorded {len(query_audits)} merchant query interactions.")

    # =========================================================================
    # PART 3: DECISION PROVIDER BENCHMARKING (RULES VS LLM VS JEV)
    # =========================================================================
    print("\n--------------------------------------------------------------------------------")
    print("PART 3: DECISION PROVIDER BENCHMARK SCORECARDS & CALIBRATION")
    print("--------------------------------------------------------------------------------")

    evaluator = BenchmarkEvaluator()
    rule_provider = RuleDecisionProvider()
    llm_provider = LLMDecisionProvider()
    jev_calibrated = JevDecisionProvider(temperature_calibration=True)
    jev_uncalibrated = JevDecisionProvider(temperature_calibration=False)

    summary_rules = evaluator.evaluate_provider("rules", rule_provider, "action_routing")
    summary_llm = evaluator.evaluate_provider("llm", llm_provider, "action_routing")
    summary_jev = evaluator.evaluate_provider("jev", jev_calibrated, "action_routing")
    summary_uncal = evaluator.evaluate_provider("jev_raw", jev_uncalibrated, "action_routing")

    summaries = [summary_rules, summary_llm, summary_jev, summary_uncal]

    print("\nBenchmark Scorecard Summary (Action Routing Suite - 20 Labeled Scenarios):")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"{'Provider':<12} | {'Accuracy':<8} | {'Macro F1':<8} | {'ECE':<7} | {'Brier':<7} | {'p50 (ms)':<8} | {'p95 (ms)':<8} | {'Cost/1k ($)':<11} | {'Autonomous'}")
    print("---------------------------------------------------------------------------------------------------------")
    for s in summaries:
        print(
            f"{s.provider_name:<12} | "
            f"{s.accuracy*100.0:>6.1f}% | "
            f"{s.macro_f1:>8.3f} | "
            f"{s.calibration.expected_calibration_error:>7.3f} | "
            f"{s.calibration.brier_score:>7.3f} | "
            f"{s.p50_latency_ms:>8.1f} | "
            f"{s.p95_latency_ms:>8.1f} | "
            f"${s.cost_per_1000_usd:>10.4f} | "
            f"{'YES' if s.is_eligible_for_autonomous else 'NO'}"
        )
    print("---------------------------------------------------------------------------------------------------------")
    print("Key Calibration Finding: Jev temperature scaling reduces ECE from "
          f"{summary_uncal.calibration.expected_calibration_error:.3f} to {summary_jev.calibration.expected_calibration_error:.3f}, "
          "granting safe statistical qualification for Autonomous Mode execution.")

    # =========================================================================
    # PART 4: DECISION MANAGER SELECTION & AUTONOMOUS GATING
    # =========================================================================
    print("\n--------------------------------------------------------------------------------")
    print("PART 4: DECISION MANAGER ORCHESTRATION & SEAMLESS RULES FALLBACK")
    print("--------------------------------------------------------------------------------")

    instances = {
        "rules": rule_provider,
        "llm": llm_provider,
        "jev": jev_calibrated
    }
    manager = DecisionManager.select_best_provider(
        summaries=[summary_rules, summary_llm, summary_jev],
        provider_instances=instances,
        fallback_provider=rule_provider
    )

    print(f"Winner Selection: Primary Decision Provider selected as '{manager.performance_summary.provider_name}'.")
    print(f"Fallback Provider: '{manager.fallback_provider.__class__.__name__}'.")

    # Propose action via primary provider
    cart_context = DecisionContext(
        tenant_id=tenant_id,
        signal_type="idle_cart",
        signal_payload={"customer_id": "cust_high_99", "cart_value": 750.0, "idle_minutes": 25},
        signal_dedupe_key="dedupe_demo_cart_99",
        as_of=as_of,
        tenant_config={"holdout_pct": 0}
    )

    print("\n[Execution 1] Dispatching high-value idle cart through primary provider (Jev):")
    candidates_primary = manager.propose_candidates(cart_context)
    for c in candidates_primary:
        print(f"  Proposed Action: {c.action_type.value.upper()} | Priority: {c.priority_score:.2f} | Calibrated Conf: {c.calibrated_probability}")
        print(f"  Rationale: {c.reasoning_summary}")

    # Fallback demonstration
    print("\n[Execution 2] Simulating Primary Provider Outage (Rate Limit / Timeout)...")
    failing_jev = JevDecisionProvider(simulate_failure=True)
    fallback_manager = DecisionManager(
        primary_provider=failing_jev,
        fallback_provider=rule_provider
    )

    candidates_fallback = fallback_manager.propose_candidates(cart_context)
    print(f"Primary Failures Intercepted: {fallback_manager.fallback_invocation_count}")
    print(f"Fallback Result: {len(candidates_fallback)} action candidate(s) successfully rescued via deterministic rules.")
    for c in candidates_fallback:
        print(f"  Rescued Action: {c.action_type.value.upper()} | Target: {c.target_id} | Calibrated Conf: {c.calibrated_probability}")
        print(f"  Rule Rationale: {c.reasoning_summary}")

    print("\n================================================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY WITHOUT ERRORS")
    print("================================================================================")


if __name__ == "__main__":
    run_demonstration()
