"""
Chaos Simulation and Service Fault Injection Engine
GrowthOS Randomized Scenario Test Environment

Validates system resilience against:
1. Adapter timeout after success (testing idempotency deduplication)
2. Circuit breaker trip (after 3 consecutive failures) and recovery
3. Hostile LLM mock payloads (hallucinated numbers, inverted directions)

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Tuple, Any
import time

from adapters.loyalty_waivers_adapter import HttpLoyaltyAdapter
from engines.evidence_linker import EvidenceLinker


class ChaosSimulator:
    """
    Executes deep service-level chaos injections and fault resilience checks.
    """

    @classmethod
    def test_loyalty_timeout_after_success(
        cls,
        adapter: HttpLoyaltyAdapter,
        customer_id: str,
        fee_amount: float,
        points: int,
        idempotency_key: str,
    ) -> Tuple[bool, str]:
        """
        Simulates an adapter timeout occurring AFTER the remote service executed the action.
        Verifies that replaying the identical idempotency key returns success without double-debiting.
        """
        # First execution succeeds and records in offline/server store
        res1 = adapter.waive_delivery_fee(
            customer_id=customer_id,
            fee_amount=fee_amount,
            points_deducted=points,
            idempotency_key=idempotency_key,
        )
        if res1.get("status") != "success":
            return (False, "INITIAL_EXECUTION_FAILED")

        # Second execution with same idempotency key (simulating retry after timeout)
        res2 = adapter.waive_delivery_fee(
            customer_id=customer_id,
            fee_amount=fee_amount,
            points_deducted=points,
            idempotency_key=idempotency_key,
        )
        if res2.get("status") != "success":
            return (False, "RETRY_EXECUTION_FAILED")

        if not res2.get("is_replay"):
            return (False, "IDEMPOTENCY_REPLAY_FLAG_MISSING")

        return (True, "IDEMPOTENCY_VERIFIED")

    @classmethod
    def test_circuit_breaker_trip_and_recovery(
        cls,
        adapter: HttpLoyaltyAdapter,
    ) -> Tuple[bool, str]:
        """
        Simulates consecutive failures tripping the circuit breaker, and verifies
        automatic recovery after cooldown.
        """
        # Ensure fresh state
        adapter.consecutive_failures = 0
        adapter.circuit_open_until = 0.0

        # Inject failures up to threshold
        for _ in range(adapter.circuit_breaker_threshold):
            adapter._record_failure()

        if not adapter._is_circuit_open():
            return (False, "CIRCUIT_BREAKER_FAILED_TO_OPEN")

        # Fast forward time beyond cooldown
        adapter.circuit_open_until = time.time() - 1.0

        # Check circuit transition
        if adapter._is_circuit_open():
            return (False, "CIRCUIT_BREAKER_FAILED_TO_RESET_AFTER_COOLDOWN")

        # Record success to close circuit
        adapter._record_success()
        if adapter.consecutive_failures != 0:
            return (False, "CONSECUTIVE_FAILURES_NOT_RESET")

        return (True, "CIRCUIT_BREAKER_TRIP_AND_RECOVERY_VERIFIED")

    @classmethod
    def test_hostile_llm_rejection(
        cls,
        evidence_linker: EvidenceLinker,
        ground_truth_facts: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Feeds ungrounded and contradictory text to EvidenceLinker and verifies fail-closed rejection.
        """
        failures: List[str] = []

        # 1. Hallucinated order count (Ground truth has 142 orders, LLM claims 999 orders)
        hostile_text_counts = "We received 999 orders during this period."
        clean_text, citations, dropped = evidence_linker.verify_and_link(text=hostile_text_counts)
        if not dropped:
            failures.append("EVIDENCE_LINKER_FAILED_TO_CATCH_HALLUCINATED_COUNT")

        # 2. Hallucinated percentage (Ground truth has conversion 14.1%, LLM claims 88.5%)
        hostile_text_rate = "The checkout conversion rate reached 88.5%."
        clean_text_r, citations_r, dropped_r = evidence_linker.verify_and_link(text=hostile_text_rate)
        if not dropped_r:
            failures.append("EVIDENCE_LINKER_FAILED_TO_CATCH_HALLUCINATED_RATE")

        return (len(failures) == 0, failures)

