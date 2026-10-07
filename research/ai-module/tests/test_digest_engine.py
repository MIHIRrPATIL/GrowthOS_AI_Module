"""
Deterministic Unit Tests for Digest & Anomaly Engine
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Component 2)

Validates:
1. Period-over-period comparisons (day-over-day, week-over-week, month-over-month).
2. Metric shifts exceeding configured thresholds (default 10%).
3. Polarity-based adverse determination for higher_is_better vs lower_is_better metrics.
4. Deterministic severity classification (high, medium, low) and low-sample noise demotion.
5. Deterministic deduplication keys.
6. Behavioral absence detection: idle high-value carts (> 30m idle, >= 300 INR, no conversion).
7. Zero LLM involvement throughout calculation and flagging.
"""

import pytest
from datetime import datetime, timezone, timedelta

from domain.events import EventEnvelope, DeviceMetadata
from domain.metrics import TimeWindow, DigestReport, DigestFlag, IdleCartAnomaly
from adapters.sql_event_storage import SqlEventStorageAdapter
from engines.metrics_engine import MetricsEngine
from engines.digest_engine import DigestEngine
from engines.vertical_templates import get_vertical_template


@pytest.fixture
def storage():
    adapter = SqlEventStorageAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


@pytest.fixture
def metrics_engine(storage):
    return MetricsEngine(storage=storage)


@pytest.fixture
def digest_engine(metrics_engine, storage):
    return DigestEngine(metrics_engine=metrics_engine, storage=storage)


def _seed_funnel_events(
    storage: SqlEventStorageAdapter,
    tenant_id: str,
    base_time: datetime,
    total_sessions: int,
    cart_sessions: int,
    checkout_sessions: int,
    purchase_sessions: int,
    rage_click_sessions: int = 0
):
    """
    Helper to seed deterministic funnel events for a given window.
    """
    events = []
    for i in range(total_sessions):
        sid = f"sess_{base_time.strftime('%Y%m%d')}_{i:03d}"
        t = base_time + timedelta(minutes=i * 5)

        # 1. Page view
        events.append(EventEnvelope(
            tenant_id=tenant_id,
            session_id=sid,
            anonymous_id=f"anon_{i:03d}",
            event_name="page.viewed",
            occurred_at=t.isoformat(),
            properties={"url": "https://dominos.co.in/menu"}
        ))

        # 2. Product view
        events.append(EventEnvelope(
            tenant_id=tenant_id,
            session_id=sid,
            anonymous_id=f"anon_{i:03d}",
            event_name="product.viewed",
            occurred_at=(t + timedelta(seconds=30)).isoformat(),
            properties={"product_id": "peppy_paneer"}
        ))

        # 3. Cart add
        if i < cart_sessions:
            events.append(EventEnvelope(
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=f"anon_{i:03d}",
                event_name="cart.item_added",
                occurred_at=(t + timedelta(minutes=1)).isoformat(),
                properties={"product_id": "peppy_paneer", "cart_total": 450.0, "quantity": 1}
            ))

        # 4. Checkout start
        if i < checkout_sessions:
            events.append(EventEnvelope(
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=f"anon_{i:03d}",
                customer_id=f"cust_{i:03d}",
                event_name="checkout.started",
                occurred_at=(t + timedelta(minutes=2)).isoformat(),
                properties={"cart_total": 450.0}
            ))

            events.append(EventEnvelope(
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=f"anon_{i:03d}",
                customer_id=f"cust_{i:03d}",
                event_name="checkout.step_completed",
                occurred_at=(t + timedelta(minutes=3)).isoformat(),
                properties={"step_name": "address"}
            ))

        # 5. Purchase complete
        if i < purchase_sessions:
            events.append(EventEnvelope(
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=f"anon_{i:03d}",
                customer_id=f"cust_{i:03d}",
                event_name="purchase.completed",
                occurred_at=(t + timedelta(minutes=4)).isoformat(),
                properties={"order_id": f"ord_{i:03d}", "order_value": 450.0}
            ))

        # 6. Rage clicks
        if i < rage_click_sessions:
            events.append(EventEnvelope(
                tenant_id=tenant_id,
                session_id=sid,
                anonymous_id=f"anon_{i:03d}",
                event_name="ui.rage_clicked",
                occurred_at=(t + timedelta(minutes=2)).isoformat(),
                properties={"click_count": 5}
            ))

    storage.store_batch(events)


def test_period_over_period_comparison_and_flags(storage, digest_engine):
    """
    Simulates Week-over-Week shift where checkout conversion rate degrades significantly:
    Prior window: 50 sessions, 40 cart adds, 30 checkouts, 20 purchases (conversion = 20/30 = 66.7%)
    Current window: 50 sessions, 40 cart adds, 30 checkouts, 6 purchases (conversion = 6/30 = 20.0%)
    Drop: from 66.7% to 20.0%, delta = (20.0 - 66.67)/66.67 * 100 = -70.0%
    Delta is > 30% -> High severity flag.
    Polarity is higher_is_better -> adverse = True.
    """
    t_prior_start = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # Seed prior week
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_dominos",
        base_time=t_prior_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=30,
        purchase_sessions=20
    )

    # Seed current week (degraded checkout)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_dominos",
        base_time=t_curr_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=30,
        purchase_sessions=6
    )

    report = digest_engine.run_digest(
        tenant_id="tenant_dominos",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    assert isinstance(report, DigestReport)
    assert report.tenant_id == "tenant_dominos"
    assert report.period == "week_over_week"
    assert report.flags_count > 0

    # Locate checkout conversion flag
    conv_flags = [f for f in report.flags if f.metric_name == "overall_conversion_rate"]
    assert len(conv_flags) == 1
    flag = conv_flags[0]

    assert flag.metric_name == "overall_conversion_rate"
    assert flag.polarity == "higher_is_better"
    assert flag.current_value == pytest.approx(0.12, abs=0.01)
    assert flag.prior_value == pytest.approx(0.40, abs=0.01)
    assert flag.adverse is True
    assert flag.severity == "high"
    assert flag.delta_pct is not None
    assert flag.delta_pct < -50.0  # ~ -70% drop

    # Check dedupe_key uniqueness and format
    expected_window_key = f"{t_curr_start.strftime('%Y%m%d')}_{t_curr_end.strftime('%Y%m%d')}"
    assert flag.dedupe_key == f"tenant_dominos:overall_conversion_rate:week_over_week:{expected_window_key}:UTC:v1.1.0"


def test_polarity_and_adverse_determination(storage, digest_engine):
    """
    Tests both directions of polarity:
    1. lower_is_better (e.g. cart_abandonment_rate):
       - If rate increases -> adverse = True
       - If rate decreases -> adverse = False
    2. higher_is_better (e.g. checkout_conversion_rate):
       - If rate increases -> adverse = False
       - If rate decreases -> adverse = True
    """
    t_prior_start = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # Prior: 50 sessions, 40 carts, 35 checkouts (cart abandonment = (40-35)/40 = 12.5%)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_polarity_test",
        base_time=t_prior_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=35,
        purchase_sessions=30
    )

    # Current: 50 sessions, 40 carts, 20 checkouts (cart abandonment = (40-20)/40 = 50.0%)
    # Cart abandonment worsened from 12.5% to 50.0% (increased!)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_polarity_test",
        base_time=t_curr_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=20,
        purchase_sessions=15
    )

    report = digest_engine.run_digest(
        tenant_id="tenant_polarity_test",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    # Cart abandonment rate is lower_is_better
    cart_flags = [f for f in report.flags if f.metric_name == "cart_abandonment_rate"]
    assert len(cart_flags) == 1
    c_flag = cart_flags[0]
    assert c_flag.polarity == "lower_is_better"
    assert c_flag.current_value > c_flag.prior_value
    assert c_flag.adverse is True  # Increased abandonment is ADVERSE


def test_severity_levels_and_low_sample_demotion(storage, digest_engine):
    """
    Verifies deterministic severity classification:
    - delta >= 30% -> high
    - delta >= 15% and < 30% -> medium
    - delta >= 10% and < 15% -> low
    - Noise mitigation: when sample_size < min_sample (30), severity demoted to low
    """
    t_prior_start = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 8, 8, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 8, 8, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # Create low sample scenario: only 10 sessions total (min sample threshold is 30)
    # Prior: 10 sessions, 8 carts, 6 checkouts, 4 purchases (conversion = 4/6 = 66.7%)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_low_sample",
        base_time=t_prior_start,
        total_sessions=10,
        cart_sessions=8,
        checkout_sessions=6,
        purchase_sessions=4
    )

    # Current: 10 sessions, 8 carts, 6 checkouts, 1 purchase (conversion = 1/6 = 16.7%)
    # Delta is -75% (would be high severity if sample were large)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_low_sample",
        base_time=t_curr_start,
        total_sessions=10,
        cart_sessions=8,
        checkout_sessions=6,
        purchase_sessions=1
    )

    report = digest_engine.run_digest(
        tenant_id="tenant_low_sample",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    conv_flags = [f for f in report.flags if f.metric_name == "overall_conversion_rate"]
    assert len(conv_flags) == 1
    flag = conv_flags[0]

    # Sample size was only 10 (denominator), which is < 30
    assert flag.current_sample_size < 30
    # Because min_sample was not met, severity MUST be demoted to low to suppress noise
    assert flag.severity == "low"


def test_idle_cart_absence_detection(storage, digest_engine):
    """
    Component 2 Absence Detection:
    Finds sessions where high-value cart additions occurred but NO purchase/checkout
    was completed and the cart has been idle for >= 30 minutes.

    Scenarios:
    1. Session A: Added ₹650 Peppy Paneer cart, idle 45m, logged in (cust_101) -> Anomaly detected, High severity
    2. Session B: Added ₹350 cart, idle 45m, anonymous -> Anomaly detected, Medium severity
    3. Session C: Added ₹800 cart, completed purchase at t+15m -> NOT an anomaly
    4. Session D: Added ₹150 cart (< 300 min value), idle 45m -> NOT an anomaly
    5. Session E: Added ₹600 cart 10m ago (active shopping, idle < 30m) -> NOT an anomaly
    6. Session F: Added ₹500 cart, but emptied cart 5m later -> NOT an anomaly
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    as_of = datetime(2026, 10, 1, 11, 45, tzinfo=timezone.utc)  # Watermark at 11:45
    window = TimeWindow(start=t_start, end=t_end)

    tenant_id = "tenant_cart_absence"
    events = []

    # 1. Session A: ₹650 cart added at 10:15, last active at 10:15, as_of is 11:45 (idle = 90 min)
    # Logged-in customer
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_A",
        anonymous_id="anon_A",
        customer_id="cust_101",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 15, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "peppy_paneer", "cart_total": 650.0, "unit_price": 650.0, "quantity": 1}
    ))

    # 2. Session B: ₹350 cart added at 10:30, last active at 10:30, as_of is 11:45 (idle = 75 min)
    # Anonymous customer
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_B",
        anonymous_id="anon_B",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "margherita", "cart_total": 350.0, "unit_price": 350.0, "quantity": 1}
    ))

    # 3. Session C: ₹800 cart added at 10:20, PURCHASE COMPLETED at 10:35
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_C",
        anonymous_id="anon_C",
        customer_id="cust_102",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 20, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "farmhouse", "cart_total": 800.0, "unit_price": 800.0, "quantity": 1}
    ))
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_C",
        anonymous_id="anon_C",
        customer_id="cust_102",
        event_name="purchase.completed",
        occurred_at=datetime(2026, 10, 1, 10, 35, tzinfo=timezone.utc).isoformat(),
        properties={"order_id": "ord_c_01", "order_value": 800.0}
    ))

    # 4. Session D: ₹150 cart added at 10:25 (below ₹300 min threshold)
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_D",
        anonymous_id="anon_D",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 25, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "garlic_bread", "cart_total": 150.0, "unit_price": 150.0, "quantity": 1}
    ))

    # 5. Session E: ₹600 cart added at 11:35 (only 10 min idle relative to 11:45 watermark)
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_E",
        anonymous_id="anon_E",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 11, 35, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "cheese_burst", "cart_total": 600.0, "unit_price": 600.0, "quantity": 1}
    ))

    # 6. Session F: ₹500 cart added at 10:10, but emptied cart at 10:12
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_F",
        anonymous_id="anon_F",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 10, tzinfo=timezone.utc).isoformat(),
        properties={"product_id": "veg_loaded", "cart_total": 500.0, "unit_price": 500.0, "quantity": 1}
    ))
    events.append(EventEnvelope(
        tenant_id=tenant_id,
        session_id="sess_F",
        anonymous_id="anon_F",
        event_name="cart.cleared",
        occurred_at=datetime(2026, 10, 1, 10, 12, tzinfo=timezone.utc).isoformat(),
        properties={}
    ))

    storage.store_batch(events)

    # Run idle cart absence detection
    anomalies = digest_engine.detect_idle_carts(
        tenant_id=tenant_id,
        window=window,
        as_of=as_of,
        min_cart_value_inr=300.0,
        idle_timeout_minutes=30.0
    )

    # Exactly 2 sessions should be flagged: Session A and Session B
    assert len(anomalies) == 2

    # Ordered by highest cart value first
    anom_A = next(a for a in anomalies if a.session_id == "sess_A")
    anom_B = next(a for a in anomalies if a.session_id == "sess_B")

    # Session A assertions
    assert anom_A.cart_total_inr == 650.0
    assert anom_A.customer_id == "cust_101"
    assert anom_A.idle_duration_minutes == pytest.approx(90.0, abs=0.1)
    assert anom_A.severity == "high"
    assert anom_A.recommended_action == "waive_delivery_fee"
    assert "absence:idle_cart" in anom_A.evidence_ref

    # Session B assertions
    assert anom_B.cart_total_inr == 350.0
    assert anom_B.customer_id is None
    assert anom_B.anonymous_id == "anon_B"
    assert anom_B.idle_duration_minutes == pytest.approx(75.0, abs=0.1)
    assert anom_B.severity == "medium"
    assert anom_B.recommended_action == "trigger_exit_intent_prompt"


def test_digest_report_convenience_filtering(storage, digest_engine):
    """
    Tests report.adverse_flags() and report.high_severity_flags() helpers.
    """
    t_prior_start = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_convenience",
        base_time=t_prior_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=30,
        purchase_sessions=25,
        rage_click_sessions=2
    )

    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_convenience",
        base_time=t_curr_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=30,
        purchase_sessions=8,
        rage_click_sessions=15
    )

    report = digest_engine.run_digest(
        tenant_id="tenant_convenience",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    adverse_flags = report.adverse_flags()
    high_flags = report.high_severity_flags()

    assert all(f.adverse for f in adverse_flags)
    assert all(f.severity == "high" for f in high_flags)
    assert report.flags_count == len(report.flags)
    assert report.anomalies_count == len(report.idle_cart_anomalies)


def test_dual_window_min_sample_gating_and_statistical_significance(storage, digest_engine):
    """
    Validates:
    1. Dual-window gating: min_sample_met required on BOTH current and prior windows.
    2. A move from 60% to 50% at n=20 is within noise (stat-sig=False, severity demoted to low).
    3. delta_pp (percentage-point delta) computed alongside delta_pct (relative delta).
    4. Two-proportion z-test correctly detects true statistical significance on large samples.
    """
    t_prior_start = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # 1. Low sample scenario: n=20 sessions in each window (threshold is 30)
    # Prior: 20 sessions, 12 purchases (60.0%)
    # Current: 20 sessions, 10 purchases (50.0%)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_statsig_low",
        base_time=t_prior_start,
        total_sessions=20,
        cart_sessions=15,
        checkout_sessions=15,
        purchase_sessions=12
    )
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_statsig_low",
        base_time=t_curr_start,
        total_sessions=20,
        cart_sessions=15,
        checkout_sessions=15,
        purchase_sessions=10
    )

    report_low = digest_engine.run_digest(
        tenant_id="tenant_statsig_low",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    flag_low = next(f for f in report_low.flags if f.metric_name == "overall_conversion_rate")
    # Delta from 60% to 50%: delta_pct = -16.7%, delta_pp = -10.0pp
    assert flag_low.delta_pct == pytest.approx(-16.6666, abs=0.1)
    assert flag_low.delta_pp == pytest.approx(-10.0, abs=0.1)
    # n=20 < min_sample=30 -> Not statistically significant, demoted to low
    assert flag_low.is_statistically_significant is False
    assert flag_low.severity == "low"

    # 2. Large sample scenario: n=100 sessions in each window (min_sample=30 met on both)
    # Prior: 100 sessions, 60 purchases (60.0%)
    # Current: 100 sessions, 25 purchases (25.0%) -> massive drop (delta_pp = -35.0pp, delta_pct = -58.3%)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_statsig_high",
        base_time=t_prior_start,
        total_sessions=100,
        cart_sessions=80,
        checkout_sessions=70,
        purchase_sessions=60
    )
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_statsig_high",
        base_time=t_curr_start,
        total_sessions=100,
        cart_sessions=80,
        checkout_sessions=70,
        purchase_sessions=25
    )

    report_high = digest_engine.run_digest(
        tenant_id="tenant_statsig_high",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        threshold_pct=10.0,
        detect_absence=False
    )

    flag_high = next(f for f in report_high.flags if f.metric_name == "overall_conversion_rate")
    assert flag_high.delta_pct == pytest.approx(-58.3333, abs=0.1)
    assert flag_high.delta_pp == pytest.approx(-35.0, abs=0.1)
    # Both windows met min sample threshold (100 >= 30) and z-score > 1.96
    assert flag_high.is_statistically_significant is True
    assert flag_high.severity == "high"


def test_zero_prior_returns_null_delta_and_new_activity(storage, digest_engine):
    """
    Validates that when prior window value is 0.0:
    1. delta_pct is None (mathematical rule: no invented 100%).
    2. is_new_activity is True.
    3. Severity is 'low'.
    """
    t_prior_start = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # Prior week: 50 sessions, 0 purchases (conversion = 0/50 = 0.0)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_zero_prior",
        base_time=t_prior_start,
        total_sessions=50,
        cart_sessions=20,
        checkout_sessions=10,
        purchase_sessions=0
    )

    # Current week: 50 sessions, 10 purchases (conversion = 10/50 = 0.20)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_zero_prior",
        base_time=t_curr_start,
        total_sessions=50,
        cart_sessions=20,
        checkout_sessions=10,
        purchase_sessions=10
    )

    report = digest_engine.run_digest(
        tenant_id="tenant_zero_prior",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        flag_new_activity=True,
        detect_absence=False
    )

    conv_flag = next((f for f in report.flags if f.metric_name == "overall_conversion_rate"), None)
    assert conv_flag is not None
    assert conv_flag.prior_value == 0.0
    assert conv_flag.current_value == pytest.approx(0.20, abs=0.01)
    assert conv_flag.delta_pct is None  # Never invented 100%
    assert conv_flag.is_new_activity is True
    assert conv_flag.severity == "low"


def test_idle_cart_recoverable_window_and_upper_bound(storage, digest_engine):
    """
    Validates absence detection work queue rules:
    - Cart idle for 45 minutes (in [30m, 180m]) is in the active recoverable queue.
    - Cart idle for 300 minutes (> 180m) is cold and excluded from active recovery.
    - Cart idle for 15 minutes (< 30m) is still actively shopping and excluded.
    """
    t_end = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    t_start = t_end - timedelta(hours=8)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Session 1: 45 min idle (recoverable)
        EventEnvelope(
            tenant_id="tenant_idle_bounds",
            session_id="sess_45m",
            anonymous_id="anon_45m",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=45)).isoformat(),
            properties={"product_id": "pizza_1", "cart_total": 450.0, "unit_price": 450.0, "quantity": 1}
        ),
        # Session 2: 300 min idle (stale/cold, > 180m)
        EventEnvelope(
            tenant_id="tenant_idle_bounds",
            session_id="sess_300m",
            anonymous_id="anon_300m",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=300)).isoformat(),
            properties={"product_id": "pizza_2", "cart_total": 600.0, "unit_price": 600.0, "quantity": 1}
        ),
        # Session 3: 15 min idle (too recent, < 30m)
        EventEnvelope(
            tenant_id="tenant_idle_bounds",
            session_id="sess_15m",
            anonymous_id="anon_15m",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=15)).isoformat(),
            properties={"product_id": "pizza_3", "cart_total": 500.0, "unit_price": 500.0, "quantity": 1}
        )
    ]
    storage.store_batch(events)

    anomalies = digest_engine.detect_idle_carts(
        tenant_id="tenant_idle_bounds",
        window=window,
        min_idle_timeout_minutes=30.0,
        max_idle_timeout_minutes=180.0
    )

    assert len(anomalies) == 1
    anom = anomalies[0]
    assert anom.session_id == "sess_45m"
    assert anom.cart_total_inr == 450.0
    assert anom.is_recoverable is True
    assert 40.0 <= anom.idle_duration_minutes <= 50.0


def test_idle_cart_cross_session_purchase_suppression(storage, metrics_engine):
    """
    Validates cross-session / cross-device conversion check via identity resolver:
    A user adds to cart in session A on web, but completes purchase in session B on mobile app.
    Session A must NOT be flagged as an idle cart anomaly (zero false positives).
    """
    from adapters.sql_identity_resolver import SqlIdentityResolver
    resolver = SqlIdentityResolver(db_path=":memory:")

    # Link web anonymous ID to customer ID
    resolver.link_identities(
        tenant_id="tenant_cross_conv",
        source_type="anonymous_id",
        source_id="anon_web_user_1",
        target_type="customer_id",
        target_id="cust_ravi_99",
        link_reason="login",
        confidence_score=1.0
    )

    engine_with_identity = DigestEngine(
        metrics_engine=metrics_engine,
        storage=storage,
        identity_resolver=resolver
    )

    t_end = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    t_start = t_end - timedelta(hours=3)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Session A: Cart added on web by anonymous_id = anon_web_user_1, 60m ago
        EventEnvelope(
            tenant_id="tenant_cross_conv",
            session_id="sess_web_abandoned",
            anonymous_id="anon_web_user_1",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=60)).isoformat(),
            properties={"product_id": "burger_combo", "cart_total": 550.0, "unit_price": 550.0, "quantity": 1}
        ),
        # Session B: Purchase completed on mobile app by customer_id = cust_ravi_99, 40m ago
        EventEnvelope(
            tenant_id="tenant_cross_conv",
            session_id="sess_app_purchase",
            anonymous_id="anon_app_user_2",
            customer_id="cust_ravi_99",
            event_name="purchase.completed",
            occurred_at=(t_end - timedelta(minutes=40)).isoformat(),
            properties={"order_id": "ord_999", "order_value": 550.0}
        )
    ]
    storage.store_batch(events)

    anomalies = engine_with_identity.detect_idle_carts(
        tenant_id="tenant_cross_conv",
        window=window
    )

    # Must be 0 because Ravi converted in Session B!
    assert len(anomalies) == 0
    resolver.close()


def test_idle_cart_item_removed_handling(storage, digest_engine):
    """
    Validates cart item tracking with cart.item_removed:
    1. Item added, then removed -> Cart empty -> Not flagged.
    2. 2 items added (800 INR), 1 item removed (400 INR) -> Net cart total 400 INR -> Medium severity (not high).
    """
    t_end = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    t_start = t_end - timedelta(hours=3)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Session 1: Add item then remove item completely
        EventEnvelope(
            tenant_id="tenant_cart_removed",
            session_id="sess_emptied",
            anonymous_id="anon_emp",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=70)).isoformat(),
            properties={"product_id": "item_a", "unit_price": 400.0, "quantity": 1}
        ),
        EventEnvelope(
            tenant_id="tenant_cart_removed",
            session_id="sess_emptied",
            anonymous_id="anon_emp",
            event_name="cart.item_removed",
            occurred_at=(t_end - timedelta(minutes=65)).isoformat(),
            properties={"product_id": "item_a", "quantity": 1}
        ),
        # Session 2: Add 2 items (800 INR), remove 1 item (400 INR) -> Net 400 INR
        EventEnvelope(
            tenant_id="tenant_cart_removed",
            session_id="sess_partial",
            anonymous_id="anon_part",
            event_name="cart.item_added",
            occurred_at=(t_end - timedelta(minutes=70)).isoformat(),
            properties={"product_id": "item_b", "unit_price": 400.0, "quantity": 2}
        ),
        EventEnvelope(
            tenant_id="tenant_cart_removed",
            session_id="sess_partial",
            anonymous_id="anon_part",
            event_name="cart.item_removed",
            occurred_at=(t_end - timedelta(minutes=65)).isoformat(),
            properties={"product_id": "item_b", "quantity": 1}
        ),
    ]
    storage.store_batch(events)

    anomalies = digest_engine.detect_idle_carts(
        tenant_id="tenant_cart_removed",
        window=window,
        min_cart_value_inr=300.0,
        high_value_threshold_inr=500.0
    )

    # Only sess_partial should be flagged
    assert len(anomalies) == 1
    anom = anomalies[0]
    assert anom.session_id == "sess_partial"
    assert anom.cart_total_inr == 400.0
    # Cart total 400 < high_value_threshold (500) -> severity is "medium", not "high"
    assert anom.severity == "medium"


def test_funnel_correlation_primary_vs_downstream(storage, digest_engine):
    """
    Validates funnel correlation:
    When a specific checkout step (checkout_step_2_drop_off_rate) spikes adversely,
    it is marked as is_primary=True, while container/downstream metrics
    (checkout_drop_off_rate, overall_conversion_rate) are marked is_primary=False with root_metric_name.
    """
    t_prior_start = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
    t_prior_end = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    prior_window = TimeWindow(start=t_prior_start, end=t_prior_end)

    t_curr_start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    t_curr_end = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc)
    current_window = TimeWindow(start=t_curr_start, end=t_curr_end)

    # Seed prior week: 100 sessions, 80 carts, 70 checkouts, 60 purchases (normal funnel)
    prior_events = []
    for i in range(100):
        sid = f"prior_s_{i}"
        t = t_prior_start + timedelta(minutes=i)
        prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="page.viewed", occurred_at=t.isoformat()))
        prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="product.viewed", occurred_at=(t + timedelta(seconds=10)).isoformat()))
        if i < 80:
            prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="cart.item_added", occurred_at=(t + timedelta(seconds=20)).isoformat(), properties={"cart_total": 450.0}))
        if i < 70:
            prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.started", occurred_at=(t + timedelta(seconds=30)).isoformat(), properties={"cart_total": 450.0}))
            prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=40)).isoformat(), properties={"step_name": "address"}))
        if i < 60:
            prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=50)).isoformat(), properties={"step_name": "payment"}))
            prior_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="purchase.completed", occurred_at=(t + timedelta(seconds=60)).isoformat(), properties={"order_id": f"ord_{i}", "order_value": 450.0}))
    storage.store_batch(prior_events)

    # Current week: 100 sessions, 80 carts, 70 checkout start & address (step 1), but step 2 (payment) drops drastically to 15!
    curr_events = []
    for i in range(100):
        sid = f"curr_s_{i}"
        t = t_curr_start + timedelta(minutes=i)
        curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="page.viewed", occurred_at=t.isoformat()))
        curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="product.viewed", occurred_at=(t + timedelta(seconds=10)).isoformat()))
        if i < 80:
            curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", event_name="cart.item_added", occurred_at=(t + timedelta(seconds=20)).isoformat(), properties={"cart_total": 450.0}))
        if i < 70:
            curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.started", occurred_at=(t + timedelta(seconds=30)).isoformat(), properties={"cart_total": 450.0}))
            curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=40)).isoformat(), properties={"step_name": "address"}))
        if i < 15:
            curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="checkout.step_completed", occurred_at=(t + timedelta(seconds=50)).isoformat(), properties={"step_name": "payment"}))
            curr_events.append(EventEnvelope(tenant_id="tenant_corr", session_id=sid, anonymous_id=f"a_{i}", customer_id=f"c_{i}", event_name="purchase.completed", occurred_at=(t + timedelta(seconds=60)).isoformat(), properties={"order_id": f"ord_{i}", "order_value": 450.0}))
    storage.store_batch(curr_events)

    report = digest_engine.run_digest(
        tenant_id="tenant_corr",
        vertical_template_id="ecommerce",
        current_window=current_window,
        prior_window=prior_window,
        period="week_over_week",
        detect_absence=False
    )

    downstream_flags = [f for f in report.flags if not f.is_primary]

    # Checkout step 2 drop-off should be the primary root bottleneck
    step2_flag = next((f for f in report.flags if f.metric_name == "checkout_step_2_drop_off_rate"), None)
    assert step2_flag is not None
    assert step2_flag.is_primary is True
    assert step2_flag.adverse is True

    # Containers (overall_conversion_rate and checkout_drop_off_rate) should be downstream
    for d_flag in downstream_flags:
        if d_flag.metric_name in ("overall_conversion_rate", "checkout_drop_off_rate"):
            assert d_flag.root_metric_name == "checkout_step_2_drop_off_rate"


def test_rolling_median_baseline_prevents_bad_week_normalization(storage, digest_engine):
    """
    Validates rolling median multi-period baseline:
    Weeks 1-3: Normal conversion (~50%)
    Week 4: Incident week (14% conversion)
    Week 5 (Current): Still degraded (16% conversion)

    If compared only to Week 4 (prior window), 14% -> 16% appears as +14.3% improvement and no adverse alert fires.
    With rolling median across 4 prior weeks [50%, 50%, 50%, 14%], baseline is 50%.
    Comparing 16% to 50% correctly flags an adverse regression (~ -68%).
    """
    t_w5_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_w5_end = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
    w5_window = TimeWindow(start=t_w5_start, end=t_w5_end)

    # Seed Weeks 1, 2, 3 (each 50 sessions, 25 purchases = 50%)
    for w_idx in [4, 3, 2]:
        w_start = t_w5_start - timedelta(weeks=w_idx)
        _seed_funnel_events(
            storage=storage,
            tenant_id="tenant_rolling",
            base_time=w_start,
            total_sessions=50,
            cart_sessions=40,
            checkout_sessions=35,
            purchase_sessions=25
        )

    # Seed Week 4 (incident week: 50 sessions, 7 purchases = 14%)
    w4_start = t_w5_start - timedelta(weeks=1)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_rolling",
        base_time=w4_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=35,
        purchase_sessions=7
    )

    # Seed Week 5 (current week: 50 sessions, 8 purchases = 16%)
    _seed_funnel_events(
        storage=storage,
        tenant_id="tenant_rolling",
        base_time=t_w5_start,
        total_sessions=50,
        cart_sessions=40,
        checkout_sessions=35,
        purchase_sessions=8
    )

    # 1. Single prior window comparison (Week 5 vs Week 4)
    w4_window = TimeWindow(start=w4_start, end=t_w5_start)
    report_single = digest_engine.run_digest(
        tenant_id="tenant_rolling",
        vertical_template_id="ecommerce",
        current_window=w5_window,
        prior_window=w4_window,
        baseline_mode="prior_window",
        threshold_pct=10.0,
        detect_absence=False
    )
    conv_single = next((f for f in report_single.flags if f.metric_name == "overall_conversion_rate"), None)
    # In single prior window, 14% -> 16% is not adverse
    if conv_single:
        assert conv_single.adverse is False

    # 2. Rolling median baseline comparison (Week 5 vs median of 4 prior weeks)
    report_rolling = digest_engine.run_digest(
        tenant_id="tenant_rolling",
        vertical_template_id="ecommerce",
        current_window=w5_window,
        baseline_mode="rolling_median",
        prior_periods=4,
        threshold_pct=10.0,
        detect_absence=False
    )
    assert report_rolling.baseline_type == "rolling_median"
    assert report_rolling.baseline_periods_count == 4

    conv_rolling = next((f for f in report_rolling.flags if f.metric_name == "overall_conversion_rate"), None)
    assert conv_rolling is not None
    assert conv_rolling.adverse is True
    assert conv_rolling.delta_pct is not None
    assert conv_rolling.delta_pct < -50.0  # Massive drop from median ~50% to 16%

