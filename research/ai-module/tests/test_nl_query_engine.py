"""
Unit tests for NLQueryEngine and MerchantQueryService
Validates:
- Query classification into fixed metric catalog.
- Deterministic metric calculation integration.
- Safe handling of unsupported out-of-catalog queries.
- 3-tier structured answer verification (Executive, Analytical, Technical).
- Audit trail recording for merchant queries.
"""

import pytest
from datetime import datetime, timezone, timedelta

from domain.metrics import TimeWindow
from domain.nlp import QueryIntent
from domain.events import EventEnvelope
from adapters.sql_event_storage import SqlEventStorageAdapter
from adapters.sql_audit_ledger import SqlAuditLedgerAdapter
from adapters.mock_llm import MockLLMAdapter
from engines.metrics_engine import MetricsEngine
from engines.evidence_linker import EvidenceLinker
from engines.nl_query_engine import NLQueryEngine
from services.merchant_query_service import MerchantQueryService


@pytest.fixture
def storage():
    adapter = SqlEventStorageAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


@pytest.fixture
def audit_ledger():
    return SqlAuditLedgerAdapter(db_path=":memory:")


@pytest.fixture
def metrics_engine(storage):
    return MetricsEngine(storage=storage)


@pytest.fixture
def llm():
    return MockLLMAdapter()


@pytest.fixture
def nl_engine(llm, metrics_engine):
    linker = EvidenceLinker()
    return NLQueryEngine(llm_port=llm, metrics_engine=metrics_engine, evidence_linker=linker)


@pytest.fixture
def query_service(nl_engine, audit_ledger):
    return MerchantQueryService(nl_query_engine=nl_engine, audit_ledger=audit_ledger)


def _seed_sample_events(storage, tenant_id: str, base_time: datetime):
    # Seed 100 sessions with cart added, 40 completed checkout step 1, 15 completed checkout step 2
    events = []
    for i in range(100):
        t = base_time + timedelta(minutes=i * 2)
        sid = f"sess_{i:03d}"
        cid = f"cust_{i:03d}"
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
                properties={"cart_value": 500.0}
            )
        )
        if i < 40:
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
        if i < 15:
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
        if i < 20:
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
                    properties={"order_total": 450.0}
                )
            )
    storage.store_batch(events)


def test_funnel_drop_off_query(storage, nl_engine):
    base_time = datetime(2026, 10, 5, 10, 0, 0, tzinfo=timezone.utc)
    _seed_sample_events(storage, "tenant_dominos", base_time)

    answer = nl_engine.process_query(
        tenant_id="tenant_dominos",
        query_text="Where is the checkout drop off happening?",
        vertical="ecommerce_d2c",
        as_of=base_time + timedelta(hours=5)
    )

    assert answer.intent == QueryIntent.FUNNEL_DROP_OFF
    assert "checkout step 2 drop off rate" in answer.executive_summary.lower()
    assert len(answer.analytical_breakdown) >= 1
    assert "checkout_step_2_drop_off_rate" in answer.technical_trace["metric_name"]
    assert len(answer.citations) >= 1
    assert answer.citations[0].is_verified is True


def test_conversion_lookup_query(storage, nl_engine):
    base_time = datetime(2026, 10, 5, 10, 0, 0, tzinfo=timezone.utc)
    _seed_sample_events(storage, "tenant_dominos", base_time)

    answer = nl_engine.process_query(
        tenant_id="tenant_dominos",
        query_text="What is our overall checkout conversion rate?",
        vertical="ecommerce_d2c",
        as_of=base_time + timedelta(hours=5)
    )

    assert answer.intent == QueryIntent.METRIC_LOOKUP
    assert "conversion rate" in answer.executive_summary.lower()
    assert "overall_conversion_rate" in answer.technical_trace["metric_name"]


def test_unsupported_query_fails_safely(nl_engine):
    answer = nl_engine.process_query(
        tenant_id="tenant_dominos",
        query_text="What is the weather in Mumbai tomorrow?",
        vertical="ecommerce_d2c"
    )

    assert answer.intent == QueryIntent.UNSUPPORTED
    assert "could not be mapped" in answer.executive_summary.lower() or "standard business metric" in answer.executive_summary.lower()
    assert answer.technical_trace["status"] == "unsupported_query"
    # Never executes or produces hallucinated numbers
    assert len(answer.citations) == 0


def test_merchant_query_service_audit_trail(storage, query_service, audit_ledger):
    base_time = datetime(2026, 10, 5, 10, 0, 0, tzinfo=timezone.utc)
    _seed_sample_events(storage, "tenant_dominos", base_time)

    answer = query_service.ask(
        tenant_id="tenant_dominos",
        merchant_id="usr_owner_1",
        question="Show checkout drop off friction",
        vertical="ecommerce_d2c",
        as_of=base_time + timedelta(hours=5)
    )

    assert answer.intent == QueryIntent.FUNNEL_DROP_OFF

    # Check audit record
    trail = audit_ledger.get_audit_trail(tenant_id="tenant_dominos")
    query_events = [r for r in trail if r.event_type == "merchant_query_answered"]
    assert len(query_events) == 1
    assert query_events[0].actor == "merchant:usr_owner_1"
    assert "Show checkout drop off friction" in query_events[0].details["query"]


def test_marketing_budget_allocation_arbitration_ads_vs_loyalty(nl_engine):
    marketing_ctx = {
        "storefront": {
            "aov_inr": 1772.0,
            "storefront_name": "GrowthOS Fashion Store",
            "city": "Hyderabad"
        },
        "loyalty": {
            "delivery_fee_inr": 59.0,
            "daily_waiver_budget_inr": 2536.0,
            "waiver_cost_pts": 80,
            "waiver_retention_cac_inr": 59.0
        },
        "ads": {
            "total_budget_inr": 138245.0,
            "target_cpa_inr": 325.0,
            "blended_cac_inr": 427.72,
            "blended_roas": 3.48,
            "campaign_count": 7,
            "bleeder_name": "Google Search Campaign 3",
            "bleeder_cpa_inr": 385.0,
            "bleeder_roas": 2.31,
            "winner_name": "Meta Search Campaign 7",
            "winner_roas": 3.50
        }
    }

    answer = nl_engine.process_query(
        tenant_id="tenant_dominos",
        query_text="do we need to add more marketing expense and which part ads or loyalty",
        vertical="ecommerce",
        marketing_context=marketing_ctx
    )

    assert answer.intent == QueryIntent.BUDGET_ALLOCATION
    assert "loyalty fee waivers" in answer.executive_summary.lower()
    assert "cheaper" in answer.executive_summary.lower()
    assert "paid ads" in answer.executive_summary.lower()
    assert len(answer.analytical_breakdown) >= 4
    assert len(answer.citations) >= 4
    for cit in answer.citations:
        assert cit.is_verified is True
        assert cit.computed_value > 0

    assert answer.technical_trace["intent"] == "budget_allocation"
    assert answer.technical_trace["arbitration_ratio"] == pytest.approx(7.25, abs=0.05)


def test_blended_cac_and_ad_roas_query(nl_engine):
    answer = nl_engine.process_query(
        tenant_id="tenant_dominos",
        query_text="What is our blended CAC and ad ROAS?",
        vertical="ecommerce"
    )

    assert answer.intent == QueryIntent.BUDGET_ALLOCATION
    metric_names = [c.metric_name for c in answer.citations]
    assert "blended_cac" in metric_names
    assert "blended_roas" in metric_names
    assert answer.technical_trace["status"] == "valid"

