"""
Data Fault and Chaos Injection Engine
GrowthOS Randomized Scenario Test Environment

Injects realistic data transmission flaws:
- Duplicates (testing idempotency)
- Late & out-of-order events
- Telemetry dropouts
- Clock skew
- Adapter timeout after success

Strictly NO emojis in code, docstrings, or logs.
"""

import copy
from typing import List, Dict, Any, Tuple
import numpy as np

from sim.scenario import FaultSpec


class FaultInjector:
    """
    Applies synthetic faults according to the scenario FaultSpec.
    """

    def __init__(self, fault_spec: FaultSpec, rng: np.random.Generator):
        self.spec = fault_spec
        self.rng = rng

    def inject_event_duplicates(self, events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """Duplicates events according to duplicate_rate to test idempotency deduplication."""
        if self.spec.duplicate_rate <= 0.0 or not events:
            return (events, 0)

        output: List[Dict[str, Any]] = []
        dup_count = 0
        for ev in events:
            output.append(ev)
            if self.rng.uniform() < self.spec.duplicate_rate:
                # Append duplicate with identical event_id / idempotency_key
                output.append(copy.deepcopy(ev))
                dup_count += 1

        return (output, dup_count)

    def inject_late_and_out_of_order_events(self, events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """Shuffles a portion of events to simulate network delays and out-of-order delivery."""
        if self.spec.late_event_rate <= 0.0 or len(events) < 3:
            return (events, 0)

        output = list(events)
        shuffled_count = 0
        for i in range(len(output) - 1):
            if self.rng.uniform() < self.spec.late_event_rate:
                # Swap with next element
                output[i], output[i + 1] = output[i + 1], output[i]
                shuffled_count += 1

        return (output, shuffled_count)

    def inject_telemetry_drops(self, events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """Drops non-critical client events at sdk_loss_rate (e.g. ad-blocked or dropped views)."""
        if self.spec.sdk_loss_rate <= 0.0 or not events:
            return (events, 0)

        output: List[Dict[str, Any]] = []
        dropped_count = 0
        for ev in events:
            ev_type = ev.get("event_type", "")
            # Only drop client telemetry (e.g. view/hover), never drop verified orders
            if "order" not in ev_type and self.rng.uniform() < self.spec.sdk_loss_rate:
                dropped_count += 1
                continue
            output.append(ev)

        return (output, dropped_count)

    def inject_clock_skew(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Applies simulated device clock skew in seconds."""
        if self.spec.clock_skew_seconds <= 0 or not events:
            return events

        output: List[Dict[str, Any]] = []
        skew = self.spec.clock_skew_seconds
        for ev in events:
            modified = copy.deepcopy(ev)
            if "client_timestamp" in modified:
                modified["client_timestamp"] += skew
            output.append(modified)

        return output
