"""
Independent Exact Metrics Oracle
GrowthOS Randomized Scenario Test Environment

Computes exact ground-truth funnel and revenue metrics directly
from the generator's session trace ledger.

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict

from sim.generators.funnel import SimulatedSession


class GroundTruthMetrics(BaseModel):
    """Immutable exact metrics calculated from generator ledger."""
    model_config = ConfigDict(extra="forbid")

    total_sessions: int
    view_count: int
    cart_count: int
    checkout_count: int
    payment_count: int
    order_count: int
    cart_to_order_conversion: float
    view_to_order_conversion: float
    gross_revenue_paise: int
    cart_subtotal_paise: int
    delivery_fee_collected_paise: int
    delivery_fee_waived_paise: int
    loyalty_points_issued: int
    aov_paise: int


class ExactMetricsOracle:
    """
    Independent oracle that re-computes all funnel metrics from raw session traces.
    """

    @staticmethod
    def compute(sessions: List[SimulatedSession]) -> GroundTruthMetrics:
        total_sessions = len(sessions)
        view_count = sum(1 for s in sessions if "view" in s.steps)
        cart_count = sum(1 for s in sessions if "cart" in s.steps)
        checkout_count = sum(1 for s in sessions if "checkout" in s.steps)
        payment_count = sum(1 for s in sessions if "payment" in s.steps)
        completed_orders = [s for s in sessions if s.order_completed]
        order_count = len(completed_orders)

        gross_revenue = sum(s.final_amount_paid_paise for s in completed_orders)
        cart_subtotal = sum(s.cart_total_paise for s in completed_orders)
        fee_collected = sum(
            (s.delivery_fee_paise if not s.fee_waived else 0)
            for s in completed_orders
        )
        fee_waived = sum(
            (s.delivery_fee_paise if s.fee_waived else 0)
            for s in sessions if s.fee_waived
        )
        points_issued = sum(s.points_earned for s in completed_orders)

        aov = gross_revenue // order_count if order_count > 0 else 0
        cart_to_order = round(order_count / cart_count, 4) if cart_count > 0 else 0.0
        view_to_order = round(order_count / view_count, 4) if view_count > 0 else 0.0

        return GroundTruthMetrics(
            total_sessions=total_sessions,
            view_count=view_count,
            cart_count=cart_count,
            checkout_count=checkout_count,
            payment_count=payment_count,
            order_count=order_count,
            cart_to_order_conversion=cart_to_order,
            view_to_order_conversion=view_to_order,
            gross_revenue_paise=gross_revenue,
            cart_subtotal_paise=cart_subtotal,
            delivery_fee_collected_paise=fee_collected,
            delivery_fee_waived_paise=fee_waived,
            loyalty_points_issued=points_issued,
            aov_paise=aov,
        )

    @classmethod
    def compare(
        cls,
        oracle_metrics: GroundTruthMetrics,
        engine_metrics: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validates engine metrics against exact oracle ground truth.
        Counts must match with exact integer equality.
        """
        mismatches: List[str] = []

        # Exact integer checks
        if "total_sessions" in engine_metrics:
            if engine_metrics["total_sessions"] != oracle_metrics.total_sessions:
                mismatches.append(
                    f"TOTAL_SESSIONS_MISMATCH: Engine reported {engine_metrics['total_sessions']}, Oracle expected {oracle_metrics.total_sessions}"
                )

        if "orders" in engine_metrics:
            if engine_metrics["orders"] != oracle_metrics.order_count:
                mismatches.append(
                    f"ORDER_COUNT_MISMATCH: Engine reported {engine_metrics['orders']}, Oracle expected {oracle_metrics.order_count}"
                )

        if "gross_revenue_paise" in engine_metrics:
            if engine_metrics["gross_revenue_paise"] != oracle_metrics.gross_revenue_paise:
                mismatches.append(
                    f"GROSS_REVENUE_MISMATCH: Engine reported {engine_metrics['gross_revenue_paise']} paise, Oracle expected {oracle_metrics.gross_revenue_paise} paise"
                )

        if "loyalty_points_issued" in engine_metrics:
            if engine_metrics["loyalty_points_issued"] != oracle_metrics.loyalty_points_issued:
                mismatches.append(
                    f"LOYALTY_POINTS_MISMATCH: Engine reported {engine_metrics['loyalty_points_issued']} points, Oracle expected {oracle_metrics.loyalty_points_issued} points"
                )

        return (len(mismatches) == 0, mismatches)
