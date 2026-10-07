"""
Deterministic Unit Tests for Grounded Metrics Engine
Compares automated calculations against hand-calculated mathematical baselines.
Validates:
1. Exact conversion, drop-off, and cart abandonment calculations.
2. Explicit numerator, denominator, and sample_size reporting.
3. Minimum-sample threshold rules (min_sample_met).
4. Zero-denominator safety without ZeroDivisionError.
5. Multi-tenant isolation and dimension filtering.
6. Fail-loud validation for unknown vertical templates.
"""

import pytest
from datetime import datetime, timezone, timedelta

from adapters.sql_event_storage import SqlEventStorageAdapter
from engines.metrics_engine import MetricsEngine
from engines.vertical_templates import get_vertical_template
from domain.events import EventEnvelope, DeviceMetadata
from domain.metrics import TimeWindow


@pytest.fixture
def storage():
    adapter = SqlEventStorageAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


@pytest.fixture
def engine(storage):
    return MetricsEngine(storage=storage)


def test_hand_calculated_metrics_baseline(storage, engine):
    """
    Creates a controlled synthetic population with known mathematical ground truth:
    - 50 Total sessions (all visit the menu)
    - 40 View specific products (sess 0-39)
    - 20 Add items to cart (sess 0-19)
    - 10 Start checkout (sess 0-9)
    - 8 Complete Step 1 Address (sess 0-7) -> 2 drop-off before Step 1
    - 4 Complete Step 2 Charges (sess 0-3) -> 4 drop-off at Step 2
    - 4 Complete Purchase (sess 0-3)
    - 5 Encounter Rage Clicks (sess 45-49)
    """
    t_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events = []

    # 1. Sessions 0 to 49 (50 sessions total)
    for i in range(50):
        sid = f"sess_{i:03d}"
        t = t_start + timedelta(minutes=i * 10)

        # All 50 visit
        events.append(EventEnvelope(
            tenant_id="ws_dominos_in",
            session_id=sid,
            event_name="page.viewed",
            occurred_at=t.isoformat()
        ))

        # 40 view product (sess 0-39)
        if i < 40:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="product.viewed",
                occurred_at=(t + timedelta(seconds=5)).isoformat()
            ))

        # 20 add to cart (sess 0-19)
        if i < 20:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="cart.item_added",
                occurred_at=(t + timedelta(seconds=15)).isoformat()
            ))

        # 10 start checkout (sess 0-9)
        if i < 10:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="checkout.started",
                occurred_at=(t + timedelta(seconds=25)).isoformat()
            ))

        # 8 complete step 1 (sess 0-7) -> 2 drop off before step 1!
        if i < 8:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="checkout.step_completed",
                occurred_at=(t + timedelta(seconds=35)).isoformat(),
                properties={"step_number": 1, "step_name": "address"}
            ))

        # 4 complete step 2 and purchase (sess 0-3) -> 4 drop off at step 2!
        if i < 4:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="checkout.step_completed",
                occurred_at=(t + timedelta(seconds=45)).isoformat(),
                properties={"step_number": 2, "step_name": "charges"}
            ))
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="purchase.completed",
                occurred_at=(t + timedelta(seconds=55)).isoformat(),
                properties={"order_id": f"ORD_{i}"}
            ))

        # 4 abandon at step 2 (sess 4-7)
        if 4 <= i < 8:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="checkout.abandoned",
                occurred_at=(t + timedelta(seconds=40)).isoformat(),
                properties={"step_abandoned_at": "Step 2"}
            ))

        # 2 abandon before step 1 (sess 8-9)
        if 8 <= i < 10:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="checkout.abandoned",
                occurred_at=(t + timedelta(seconds=30)).isoformat(),
                properties={"step_abandoned_at": "Step 1"}
            ))

        # 5 have rage clicks (sess 45-49)
        if i >= 45:
            events.append(EventEnvelope(
                tenant_id="ws_dominos_in",
                session_id=sid,
                event_name="user.rage_click",
                occurred_at=(t + timedelta(seconds=30)).isoformat()
            ))

    # Ingest baseline population
    storage.store_batch(events)

    # 1. Test Cart Abandonment Rate:
    # Denominator: 20 cart sessions
    # Numerator: 20 - 4 = 16 abandoned
    # Expected Ratio = 16 / 20 = 0.800000 (80.0%)
    m_cart_abandon = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window
    )
    assert m_cart_abandon.numerator == 16
    assert m_cart_abandon.denominator == 20
    assert m_cart_abandon.sample_size == 20
    assert m_cart_abandon.value == pytest.approx(0.800000, abs=1e-6)
    assert m_cart_abandon.unit == "ratio"
    assert m_cart_abandon.min_sample_met is True  # threshold 20

    # 2. Test Checkout Drop-Off Rate:
    # Denominator: 10 checkout starts
    # Numerator: 10 - 4 = 6 drop-offs
    # Expected Ratio = 6 / 10 = 0.600000 (60.0%)
    m_chk_drop = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        window=window
    )
    assert m_chk_drop.numerator == 6
    assert m_chk_drop.denominator == 10
    assert m_chk_drop.sample_size == 10
    assert m_chk_drop.value == pytest.approx(0.600000, abs=1e-6)
    assert m_chk_drop.min_sample_met is False  # threshold 15

    # 3. Test Checkout Step 1 Drop-Off Rate (Non-zero ground truth test!):
    # Denominator: 10 checkout starts
    # Numerator: 10 - 8 = 2 dropped off before completing step 1
    # Expected Ratio = 2 / 10 = 0.200000 (20.0%)
    m_step1_drop = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_step_1_drop_off_rate",
        window=window
    )
    assert m_step1_drop.numerator == 2
    assert m_step1_drop.denominator == 10
    assert m_step1_drop.sample_size == 10
    assert m_step1_drop.value == pytest.approx(0.200000, abs=1e-6)
    assert m_step1_drop.min_sample_met is True  # threshold 10

    # 4. Test Checkout Step 2 Drop-Off Rate:
    # Denominator: 8 step 1 completions
    # Numerator: 8 - 4 = 4 did not complete step 2
    # Expected Ratio = 4 / 8 = 0.500000 (50.0%)
    m_step2_drop = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_step_2_drop_off_rate",
        window=window
    )
    assert m_step2_drop.numerator == 4
    assert m_step2_drop.denominator == 8
    assert m_step2_drop.sample_size == 8
    assert m_step2_drop.value == pytest.approx(0.500000, abs=1e-6)
    assert m_step2_drop.min_sample_met is False  # threshold 10, 8 < 10

    # 5. Test Add to Cart Rate:
    # Denominator: 40 product views
    # Numerator: 20 cart adds
    # Expected Ratio = 20 / 40 = 0.500000 (50.0%)
    m_add_cart = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="add_to_cart_rate",
        window=window
    )
    assert m_add_cart.numerator == 20
    assert m_add_cart.denominator == 40
    assert m_add_cart.sample_size == 40
    assert m_add_cart.value == pytest.approx(0.500000, abs=1e-6)
    assert m_add_cart.min_sample_met is True  # threshold 30

    # 6. Test Cart to Checkout Rate:
    # Denominator: 20 cart adds
    # Numerator: 10 checkout starts
    # Expected Ratio = 10 / 20 = 0.500000 (50.0%)
    m_cart_chk = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="cart_to_checkout_rate",
        window=window
    )
    assert m_cart_chk.numerator == 10
    assert m_cart_chk.denominator == 20
    assert m_cart_chk.sample_size == 20
    assert m_cart_chk.value == pytest.approx(0.500000, abs=1e-6)
    assert m_cart_chk.min_sample_met is True  # threshold 20

    # 7. Test Overall Conversion Rate:
    # Denominator: 50 visits
    # Numerator: 4 purchases
    # Expected Ratio = 4 / 50 = 0.080000 (8.0%)
    m_conv = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=window
    )
    assert m_conv.numerator == 4
    assert m_conv.denominator == 50
    assert m_conv.sample_size == 50
    assert m_conv.value == pytest.approx(0.080000, abs=1e-6)
    assert m_conv.min_sample_met is True  # threshold 30

    # 8. Test Rage Click Session Rate:
    # Denominator: 50 total sessions
    # Numerator: 5 sessions with rage click
    # Expected Ratio = 5 / 50 = 0.100000 (10.0%)
    m_rage = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="rage_click_session_rate",
        window=window
    )
    assert m_rage.numerator == 5
    assert m_rage.denominator == 50
    assert m_rage.sample_size == 50
    assert m_rage.value == pytest.approx(0.100000, abs=1e-6)
    assert m_rage.min_sample_met is True  # threshold 25


def test_zero_denominator_safety(engine):
    """Empty window returns 0.0 without ZeroDivisionError."""
    t_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t_end = datetime(2025, 1, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    res = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        window=window
    )
    assert res.value is None
    assert res.status in ("zero_denominator", "no_data")
    assert res.sample_size == 0
    assert res.min_sample_met is False


def test_multi_tenant_metrics_isolation(storage, engine):
    """Events in Tenant A do not affect Tenant B's metrics."""
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # Tenant A has 10 visits and 10 purchases
    events_a = [
        EventEnvelope(tenant_id="tenant_a", session_id=f"sa_{i}", event_name="page.viewed", occurred_at=t_start.isoformat())
        for i in range(10)
    ] + [
        EventEnvelope(tenant_id="tenant_a", session_id=f"sa_{i}", event_name="purchase.completed", occurred_at=t_start.isoformat())
        for i in range(10)
    ]
    storage.store_batch(events_a)

    # Tenant B has 10 visits and 0 purchases
    events_b = [
        EventEnvelope(tenant_id="tenant_b", session_id=f"sb_{i}", event_name="page.viewed", occurred_at=t_start.isoformat())
        for i in range(10)
    ]
    storage.store_batch(events_b)

    res_a = engine.calculate_metric("tenant_a", "ecommerce", "overall_conversion_rate", window)
    res_b = engine.calculate_metric("tenant_b", "ecommerce", "overall_conversion_rate", window)

    assert res_a.value == 1.000000
    assert res_a.numerator == 10
    assert res_b.value == 0.000000
    assert res_b.numerator == 0


def test_dimension_filtering(storage, engine):
    """Calculates metrics broken down by device dimension."""
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # Mobile sessions: 10 visits, 5 purchases (50% conversion)
    events = [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            session_id=f"mob_{i}",
            event_name="page.viewed",
            device=DeviceMetadata(device_type="mobile"),
            occurred_at=t_start.isoformat()
        )
        for i in range(10)
    ] + [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            session_id=f"mob_{i}",
            event_name="purchase.completed",
            device=DeviceMetadata(device_type="mobile"),
            occurred_at=t_start.isoformat()
        )
        for i in range(5)
    ]

    # Desktop sessions: 10 visits, 1 purchase (10% conversion)
    events += [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            session_id=f"desk_{i}",
            event_name="page.viewed",
            device=DeviceMetadata(device_type="desktop"),
            occurred_at=t_start.isoformat()
        )
        for i in range(10)
    ] + [
        EventEnvelope(
            tenant_id="ws_dominos_in",
            session_id=f"desk_0",
            event_name="purchase.completed",
            device=DeviceMetadata(device_type="desktop"),
            occurred_at=t_start.isoformat()
        )
    ]

    storage.store_batch(events)

    mobile_res = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=window,
        dimensions={"device_type": "mobile"}
    )
    desktop_res = engine.calculate_metric(
        tenant_id="ws_dominos_in",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=window,
        dimensions={"device_type": "desktop"}
    )

    assert mobile_res.value == 0.500000
    assert mobile_res.numerator == 5
    assert mobile_res.denominator == 10
    assert mobile_res.dimensions == {"device_type": "mobile"}

    assert desktop_res.value == 0.100000
    assert desktop_res.numerator == 1
    assert desktop_res.denominator == 10
    assert desktop_res.dimensions == {"device_type": "desktop"}


def test_unknown_template_or_metric_fails_loudly(engine):
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    with pytest.raises(KeyError, match="Unknown vertical_template_id"):
        engine.calculate_metric("ws_dominos_in", "non_existent_template", "cart_abandonment_rate", window)

    with pytest.raises(KeyError, match="not defined in vertical template"):
        engine.calculate_metric("ws_dominos_in", "ecommerce", "invalid_metric_name", window)


def test_saas_subscription_funnel(storage, engine):
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # 20 landing visits, 10 signup starts, 8 signup completes, 6 workspaces, 4 onboarded, 4 trials, 2 paid
    events = []
    for i in range(20):
        sid = f"saas_sess_{i}"
        events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="page.viewed", occurred_at=t_start.isoformat()))
        if i < 10:
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="user.signup_started", occurred_at=t_start.isoformat()))
        if i < 8:
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="user.signed_up", occurred_at=t_start.isoformat()))
        if i < 6:
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="workspace.created", occurred_at=t_start.isoformat()))
        if i < 4:
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="onboarding.completed", occurred_at=t_start.isoformat()))
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="trial.started", occurred_at=t_start.isoformat()))
        if i < 2:
            events.append(EventEnvelope(tenant_id="ws_b2b_saas", session_id=sid, event_name="subscription.activated", occurred_at=t_start.isoformat()))

    storage.store_batch(events)

    # Signup completion rate: 8 / 10 = 0.800000
    res_signup = engine.calculate_metric("ws_b2b_saas", "saas_subscription", "signup_completion_rate", window)
    assert res_signup.value == pytest.approx(0.800000, abs=1e-6)
    assert res_signup.numerator == 8
    assert res_signup.denominator == 10

    # Onboarding drop-off rate: (6 - 4) / 6 = 2 / 6 = 0.333333
    res_onboard = engine.calculate_metric("ws_b2b_saas", "saas_subscription", "onboarding_drop_off_rate", window)
    assert res_onboard.value == pytest.approx(0.333333, abs=1e-6)
    assert res_onboard.numerator == 2
    assert res_onboard.denominator == 6

    # Trial to paid conversion rate: 2 / 4 = 0.500000
    res_paid = engine.calculate_metric("ws_b2b_saas", "saas_subscription", "trial_to_paid_conversion_rate", window)
    assert res_paid.value == pytest.approx(0.500000, abs=1e-6)
    assert res_paid.numerator == 2
    assert res_paid.denominator == 4


def test_travel_and_hospitality_funnel(storage, engine):
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # 30 searches, 15 listing views, 10 date selections, 7 payment attempts, 2 payment fails, 5 bookings
    events = []
    for i in range(30):
        sid = f"travel_{i}"
        events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="search.performed", occurred_at=t_start.isoformat()))
        if i < 15:
            events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="listing.viewed", occurred_at=t_start.isoformat()))
        if i < 10:
            events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="dates.selected", occurred_at=t_start.isoformat()))
        if i < 7:
            events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="payment.initiated", occurred_at=t_start.isoformat()))
        if 5 <= i < 7:
            events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="payment.failed", occurred_at=t_start.isoformat()))
        if i < 5:
            events.append(EventEnvelope(tenant_id="ws_travel_exp", session_id=sid, event_name="booking.confirmed", occurred_at=t_start.isoformat()))

    storage.store_batch(events)

    # Search to detail: 15 / 30 = 0.500000
    res_search = engine.calculate_metric("ws_travel_exp", "travel_hospitality", "search_to_detail_rate", window)
    assert res_search.value == pytest.approx(0.500000, abs=1e-6)

    # Booking drop-off: (10 - 5) / 10 = 5 / 10 = 0.500000
    res_drop = engine.calculate_metric("ws_travel_exp", "travel_hospitality", "booking_drop_off_rate", window)
    assert res_drop.value == pytest.approx(0.500000, abs=1e-6)

    # Payment failure rate: 2 / 7 = 0.285714
    res_pay = engine.calculate_metric("ws_travel_exp", "travel_hospitality", "payment_failure_rate", window)
    assert res_pay.value == pytest.approx(0.285714, abs=1e-6)


def test_fintech_and_subscription_templates_catalog(storage, engine):
    t_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # Calculate all metrics on empty data to verify every metric formula compiles and runs cleanly
    templates = ["ecommerce", "qsr_delivery", "saas_subscription", "travel_hospitality", "fintech_lending", "subscription_box"]
    for tmpl in templates:
        all_metrics = engine.calculate_all_template_metrics(
            tenant_id="ws_catalog_test",
            vertical_template_id=tmpl,
            window=window
        )
        assert len(all_metrics) >= 5
        for m_name, m_res in all_metrics.items():
            assert m_res.value is None
            assert m_res.status in ("zero_denominator", "no_data")
            assert m_res.min_sample_met is False
            assert m_res.tenant_id == "ws_catalog_test"
            assert m_res.vertical_template_id == tmpl


def test_window_boundary_exact_start_and_end(storage, engine):
    """
    Validates half-open time window semantics [window.start, window.end):
    - An event exactly at window.start MUST be included.
    - An event at window.end - 1 microsecond MUST be included.
    - An event exactly at window.end MUST be excluded from this window (and included in next window).
    """
    t_start = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)
    next_window = TimeWindow(start=t_end, end=t_end + timedelta(hours=1))

    # Event 1: exactly at window.start
    ev1 = EventEnvelope(
        tenant_id="ws_boundary_test",
        session_id="sess_boundary_start",
        event_name="page.viewed",
        occurred_at=t_start.isoformat()
    )
    # Event 2: just before window.end
    ev2 = EventEnvelope(
        tenant_id="ws_boundary_test",
        session_id="sess_boundary_inside",
        event_name="page.viewed",
        occurred_at=(t_end - timedelta(microseconds=1)).isoformat()
    )
    # Event 3: exactly at window.end
    ev3 = EventEnvelope(
        tenant_id="ws_boundary_test",
        session_id="sess_boundary_end",
        event_name="page.viewed",
        occurred_at=t_end.isoformat()
    )

    storage.store_batch([ev1, ev2, ev3])

    res_current = engine.calculate_metric(
        tenant_id="ws_boundary_test",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=window
    )
    # Exactly 2 sessions (ev1 and ev2) are in [10:00, 11:00)
    assert res_current.denominator == 2
    assert res_current.numerator == 0

    res_next = engine.calculate_metric(
        tenant_id="ws_boundary_test",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=next_window
    )
    # Exactly 1 session (ev3) is in [11:00, 12:00)
    assert res_next.denominator == 1
    assert res_next.numerator == 0


def test_duplicate_event_ids(storage, engine):
    """
    Duplicate event_ids must be idempotent at storage level and never inflate counts.
    """
    t_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    ev = EventEnvelope(
        tenant_id="ws_dedupe_test",
        event_id="evt_fixed_uuid_101",
        session_id="sess_dedupe_01",
        event_name="page.viewed",
        occurred_at=(t_start + timedelta(hours=1)).isoformat()
    )

    # Ingest the same event 3 times
    res1 = storage.store_event(ev)
    res2 = storage.store_event(ev)
    res3 = storage.store_event(ev)
    assert res1 is True
    assert res2 is False
    assert res3 is False

    metric = engine.calculate_metric(
        tenant_id="ws_dedupe_test",
        vertical_template_id="ecommerce",
        metric_name="overall_conversion_rate",
        window=window
    )
    assert metric.denominator == 1


def test_late_arriving_event_with_earlier_as_of(storage, engine):
    """
    Enforces reproducible as_of watermark filtering on received_at:
    Late-arriving events with received_at > as_of MUST NOT alter historical calculations.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # Step 1: Initial event arrived on time (occurred at 10:10, received at 10:10)
    ev_initial = EventEnvelope(
        tenant_id="ws_watermark_test",
        session_id="sess_late_01",
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 10, tzinfo=timezone.utc).isoformat(),
        received_at=datetime(2026, 10, 1, 10, 10, tzinfo=timezone.utc).isoformat()
    )
    storage.store_event(ev_initial)

    as_of_t1 = datetime(2026, 10, 1, 10, 45, tzinfo=timezone.utc)

    # Metric calculated as of 10:45: 1 cart session (occurred at 10:10, idle 35m >= 30m maturity limit).
    # 0 purchases received as of 10:45 -> abandonment rate = 1.0 (100%)
    res_t1 = engine.calculate_metric(
        tenant_id="ws_watermark_test",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window,
        as_of=as_of_t1
    )
    assert res_t1.denominator == 1
    assert res_t1.numerator == 1
    assert res_t1.value == pytest.approx(1.0, abs=1e-6)

    # Step 2: Ingest a late-arriving purchase event.
    # It occurred at 10:20 (within the window), but was received at 11:30 (after as_of_t1)
    ev_late = EventEnvelope(
        tenant_id="ws_watermark_test",
        session_id="sess_late_01",
        event_name="purchase.completed",
        occurred_at=datetime(2026, 10, 1, 10, 20, tzinfo=timezone.utc).isoformat(),
        received_at=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc).isoformat(),
        properties={"order_id": "ORD_LATE_1"}
    )
    storage.store_event(ev_late)

    # Re-query with historical as_of = 10:45
    # Invariant: Must return the EXACT SAME result because received_at (11:30) > as_of (10:45)
    res_t1_replay = engine.calculate_metric(
        tenant_id="ws_watermark_test",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window,
        as_of=as_of_t1
    )
    assert res_t1_replay.denominator == 1
    assert res_t1_replay.numerator == 1
    assert res_t1_replay.value == pytest.approx(1.0, abs=1e-6)
    assert res_t1_replay.evidence_ref == res_t1.evidence_ref

    # Query with updated as_of = 12:00: late event is now recognized -> abandonment rate = 0.0
    as_of_t2 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    res_t2 = engine.calculate_metric(
        tenant_id="ws_watermark_test",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window,
        as_of=as_of_t2
    )
    assert res_t2.denominator == 1
    assert res_t2.numerator == 0
    assert res_t2.value == pytest.approx(0.0, abs=1e-6)


def test_out_of_order_funnel_steps(storage, engine):
    """
    Events inserted in reversed chronological order must still compute correctly.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    sid = "sess_ooo_01"
    # Insert purchase FIRST, checkout SECOND, cart THIRD
    storage.store_event(EventEnvelope(
        tenant_id="ws_ooo_test",
        session_id=sid,
        event_name="purchase.completed",
        occurred_at=datetime(2026, 10, 1, 10, 25, tzinfo=timezone.utc).isoformat()
    ))
    storage.store_event(EventEnvelope(
        tenant_id="ws_ooo_test",
        session_id=sid,
        event_name="checkout.started",
        occurred_at=datetime(2026, 10, 1, 10, 15, tzinfo=timezone.utc).isoformat()
    ))
    storage.store_event(EventEnvelope(
        tenant_id="ws_ooo_test",
        session_id=sid,
        event_name="cart.item_added",
        occurred_at=datetime(2026, 10, 1, 10, 5, tzinfo=timezone.utc).isoformat()
    ))

    # Abandonment rate must be 0% (completed purchase)
    res_abandon = engine.calculate_metric(
        tenant_id="ws_ooo_test",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window
    )
    assert res_abandon.denominator == 1
    assert res_abandon.numerator == 0
    assert res_abandon.value == pytest.approx(0.0, abs=1e-6)


def test_cross_tenant_isolation_shared_identifiers(storage, engine):
    """
    Colliding session IDs across tenants must never leak across tenant boundaries.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    shared_sid = "sess_collision_xyz"
    # Tenant Alpha converts
    storage.store_batch([
        EventEnvelope(tenant_id="tenant_alpha", session_id=shared_sid, event_name="cart.item_added", occurred_at=datetime(2026, 10, 1, 10, 5, tzinfo=timezone.utc).isoformat()),
        EventEnvelope(tenant_id="tenant_alpha", session_id=shared_sid, event_name="purchase.completed", occurred_at=datetime(2026, 10, 1, 10, 15, tzinfo=timezone.utc).isoformat()),
    ])

    # Tenant Beta abandons
    storage.store_batch([
        EventEnvelope(tenant_id="tenant_beta", session_id=shared_sid, event_name="cart.item_added", occurred_at=datetime(2026, 10, 1, 10, 5, tzinfo=timezone.utc).isoformat()),
    ])

    res_alpha = engine.calculate_metric("tenant_alpha", "ecommerce", "cart_abandonment_rate", window)
    res_beta = engine.calculate_metric("tenant_beta", "ecommerce", "cart_abandonment_rate", window)

    assert res_alpha.numerator == 0
    assert res_alpha.value == pytest.approx(0.0, abs=1e-6)

    assert res_beta.numerator == 1
    assert res_beta.value == pytest.approx(1.0, abs=1e-6)


def test_window_additivity(storage, engine):
    """
    Validates that attributing sessions by session_start_time guarantees clean additivity:
    denominator(Window 1) + denominator(Window 2) == denominator(Window 1 + Window 2)
    numerator(Window 1) + numerator(Window 2) == numerator(Window 1 + Window 2)
    """
    t0 = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)

    w1 = TimeWindow(start=t0, end=t1)
    w2 = TimeWindow(start=t1, end=t2)
    w_combined = TimeWindow(start=t0, end=t2)

    events = []
    # Day 1: 15 sessions (5 convert, 10 do not)
    for i in range(15):
        sid = f"w1_sess_{i}"
        events.append(EventEnvelope(tenant_id="ws_additivity", session_id=sid, event_name="page.viewed", occurred_at=(t0 + timedelta(hours=i)).isoformat()))
        if i < 5:
            events.append(EventEnvelope(tenant_id="ws_additivity", session_id=sid, event_name="purchase.completed", occurred_at=(t0 + timedelta(hours=i, minutes=10)).isoformat()))

    # Day 2: 25 sessions (10 convert, 15 do not)
    for i in range(25):
        sid = f"w2_sess_{i}"
        events.append(EventEnvelope(tenant_id="ws_additivity", session_id=sid, event_name="page.viewed", occurred_at=(t1 + timedelta(minutes=i * 30)).isoformat()))
        if i < 10:
            events.append(EventEnvelope(tenant_id="ws_additivity", session_id=sid, event_name="purchase.completed", occurred_at=(t1 + timedelta(minutes=i * 30 + 10)).isoformat()))

    storage.store_batch(events)

    m1 = engine.calculate_metric("ws_additivity", "ecommerce", "overall_conversion_rate", w1)
    m2 = engine.calculate_metric("ws_additivity", "ecommerce", "overall_conversion_rate", w2)
    m_comb = engine.calculate_metric("ws_additivity", "ecommerce", "overall_conversion_rate", w_combined)

    assert m1.denominator == 15
    assert m1.numerator == 5

    assert m2.denominator == 25
    assert m2.numerator == 10

    assert m_comb.denominator == 15 + 25  # 40
    assert m_comb.numerator == 5 + 10     # 15
    assert m1.denominator + m2.denominator == m_comb.denominator
    assert m1.numerator + m2.numerator == m_comb.numerator


def test_deterministic_purity(storage, engine):
    """
    Passing explicit clock guarantees 100% deterministic purity: repeated calls return bit-for-bit identical results.
    """
    t_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    fixed_clock = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    storage.store_batch([
        EventEnvelope(tenant_id="ws_purity", session_id="s1", event_name="page.viewed", occurred_at=(t_start + timedelta(hours=1)).isoformat()),
        EventEnvelope(tenant_id="ws_purity", session_id="s1", event_name="purchase.completed", occurred_at=(t_start + timedelta(hours=2)).isoformat()),
    ])

    results = [
        engine.calculate_metric(
            tenant_id="ws_purity",
            vertical_template_id="ecommerce",
            metric_name="overall_conversion_rate",
            window=window,
            clock=fixed_clock
        )
        for _ in range(5)
    ]

    base = results[0]
    for r in results[1:]:
        assert r.value == base.value
        assert r.numerator == base.numerator
        assert r.denominator == base.denominator
        assert r.sample_size == base.sample_size
        assert r.status == base.status
        assert r.min_sample_met == base.min_sample_met
        assert r.evidence_ref == base.evidence_ref


def test_slow_funnel_cohort_conversion(storage, engine):
    """
    Entity: customer. Slow funnel cohort resolution:
    - Customer A: starts trial on Day 2, pays on Day 10 (8 days later in different session). In 14-day cohort -> Converted.
    - Customer B: starts trial on Day 3, pays on Day 24 (21 days later in different session). Exceeds 14-day cohort -> NOT converted.
    - Customer C: starts trial on Day 5, never pays -> NOT converted.
    - Customer D: starts trial on Day 18 (outside window) -> Excluded from cohort denominator.
    """
    t_start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Customer A (converts in 8 days)
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_A", session_id="sess_a_1", event_name="trial.started", occurred_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc).isoformat()),
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_A", session_id="sess_a_2", event_name="subscription.activated", occurred_at=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc).isoformat()),

        # Customer B (converts in 21 days, > 14 day cohort limit)
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_B", session_id="sess_b_1", event_name="trial.started", occurred_at=datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc).isoformat()),
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_B", session_id="sess_b_2", event_name="subscription.activated", occurred_at=datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc).isoformat()),

        # Customer C (never converts)
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_C", session_id="sess_c_1", event_name="trial.started", occurred_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc).isoformat()),

        # Customer D (trial started outside window)
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_D", session_id="sess_d_1", event_name="trial.started", occurred_at=datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat()),
        EventEnvelope(tenant_id="ws_cohort_saas", customer_id="cust_D", session_id="sess_d_2", event_name="subscription.activated", occurred_at=datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc).isoformat()),
    ]
    storage.store_batch(events)

    # Run cohort calculation
    metric = engine.calculate_metric(
        tenant_id="ws_cohort_saas",
        vertical_template_id="saas_subscription",
        metric_name="trial_to_paid_conversion_rate",
        window=window
    )

    # Denominator: 3 customers started trial in window [Oct 1, Oct 15) -> A, B, C
    assert metric.denominator == 3
    # Numerator: 1 customer converted within 14 days -> A only
    assert metric.numerator == 1
    assert metric.value == pytest.approx(1.0 / 3.0, abs=1e-6)
    assert metric.sample_size == 3


def test_recent_session_maturity_window(storage, engine):
    """
    Prevents recent uncompleted sessions from falsely inflating abandonment rates:
    A session active within maturity_window_minutes (30m) is excluded from abandonment denominator.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Session A: cart added at 10:15 (idle 45 mins before window end -> mature). Abandoned!
        EventEnvelope(tenant_id="ws_maturity", session_id="sess_A", event_name="cart.item_added", occurred_at=datetime(2026, 10, 1, 10, 15, tzinfo=timezone.utc).isoformat()),

        # Session B: cart added at 10:55 (active 5 mins before window end -> NOT mature). Still browsing!
        EventEnvelope(tenant_id="ws_maturity", session_id="sess_B", event_name="cart.item_added", occurred_at=datetime(2026, 10, 1, 10, 55, tzinfo=timezone.utc).isoformat()),

        # Session C: cart added at 10:50, purchased at 10:52. Converted! (Always mature upon purchase)
        EventEnvelope(tenant_id="ws_maturity", session_id="sess_C", event_name="cart.item_added", occurred_at=datetime(2026, 10, 1, 10, 50, tzinfo=timezone.utc).isoformat()),
        EventEnvelope(tenant_id="ws_maturity", session_id="sess_C", event_name="purchase.completed", occurred_at=datetime(2026, 10, 1, 10, 52, tzinfo=timezone.utc).isoformat()),
    ]
    storage.store_batch(events)

    metric = engine.calculate_metric(
        tenant_id="ws_maturity",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window,
        clock=t_end
    )

    # Session B is excluded from denominator because it had only 5 minutes of inactivity (< 30 min maturity limit)
    # Denominator: 2 (Session A and Session C)
    # Numerator: 1 (Session A abandoned)
    # Abandonment rate = 1 / 2 = 50% (NOT 2 / 3 = 66.7%)
    assert metric.denominator == 2
    assert metric.numerator == 1
    assert metric.value == pytest.approx(0.50, abs=1e-6)


def test_negative_ratio_prevention_set_difference(storage, engine):
    """
    Express checkout / missing checkout.started event must NOT result in negative drop-off rate.
    Uses set differences: assert 0 <= numerator <= denominator.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events = []
    # 2 sessions start checkout and abandon
    for i in range(2):
        sid = f"sess_reg_{i}"
        events.append(EventEnvelope(tenant_id="ws_express", session_id=sid, event_name="checkout.started", occurred_at=(t_start + timedelta(minutes=i * 5)).isoformat()))

    # 5 sessions do express checkout (purchase.completed without checkout.started)
    for i in range(5):
        sid = f"sess_exp_{i}"
        events.append(EventEnvelope(tenant_id="ws_express", session_id=sid, event_name="purchase.completed", occurred_at=(t_start + timedelta(minutes=20 + i * 5)).isoformat()))

    storage.store_batch(events)

    # Naive formula (checkout - purchase) / checkout = (2 - 7) / 2 = -2.5 (BUG!)
    # Set difference: checkout_sessions - purchased_sessions = 2 - 0 = 2 drop-offs out of 2 checkouts
    metric = engine.calculate_metric(
        tenant_id="ws_express",
        vertical_template_id="ecommerce",
        metric_name="checkout_drop_off_rate",
        window=window
    )
    assert metric.denominator == 2
    assert metric.numerator == 2
    assert metric.value == pytest.approx(1.0, abs=1e-6)
    assert 0 <= metric.numerator <= metric.denominator


def test_event_taxonomy_mapping_layer(storage, engine):
    """
    Normalizes third-party SDK / vendor aliases into canonical template events.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    # Ingest vendor alias events
    events = [
        EventEnvelope(tenant_id="ws_alias", session_id="s1", event_name="cart_add", occurred_at=(t_start + timedelta(minutes=5)).isoformat()),
        EventEnvelope(tenant_id="ws_alias", session_id="s1", event_name="begin_checkout", occurred_at=(t_start + timedelta(minutes=10)).isoformat()),
        EventEnvelope(tenant_id="ws_alias", session_id="s1", event_name="order_complete", occurred_at=(t_start + timedelta(minutes=15)).isoformat()),
    ]
    storage.store_batch(events)

    # Should resolve cart_add -> cart.item_added, order_complete -> purchase.completed
    metric = engine.calculate_metric(
        tenant_id="ws_alias",
        vertical_template_id="ecommerce",
        metric_name="cart_abandonment_rate",
        window=window
    )
    assert metric.denominator == 1
    assert metric.numerator == 0
    assert metric.value == pytest.approx(0.0, abs=1e-6)


def test_test_and_bot_traffic_exclusion(storage, engine):
    """
    Excludes bot and QA/test traffic by default so production rates are not polluted.
    """
    t_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    window = TimeWindow(start=t_start, end=t_end)

    events = [
        # Real user session (visits & buys)
        EventEnvelope(tenant_id="ws_bot_filter", session_id="s_real", event_name="page.viewed", occurred_at=(t_start + timedelta(minutes=5)).isoformat()),
        EventEnvelope(tenant_id="ws_bot_filter", session_id="s_real", event_name="purchase.completed", occurred_at=(t_start + timedelta(minutes=10)).isoformat()),

        # Crawler / Bot session (device_type="bot")
        EventEnvelope(tenant_id="ws_bot_filter", session_id="s_bot", device=DeviceMetadata(device_type="bot"), event_name="page.viewed", occurred_at=(t_start + timedelta(minutes=15)).isoformat()),

        # QA / Test automation session (is_test=True)
        EventEnvelope(tenant_id="ws_bot_filter", session_id="s_test", event_name="page.viewed", properties={"is_test": True}, occurred_at=(t_start + timedelta(minutes=20)).isoformat()),
    ]
    storage.store_batch(events)

    # With default exclusion: only 1 real user session
    m_clean = engine.calculate_metric("ws_bot_filter", "ecommerce", "overall_conversion_rate", window, exclude_test_traffic=True)
    assert m_clean.denominator == 1
    assert m_clean.numerator == 1
    assert m_clean.value == pytest.approx(1.0, abs=1e-6)

    # Without exclusion: 3 sessions included
    m_raw = engine.calculate_metric("ws_bot_filter", "ecommerce", "overall_conversion_rate", window, exclude_test_traffic=False)
    assert m_raw.denominator == 3
    assert m_raw.numerator == 1
    assert m_raw.value == pytest.approx(1.0 / 3.0, abs=1e-6)

