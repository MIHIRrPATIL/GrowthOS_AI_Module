"""
Unit tests for synthetic event generator
"""

import pytest
from generators.synthetic_events import (
    SyntheticEventGenerator,
    KNOWN_CUSTOMERS,
    DOMINOS_MENU,
)
from domain.events import EventEnvelope


def test_generator_converting_session():
    generator = SyntheticEventGenerator(seed=123)
    events = generator.generate_session(scenario="converting")

    event_names = [e.event_name for e in events]
    assert "page.viewed" in event_names
    assert "product.viewed" in event_names
    assert "product.customized" in event_names
    assert "cart.item_added" in event_names
    assert "checkout.started" in event_names
    assert "purchase.completed" in event_names

    # Check purchase payload
    purchase = next(e for e in events if e.event_name == "purchase.completed")
    assert purchase.properties["total_amount"] > 0
    assert purchase.properties["loyalty_points_earned"] > 0


def test_generator_fee_friction_session():
    generator = SyntheticEventGenerator(seed=456)
    events = generator.generate_session(scenario="fee_friction")

    event_names = [e.event_name for e in events]
    assert "checkout.started" in event_names
    assert "user.typing_dynamics" in event_names
    assert "user.exit_intent" in event_names
    assert "checkout.abandoned" in event_names
    assert "purchase.completed" not in event_names

    abandoned = next(e for e in events if e.event_name == "checkout.abandoned")
    assert abandoned.properties["reason"] == "delivery_charge_hesitation"
    assert abandoned.properties["delivery_fee"] == 60.00
    assert abandoned.properties["step_number"] == 2


def test_generator_rage_click_session():
    generator = SyntheticEventGenerator(seed=789)
    events = generator.generate_session(scenario="rage_click")

    rage_clicks = [e for e in events if e.event_name == "user.rage_click"]
    assert len(rage_clicks) >= 3
    assert rage_clicks[0].properties["element_id"] == "btnStartCheckout"


def test_generator_dormant_session():
    generator = SyntheticEventGenerator(seed=101)
    events = generator.generate_session(scenario="dormant")

    event_names = [e.event_name for e in events]
    assert "cart.item_added" in event_names
    assert "checkout.started" not in event_names
    assert "purchase.completed" not in event_names


def test_generator_batch_generation():
    generator = SyntheticEventGenerator(seed=2026)
    batch = generator.generate_batch(session_count=30)

    assert len(batch) > 100
    # Every generated item must be a valid EventEnvelope instance
    for event in batch:
        assert isinstance(event, EventEnvelope)
        assert event.event_id.startswith("evt_")
        assert event.session_id.startswith("sess_")
        assert event.anonymous_id.startswith("anon_")

    # Chronologically sorted check
    occurred_times = [e.occurred_at for e in batch]
    assert occurred_times == sorted(occurred_times)
