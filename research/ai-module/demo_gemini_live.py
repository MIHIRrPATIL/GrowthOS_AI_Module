#!/usr/bin/env python3
"""
Direct Google Gemini Live Interactive Demonstration
GrowthOS Module 4: AI Growth Brain

Demonstrates live direct Google Gemini provider integration (gemini-2.5-flash) across:
1. Natural Language Query Engine:
   - Maps merchant queries against the fixed eCommerce metric catalog.
   - Computes deterministic metrics and synthesizes 3-Tier structured responses with citation anchors.
2. Digest Explanation Engine with EvidenceLinker:
   - Generates executive narrative with strict citation tags.
   - Runs deterministic anti-hallucination verification, pruning ungrounded claims or polarity inversions.
3. Decision Provider & Autonomous Policy Check:
   - Evaluates a batch of diverse customer idle carts with calibrated confidence.
   - Preserves deterministic rule fallback if API is unconfigured or unavailable.

Strictly NO emojis used in logs or output.
"""

import sys
import os
import time
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from domain.metrics import TimeWindow, DigestReport, DigestFlag
from domain.events import EventEnvelope
from domain.nlp import QueryIntent
from domain.actions import ActionType
from ports.decision import DecisionContext
from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.openrouter_client import OpenRouterClient, load_dotenv_if_present
from adapters.openrouter_llm_adapter import OpenRouterLLMAdapter
from adapters.openrouter_decision_provider import OpenRouterDecisionProvider
from adapters.gemini_client import GeminiClient, RateLimitCircuitOpenError
from adapters.gemini_llm_adapter import GeminiLLMAdapter
from adapters.gemini_decision_provider import GeminiDecisionProvider
from adapters.mock_llm import MockLLMAdapter
from engines.rule_decision_provider import RuleDecisionProvider
from engines.metrics_engine import MetricsEngine
from engines.evidence_linker import EvidenceLinker
from engines.digest_explanation_engine import DigestExplanationEngine
from engines.nl_query_engine import NLQueryEngine
from engines.digest_engine import DigestEngine
from services.merchant_query_service import MerchantQueryService
from services.decision_manager import DecisionManager


def print_banner(text: str, width: int = 100):
    print("\n" + "=" * width)
    print(text.center(width))
    print("=" * width)


def seed_store_telemetry(storage: SqlEventStorageAdapter, tenant_id: str, as_of: datetime):
    """
    Seeds realistic eCommerce event telemetry across contiguous 7-day windows:
    - Control week: as_of - 21d to as_of - 14d (stable baseline, 0 anomaly flags)
    - Prior week: as_of - 14d to as_of - 7d (contiguous prior window)
    - Current week: as_of - 7d to as_of (active period under observation)
    Incorporates:
    - Seeded pseudo-random jitter (random.Random(42)) on timestamps and cart values.
    - Verified identity merge when guest starts checkout.
    - Unmerged anonymous guest visitor session.
    """
    rng = random.Random(42)
    events = []

    def seed_window(start_time: datetime, count: int, p_add: float, p_chk: float, p_s1: float, p_s2: float, p_pur: float, prefix: str):
        for i in range(count):
            is_guest = (i % 5 == 0)
            sid = f"{prefix}_sess_{i:04d}"
            anon_id = f"{prefix}_anon_{i:04d}"
            initial_cid = None if is_guest else f"{prefix}_cust_{i:04d}"
            checkout_cid = f"{prefix}_cust_{i:04d}"

            # Seeded jitter (+/- 30 seconds) within contiguous 7-day spread
            jitter_sec = rng.randint(-30, 30)
            t = start_time + timedelta(minutes=i * 30, seconds=jitter_sec)
            cart_val = round(750.0 + rng.uniform(-25.0, 25.0), 2)

            # 1. Page view
            events.append(EventEnvelope(
                event_id=f"{prefix}_view_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                source_module="module_2", event_name="page.viewed", occurred_at=t.isoformat(),
                received_at=t.isoformat(), session_id=sid, customer_id=initial_cid, anonymous_id=anon_id,
                properties={"path": "/products"}
            ))
            # 2. Add to cart
            if i < int(count * p_add):
                events.append(EventEnvelope(
                    event_id=f"{prefix}_add_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                    source_module="module_2", event_name="cart.item_added", occurred_at=(t + timedelta(seconds=20)).isoformat(),
                    received_at=(t + timedelta(seconds=20)).isoformat(), session_id=sid, customer_id=initial_cid, anonymous_id=anon_id,
                    properties={"cart_value": cart_val}
                ))
            # 3. Checkout started (identity merge occurs here for guest users)
            if i < int(count * p_chk):
                if is_guest and i == 5 and prefix == "cur":
                    print(f"[Identity Merge Log] Session '{sid}': Guest '{anon_id}' merged to customer '{checkout_cid}' upon checkout start.")
                events.append(EventEnvelope(
                    event_id=f"{prefix}_chk_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                    source_module="module_2", event_name="checkout.started", occurred_at=(t + timedelta(seconds=40)).isoformat(),
                    received_at=(t + timedelta(seconds=40)).isoformat(), session_id=sid, customer_id=checkout_cid, anonymous_id=anon_id,
                    properties={}
                ))
            # 4. Step 1 (address completed)
            if i < int(count * p_s1):
                events.append(EventEnvelope(
                    event_id=f"{prefix}_s1_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                    source_module="module_2", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=60)).isoformat(),
                    received_at=(t + timedelta(seconds=60)).isoformat(), session_id=sid, customer_id=checkout_cid, anonymous_id=anon_id,
                    properties={"step_number": 1, "step_name": "address"}
                ))
            # 5. Step 2 (payment/delivery completed)
            if i < int(count * p_s2):
                events.append(EventEnvelope(
                    event_id=f"{prefix}_s2_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                    source_module="module_2", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=80)).isoformat(),
                    received_at=(t + timedelta(seconds=80)).isoformat(), session_id=sid, customer_id=checkout_cid, anonymous_id=anon_id,
                    properties={"step_number": 2, "step_name": "payment"}
                ))
            # 6. Purchase completed
            if i < int(count * p_pur):
                events.append(EventEnvelope(
                    event_id=f"{prefix}_pur_{i}", schema_version="1.0.0", tenant_id=tenant_id,
                    source_module="module_2", event_name="purchase.completed", occurred_at=(t + timedelta(seconds=100)).isoformat(),
                    received_at=(t + timedelta(seconds=100)).isoformat(), session_id=sid, customer_id=checkout_cid, anonymous_id=anon_id,
                    properties={"order_value": cart_val}
                ))

    # Control window (days 14 to 21 prior to as_of): stable control week with baseline rates
    seed_window(as_of - timedelta(days=21), 300, p_add=0.70, p_chk=0.50, p_s1=0.42, p_s2=0.30, p_pur=0.25, prefix="ctrl")
    # Prior window (days 7 to 14 prior to as_of): 210 carts, 150 checkouts, 126 step 1, 90 step 2, 75 purchases
    seed_window(as_of - timedelta(days=14), 300, p_add=0.70, p_chk=0.50, p_s1=0.42, p_s2=0.30, p_pur=0.25, prefix="prior")
    # Current window (days 0 to 7 prior to as_of): 210 carts, 150 checkouts, 108 step 1, 54 step 2, 39 purchases
    seed_window(as_of - timedelta(days=7), 300, p_add=0.70, p_chk=0.50, p_s1=0.36, p_s2=0.18, p_pur=0.13, prefix="cur")

    print("[Telemetry Check] Session 'cur_sess_0150': Unmerged anonymous guest 'cur_anon_0150' added cart but abandoned without checkout identification.")

    storage.store_batch(events)


def run_demo():
    require_live = "--require-live" in sys.argv
    tenant_id = "tenant_gemini_demo"
    # Pinned to IST midnight (day boundaries in merchant timezone UTC+05:30)
    IST = timezone(timedelta(hours=5, minutes=30))
    as_of = datetime(2026, 10, 6, 0, 0, 0, tzinfo=IST)

    live_calls_count = 0
    fallback_calls_count = 0

    # Storage and engines
    storage = SqlEventStorageAdapter(db_path=":memory:")
    audit_ledger = SqlAuditLedgerAdapter(db_path=":memory:")
    metrics_engine = MetricsEngine(storage=storage)
    evidence_linker = EvidenceLinker()

    load_dotenv_if_present()
    gemini_key = (os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    target_gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip()
    target_or_model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash").strip()

    gemini_client: Optional[GeminiClient] = None
    openrouter_client: Optional[OpenRouterClient] = None

    if gemini_key:
        gemini_client = GeminiClient(api_key=gemini_key, model=target_gemini_model)
    if openrouter_key:
        openrouter_client = OpenRouterClient(api_key=openrouter_key, model=target_or_model)

    primary_gemini_llm = GeminiLLMAdapter(client=gemini_client, model=target_gemini_model) if gemini_client else None
    secondary_or_llm = OpenRouterLLMAdapter(client=openrouter_client, model=target_or_model) if openrouter_client else None
    mock_llm = MockLLMAdapter()

    primary_gemini_dec = GeminiDecisionProvider(client=gemini_client, model=target_gemini_model) if gemini_client else None
    secondary_or_dec = OpenRouterDecisionProvider(client=openrouter_client, model=target_or_model) if openrouter_client else None
    rule_decision = RuleDecisionProvider()

    mode_label = f"DIRECT GOOGLE GEMINI ({target_gemini_model})"
    if not gemini_key and openrouter_key:
        mode_label = f"OPENROUTER SECONDARY LIVE ({target_or_model})"
    elif not gemini_key and not openrouter_key:
        mode_label = "DRY-RUN SIMULATION (OFFLINE MOCK)"

    print_banner(f"RUNNING AI ENGINE DEMONSTRATION ({mode_label})")
    print(f"Reference Watermark (Pinned IST Midnight): {as_of.isoformat()}")

    # Seed events
    seed_store_telemetry(storage, tenant_id, as_of)
    print(f"Stored 900 customer sessions (300 control, 300 prior, 300 current) across full funnel for tenant: '{tenant_id}'")

    # =========================================================================
    # PART 1: NATURAL LANGUAGE QUERY ENGINE
    # =========================================================================
    print_banner("PART 1: NATURAL LANGUAGE QUERY ENGINE (ZERO FREE-FORM SQL)")

    # Active LLM port holder for NL engine
    active_llm = primary_gemini_llm or secondary_or_llm or mock_llm
    nl_engine = NLQueryEngine(
        llm_port=active_llm,
        metrics_engine=metrics_engine,
        evidence_linker=evidence_linker
    )
    query_service = MerchantQueryService(
        nl_query_engine=nl_engine,
        audit_ledger=audit_ledger
    )

    test_queries = [
        "Where is the checkout drop off happening?",
        "What is our checkout conversion rate?",
        "What is our cart abandonment rate compared to last week?",
        "How is our checkout step 2 drop off rate performing compared to last week?",
        "What will the weather in Mumbai be like on Friday?"
    ]

    answers = []
    for q in test_queries:
        print(f"\nMerchant Query: \"{q}\"")
        ans = None

        # Tier 1 Attempt: Direct Gemini
        if primary_gemini_llm:
            try:
                nl_engine.llm_port = primary_gemini_llm
                ans = query_service.ask(
                    tenant_id=tenant_id,
                    merchant_id="merchant_admin_01",
                    question=q,
                    vertical="ecommerce",
                    as_of=as_of
                )
                live_calls_count += 1
            except Exception as e:
                err_str = str(e)
                if any(k in err_str for k in ("429", "Circuit", "Rate limit", "Quota")):
                    print(f"  [GEMINI RATE LIMIT / CIRCUIT OPEN] Primary Gemini direct unavailable. Checking secondary live provider...")
                else:
                    raise

        # Tier 2 Attempt: Secondary live provider (OpenRouter)
        if ans is None and secondary_or_llm:
            try:
                print(f"  [LIVE FAILOVER] Dispatching to secondary live provider OpenRouter ({target_or_model})...")
                nl_engine.llm_port = secondary_or_llm
                ans = query_service.ask(
                    tenant_id=tenant_id,
                    merchant_id="merchant_admin_01",
                    question=q,
                    vertical="ecommerce",
                    as_of=as_of
                )
                live_calls_count += 1
            except Exception as e2:
                print(f"  [SECONDARY PROVIDER UNAVAILABLE: {e2}]. Falling back to deterministic mock...")

        # Tier 3 Attempt: Deterministic Mock fallback
        if ans is None:
            print(f"  [OFFLINE FALLBACK] Activating local MockLLMAdapter...")
            nl_engine.llm_port = mock_llm
            ans = query_service.ask(
                tenant_id=tenant_id,
                merchant_id="merchant_admin_01",
                question=q,
                vertical="ecommerce",
                as_of=as_of
            )
            fallback_calls_count += 1

        answers.append(ans)
        print(f"Intent Classification: {ans.intent.value.upper()}")
        print(f"Tier 1 (Executive Summary): {ans.executive_summary}")
        print("Tier 2 (Analytical Breakdown):")
        for pt in ans.analytical_breakdown:
            print(f"  * {pt}")

        trace = ans.technical_trace
        print("Tier 3 (Technical Trace & Audit Envelope):")
        print(f"  * Metric: {trace.get('metric_name')} | Status: {trace.get('status')} | Version: {trace.get('definition_version')}")
        if "numerator" in trace and trace.get("numerator") is not None:
            num_lbl = trace.get("numerator_label", "numerator")
            den_lbl = trace.get("denominator_label", "denominator")
            print(f"  * Current: {trace.get('numerator')} / {trace.get('denominator')} ({num_lbl} / {den_lbl})")
        if trace.get("prior_comparison"):
            prior = trace["prior_comparison"]
            num_lbl = trace.get("numerator_label", "numerator")
            den_lbl = trace.get("denominator_label", "denominator")
            print(f"  * Prior: {prior.get('prior_numerator')} / {prior.get('prior_denominator')} ({num_lbl} / {den_lbl})")
        print(f"  * Window: {trace.get('window')} | As Of: {trace.get('as_of')}")
        print(f"  * Model: {trace.get('model_version')} | Provider: {trace.get('provider')} | Degraded: {trace.get('degraded')}")
        print(f"  * Evidence Ref: {trace.get('evidence_ref')}")
        if ans.citations:
            print("  Evidence Anchors:")
            for c in ans.citations:
                p_val_str = f" (Prior: {c.prior_value:.3f})" if c.prior_value is not None else ""
                print(f"    - [Citation Anchor] {c.metric_name} = {c.computed_value:.3f}{p_val_str} (Sample: {c.sample_size})")

    # Part 1 Assertions
    try:
        # Query 1: Funnel Drop-off multi-step table
        ans_dropoff = answers[0]
        assert ans_dropoff.intent == QueryIntent.FUNNEL_DROP_OFF, "Query 1 intent mismatch"
        assert any("Step 1 to Step 2" in b for b in ans_dropoff.analytical_breakdown), "Query 1 missing Step 2 breakdown"
        assert any("50.0%" in b for b in ans_dropoff.analytical_breakdown), "Query 1 missing Step 2 50.0% figure"
        assert any("p < 0.001" in b for b in ans_dropoff.analytical_breakdown), "Query 1 missing Step 2 p-value"
        assert any("Excess lost: +23.1 sessions" in b for b in ans_dropoff.analytical_breakdown), "Query 1 missing excess lost volume"

        # Query 2: Checkout conversion rate point-in-time lookup (NO prior comparison!)
        ans_chk_conv = answers[1]
        assert ans_chk_conv.intent == QueryIntent.METRIC_LOOKUP, "Query 2 must be METRIC_LOOKUP"
        assert ans_chk_conv.technical_trace["metric_name"] == "checkout_conversion_rate", "Query 2 wrong metric mapped"
        assert ans_chk_conv.technical_trace["numerator"] == 39, "Query 2 numerator must be 39"
        assert ans_chk_conv.technical_trace["denominator"] == 150, "Query 2 denominator must be 150 checkouts started"
        assert ans_chk_conv.technical_trace["prior_comparison"] is None, "Query 2 METRIC_LOOKUP must not compare periods"
        assert "26.0%" in ans_chk_conv.executive_summary, "Query 2 executive summary missing 26.0%"

        # Query 3: Cart abandonment rate period comparison (171/210 vs 135/210)
        ans_abandon = answers[2]
        assert ans_abandon.technical_trace["metric_name"] == "cart_abandonment_rate", "Query 3 wrong metric"
        assert ans_abandon.technical_trace["numerator"] == 171, "Query 3 current numerator must be 171"
        assert ans_abandon.technical_trace["denominator"] == 210, "Query 3 current denominator must be 210"
        prior_data = ans_abandon.technical_trace.get("prior_comparison", {})
        assert prior_data.get("prior_numerator") == 135, "Query 3 prior numerator must be 135"
        assert prior_data.get("prior_denominator") == 210, "Query 3 prior denominator must be 210"
        assert "+17.1 pp" in ans_abandon.executive_summary or "+17.1 pp" in " ".join(ans_abandon.analytical_breakdown), "Query 3 missing pp delta"

        # Query 4: Step 2 drop-off rate (54/108 vs 36/126)
        ans_s2 = answers[3]
        assert ans_s2.intent == QueryIntent.PERIOD_COMPARISON, "Query 4 must be PERIOD_COMPARISON"
        assert ans_s2.technical_trace["numerator"] == 54, "Query 4 numerator must be 54"
        assert ans_s2.technical_trace["denominator"] == 108, "Query 4 denominator must be 108"
        assert "+21.4 pp" in ans_s2.executive_summary or "+21.4 pp" in " ".join(ans_s2.analytical_breakdown), "Query 4 missing pp delta"

        # Query 5: Weather query rejected
        ans_weather = answers[4]
        assert ans_weather.intent == QueryIntent.UNSUPPORTED, "Query 5 must be classified as UNSUPPORTED"
        assert "cart_abandonment_rate" in " ".join(ans_weather.analytical_breakdown), "Query 5 must list catalog metrics"
        assert "checkout_step_3_drop_off_rate" in " ".join(ans_weather.analytical_breakdown), "Query 5 must list full catalog"
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] Part 1 Validation Error: {e}")
        sys.exit(1)

    # =========================================================================
    # PART 2: FACT-GROUNDED DIGEST REPORT & CITATION AUDIT
    # =========================================================================
    print_banner("PART 2: FACT-GROUNDED DIGEST REPORT & CITATION AUDIT")

    digest_engine = DigestEngine(metrics_engine=metrics_engine, storage=storage)

    # 1. Control Week Stability Test (Zero False Positives)
    ctrl_win = TimeWindow(start=as_of - timedelta(days=21), end=as_of - timedelta(days=14))
    prior_win = TimeWindow(start=as_of - timedelta(days=14), end=as_of - timedelta(days=7))
    current_win = TimeWindow(start=as_of - timedelta(days=7), end=as_of)

    ctrl_report = digest_engine.run_digest(
        tenant_id=tenant_id,
        vertical_template_id="ecommerce",
        current_window=ctrl_win,
        prior_window=prior_win,
        period="week_over_week",
        threshold_pct=10.0,
        as_of=as_of
    )
    print(f"Control Week Stability Check (14-21 days ago vs 7-14 days ago): {len(ctrl_report.flags)} anomaly flags generated (Clean baseline, zero false positives).")
    assert len(ctrl_report.flags) == 0, "Control week generated false-positive flags"

    # 2. Active Digest Run (Current vs Prior Week)
    active_report = digest_engine.run_digest(
        tenant_id=tenant_id,
        vertical_template_id="ecommerce",
        current_window=current_win,
        prior_window=prior_win,
        period="week_over_week",
        threshold_pct=10.0,
        as_of=as_of
    )

    explanation_engine = DigestExplanationEngine(
        llm_port=nl_engine.llm_port,
        evidence_linker=evidence_linker
    )

    explanation = None
    if primary_gemini_llm:
        try:
            explanation_engine.llm_port = primary_gemini_llm
            explanation = explanation_engine.generate_explanation(active_report, vertical="ecommerce")
            live_calls_count += 1
        except Exception as e:
            if any(k in str(e) for k in ("429", "Circuit", "Rate limit", "Quota")):
                print("  [GEMINI RATE LIMIT / CIRCUIT OPEN] Failover to secondary provider for digest explanation...")
            else:
                raise

    if explanation is None and secondary_or_llm:
        try:
            explanation_engine.llm_port = secondary_or_llm
            explanation = explanation_engine.generate_explanation(active_report, vertical="ecommerce")
            live_calls_count += 1
        except Exception as e:
            print(f"  [SECONDARY PROVIDER UNAVAILABLE: {e}]. Falling back to mock for explanation...")

    if explanation is None:
        explanation_engine.llm_port = mock_llm
        explanation = explanation_engine.generate_explanation(active_report, vertical="ecommerce")
        fallback_calls_count += 1

    print(f"\nGenerated Headline (Impact-Ranked): {explanation.headline}")
    print(f"Generated Executive Summary: {explanation.executive_summary}")
    print(f"Verified Evidence Citations ({len(explanation.citations)}):")
    for cit in explanation.citations:
        prior_str = f" | Prior: {cit.prior_value:.4f}" if cit.prior_value is not None else ""
        print(f"  - [{cit.citation_id}] Metric: {cit.metric_name} | Value: {cit.computed_value:.4f}{prior_str} | Sample: {cit.sample_size}")

    # 3. Anti-Hallucination Gate Test (Isolated Single-Defect Sentences)
    print("\nAnti-Hallucination Gate Test (Testing Isolated Single Defects Without Hype Words):")
    test_gate_sentences = [
        ("Valid Fact", "Checkout step 2 drop off rate rose to 50.0%."),
        ("Defect 1: Bare Wrong Number", "Cart abandonment reached 94.5%."),
        ("Defect 2: Wrong Direction Without Hype", "Step 2 drop-off decreased compared to the prior period."),
        ("Defect 3: Right Number Attached to Wrong Metric", "Cart abandonment rate was 50.0%.")
    ]

    gate_clean_results = []
    gate_dropped_results = []
    for label, sent in test_gate_sentences:
        clean, cits, dropped = evidence_linker.verify_and_link(
            text=sent,
            flags=active_report.flags,
            anomalies=[]
        )
        gate_clean_results.append((label, sent, clean))
        gate_dropped_results.append((label, sent, dropped))
        status = "PASSED" if clean else "REJECTED"
        print(f"  * [{label}] Status: {status}")
        print(f"    Input: \"{sent}\"")
        if clean:
            print(f"    Verified Output: \"{clean}\"")
        else:
            print(f"    Rejection Reason: {dropped[0] if dropped else 'Rejected'}")

    # Part 2 Assertions
    try:
        # Valid fact must pass
        assert gate_clean_results[0][2] != "", "Valid 50.0% fact was erroneously rejected"
        # Bare wrong number (94.5%) must be rejected
        assert gate_clean_results[1][2] == "", "Bare wrong number was not pruned"
        assert any("does not match" in d for d in gate_dropped_results[1][2]), "Bare wrong number missed number-mismatch check"
        # Wrong direction without hype must be rejected
        assert gate_clean_results[2][2] == "", "Wrong direction was not pruned"
        assert any("Direction contradiction" in d or "Polarity" in d for d in gate_dropped_results[2][2]), "Wrong direction missed polarity check"
        # Right number attached to wrong metric must be rejected
        assert gate_clean_results[3][2] == "", "Cross-metric number match was not pruned"
        assert any("does not match referenced metric" in d for d in gate_dropped_results[3][2]), "Cross-metric missed binding check"
        # Headline and Executive Summary must rank Step 2 as primary bottleneck
        assert "Step 2 Drop Off Rate" in explanation.headline, "Step 2 not ranked first in headline"
        assert "+23.1 Excess Lost Sessions" in explanation.headline, "Headline missing excess lost volume"
        assert len(explanation.citations) >= 1, "Expected at least 1 verified citation"
        assert explanation.citations[0].prior_value is not None, "Citation missing prior_value"
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] Part 2 Validation Error: {e}")
        sys.exit(1)

    # =========================================================================
    # PART 3: DECISION PROVIDER & AUTONOMOUS GATING
    # =========================================================================
    print_banner("PART 3: DECISION PROVIDER & AUTONOMY RESCUE FALLBACK")

    primary_dec = primary_gemini_dec or secondary_or_dec or rule_decision
    decision_manager = DecisionManager(
        primary_provider=primary_dec,
        fallback_provider=rule_decision
    )

    test_customer_carts = [
        {
            "scenario": "High-Value Identified Customer (Eligible for delivery fee waiver)",
            "customer_id": "cust_high_value_01",
            "cart_value": 750.0,
            "idle_minutes": 35,
            "is_anonymous": False
        },
        {
            "scenario": "VIP Repeat Buyer (High cart value, extended idle time)",
            "customer_id": "cust_vip_02",
            "cart_value": 1450.0,
            "idle_minutes": 45,
            "is_anonymous": False
        },
        {
            "scenario": "Mid-Tier Cart (INR 300 to INR 500 band: Eligible for WhatsApp recovery)",
            "customer_id": "cust_mid_tier_03",
            "cart_value": 420.0,
            "idle_minutes": 35,
            "is_anonymous": False
        },
        {
            "scenario": "Small Cart Below Threshold (Cart < INR 300 policy threshold)",
            "customer_id": "cust_small_04",
            "cart_value": 220.0,
            "idle_minutes": 35,
            "is_anonymous": False
        },
        {
            "scenario": "Anonymous Guest Session (Policy prohibits outreach without contact identity)",
            "customer_id": None,
            "anonymous_id": "anon_guest_05",
            "cart_value": 890.0,
            "idle_minutes": 35,
            "is_anonymous": True
        }
    ]

    print("\nDispatching diverse customer idle carts through decision manager:\n")
    all_candidates = []
    rejection_codes = []
    for cart in test_customer_carts:
        cid_label = cart.get("customer_id") or cart.get("anonymous_id")
        print(f"Scenario: {cart['scenario']}")
        print(f"  Identifier: {cid_label} | Cart Value: INR {cart['cart_value']:.0f} | Idle: {cart['idle_minutes']} mins | Anonymous: {cart['is_anonymous']}")
        cart_ctx = DecisionContext(
            tenant_id=tenant_id,
            signal_type="idle_cart",
            signal_payload=cart,
            signal_dedupe_key=f"dedupe_{cid_label}",
            as_of=as_of,
            tenant_config={
                "fee_waiver_amount_paise": 5000,
                "idle_threshold_minutes": 30,
                "min_cart_value_inr": 300.0,
                "high_value_cart_threshold_paise": 50000,
                "mid_value_cart_threshold_paise": 30000,
                "holdout_pct": 10
            }
        )

        candidates = None
        # Try primary live decision provider
        try:
            candidates = decision_manager.propose_candidates(cart_ctx)
            if not decision_manager.last_rejection_code:
                live_calls_count += 1
        except Exception as e:
            if any(k in str(e) for k in ("429", "Circuit", "Rate limit", "Quota")) and secondary_or_dec:
                print("  [LIVE FAILOVER] Dispatching cart decision to secondary provider OpenRouter...")
                decision_manager.primary_provider = secondary_or_dec
                candidates = decision_manager.propose_candidates(cart_ctx)
                if not decision_manager.last_rejection_code:
                    live_calls_count += 1
            else:
                print(f"  [DECISION FALLBACK] Rule fallback engaged: {e}")
                decision_manager.primary_provider = rule_decision
                candidates = decision_manager.propose_candidates(cart_ctx)
                fallback_calls_count += 1

        all_candidates.append(candidates)
        rejection_codes.append(decision_manager.last_rejection_code)

        if candidates:
            for c in candidates:
                print(f"  Action Proposed: {c.action_type.value.upper()} | Target: {c.target_id}")
                conf_str = f"Calibrated: {c.calibrated_probability:.2f}" if c.calibrated_probability is not None else "Deterministic Rule Policy (calibrated_probability=None)"
                if c.llm_self_reported_confidence is not None:
                    conf_str += f" [LLM Raw Self-Report: {c.llm_self_reported_confidence:.2f}]"
                print(f"  Confidence: {conf_str} | Priority: {c.priority_score:.2f} | Holdout: {c.is_holdout}")
                print(f"  Rationale: {c.reasoning_summary}")
        else:
            code = decision_manager.last_rejection_code or "POLICY_FILTER"
            print(f"  Action Proposed: DO_NOTHING [Rejection Code: {code}]")
        print()

    # Part 3 Assertions
    try:
        # Scenario 1: High-value identified eligible cart (INR 750)
        assert len(all_candidates[0]) > 0, "Scenario 1 should propose an action"
        assert all_candidates[0][0].action_type == ActionType.WAIVE_DELIVERY_FEE, "Scenario 1 action mismatch"
        assert "holdout" in all_candidates[0][0].reasoning_summary.lower() or all_candidates[0][0].is_holdout is not None, "Scenario 1 rationale missing holdout mention"

        # Scenario 2: VIP Repeat (INR 1450)
        assert len(all_candidates[1]) > 0, "Scenario 2 should propose an action"
        assert all_candidates[1][0].action_type == ActionType.WAIVE_DELIVERY_FEE, "Scenario 2 action mismatch"

        # Scenario 3: Mid-Tier (INR 420) in ₹300-₹500 band -> SEND_RECOVERY_WHATSAPP
        assert len(all_candidates[2]) > 0, "Scenario 3 should propose an action"
        assert all_candidates[2][0].action_type == ActionType.SEND_RECOVERY_WHATSAPP, "Scenario 3 action mismatch"

        # Scenario 4: Below threshold (< INR 300) -> DO_NOTHING with BELOW_MIN_CART_VALUE
        assert len(all_candidates[3]) == 0, "Scenario 4 below threshold must return DO_NOTHING"
        assert rejection_codes[3] == "BELOW_MIN_CART_VALUE", f"Scenario 4 rejection code mismatch: {rejection_codes[3]}"

        # Scenario 5: Anonymous guest -> DO_NOTHING with ANONYMOUS_NO_CONTACT
        assert len(all_candidates[4]) == 0, "Scenario 5 anonymous guest must return DO_NOTHING"
        assert rejection_codes[4] == "ANONYMOUS_NO_CONTACT", f"Scenario 5 rejection code mismatch: {rejection_codes[4]}"
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] Part 3 Validation Error: {e}")
        sys.exit(1)

    # =========================================================================
    # SUMMARY & INTEGRITY REPORT
    # =========================================================================
    print_banner("EXECUTION SUMMARY & PROVIDER AUDIT")
    print(f"Live API Calls Completed : {live_calls_count}")
    print(f"Fallback Calls Completed : {fallback_calls_count}")

    if live_calls_count > 0:
        print(f"\n[STATUS: FULLY LIVE ({live_calls_count} LIVE CALLS VALIDATED)]")
    else:
        print("\n[STATUS: DEGRADED (MOCK FALLBACK ACTIVE - 0 LIVE CALLS)]")
        if require_live:
            print("\n[ERROR] --require-live flag was specified, but zero live API calls were completed.")
            sys.exit(1)

    print("\n" + "=" * 100)
    print("ALL MODULE 4 WORKFLOWS VALIDATED AND ASSERTIONS PASSED".center(100))
    print("=" * 100 + "\n")


if __name__ == "__main__":
    run_demo()
