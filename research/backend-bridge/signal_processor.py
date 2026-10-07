"""
GrowthOS Behavioral Signal Processor
Transforms raw behavioral event streams into derived semantic signals for Module 4 (AI Growth Brain).
"""

from typing import Dict, List, Optional
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from schemas import EventEnvelope, DerivedBehavioralSignal


class SignalProcessor:
    def __init__(self):
        # In-memory session and user history buffers for signal calculation
        self.session_events: Dict[str, List[EventEnvelope]] = defaultdict(list)
        self.product_views_by_user: Dict[str, List[Dict]] = defaultdict(list)
        self.rage_clicks_by_element: Dict[str, List[EventEnvelope]] = defaultdict(list)
        self.derived_signals: List[DerivedBehavioralSignal] = []

    def process_event(self, event: EventEnvelope) -> List[DerivedBehavioralSignal]:
        """
        Processes a single event and checks for heuristic signal triggers.
        """
        user_key = event.customer_id or event.anonymous_id
        self.session_events[event.session_id].append(event)
        new_signals: List[DerivedBehavioralSignal] = []

        # 1. Product Interest & High Intent Detection
        if event.event_name == "product.viewed":
            product_id = event.properties.get("product_id") or event.properties.get("sku") or "unknown_product"
            self.product_views_by_user[user_key].append({
                "product_id": product_id,
                "timestamp": event.timestamp,
                "session_id": event.session_id,
                "name": event.properties.get("name")
            })

            # Check if user viewed same product >= 3 times
            views = [v for v in self.product_views_by_user[user_key] if v["product_id"] == product_id]
            sessions = len(set(v["session_id"] for v in views))
            if len(views) >= 3 and sessions >= 1:
                signal = DerivedBehavioralSignal(
                    signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                    signal_type="behavior.high_intent.detected",
                    customer_id=event.customer_id,
                    anonymous_id=event.anonymous_id,
                    session_id=event.session_id,
                    workspace_id=event.workspace_id,
                    confidence=0.91,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    summary=f"High purchase intent detected for product {product_id}. Viewed {len(views)} times across {sessions} session(s).",
                    evidence={
                        "product_id": product_id,
                        "product_name": event.properties.get("name"),
                        "total_views": len(views),
                        "distinct_sessions": sessions,
                        "last_price": event.properties.get("price")
                    },
                    recommended_action="Trigger targeted retention reward or dynamic discount in Module 1 / Module 3.",
                    affected_module="Module 4 (Customer Intelligence)"
                )
                new_signals.append(signal)
                self.derived_signals.append(signal)

        # 2. Checkout Friction & Abandonment
        elif event.event_name == "checkout.abandoned":
            step = event.properties.get("step_abandoned_at") or event.properties.get("step_name")
            cart_value = event.properties.get("cart_value") or 0.0
            signal = DerivedBehavioralSignal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                signal_type="behavior.checkout_friction.detected",
                customer_id=event.customer_id,
                anonymous_id=event.anonymous_id,
                session_id=event.session_id,
                workspace_id=event.workspace_id,
                confidence=0.88,
                detected_at=datetime.now(timezone.utc).isoformat(),
                summary=f"Checkout abandoned at step '{step}' with cart value ₹{cart_value}.",
                evidence={
                    "abandoned_step": step,
                    "cart_value": cart_value,
                    "device_type": event.device.device_type,
                    "time_spent_seconds": event.properties.get("time_in_checkout_seconds", 0)
                },
                recommended_action="Module 4 should orchestrate checkout recovery incentive and evaluate delivery fee barrier.",
                affected_module="Module 4 (AI Growth Brain)"
            )
            new_signals.append(signal)
            self.derived_signals.append(signal)

        # 3. Rage Click Clustering (UX friction)
        elif event.event_name == "user.rage_click":
            element_key = f"{event.properties.get('tag_name')}:{event.properties.get('element_id') or event.properties.get('class_name')}"
            self.rage_clicks_by_element[element_key].append(event)

            if len(self.rage_clicks_by_element[element_key]) >= 2:
                signal = DerivedBehavioralSignal(
                    signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                    signal_type="behavior.ux_rage_cluster.detected",
                    customer_id=event.customer_id,
                    anonymous_id=event.anonymous_id,
                    session_id=event.session_id,
                    workspace_id=event.workspace_id,
                    confidence=0.95,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    summary=f"UX Friction: Repeated rage click cluster detected on element <{element_key}>.",
                    evidence={
                        "element": element_key,
                        "text_content": event.properties.get("text_content"),
                        "total_rage_events": len(self.rage_clicks_by_element[element_key]),
                        "device_type": event.device.device_type,
                        "url": event.page.url
                    },
                    recommended_action="Inspect element affordance and responsiveness on target device.",
                    affected_module="Module 2 (Conversion Intelligence)"
                )
                new_signals.append(signal)
                self.derived_signals.append(signal)

        # 4. Exit Intent Signal
        elif event.event_name == "user.exit_intent":
            signal = DerivedBehavioralSignal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                signal_type="behavior.exit_intent.detected",
                customer_id=event.customer_id,
                anonymous_id=event.anonymous_id,
                session_id=event.session_id,
                workspace_id=event.workspace_id,
                confidence=0.82,
                detected_at=datetime.utcnow().isoformat() + "Z",
                summary="Exit intent detected on desktop viewport.",
                evidence={
                    "velocity_y": event.properties.get("velocity_y"),
                    "page_url": event.page.url,
                    "dwell_seconds": event.properties.get("dwell_seconds_before_exit")
                },
                recommended_action="Display personalized exit modal or loyalty teaser.",
                affected_module="Module 1 / Module 4"
            )
            new_signals.append(signal)
            self.derived_signals.append(signal)

        return new_signals

    def get_signals_for_user(self, user_id: str) -> List[DerivedBehavioralSignal]:
        return [s for s in self.derived_signals if s.customer_id == user_id or s.anonymous_id == user_id]

    def get_all_signals(self) -> List[DerivedBehavioralSignal]:
        return self.derived_signals
