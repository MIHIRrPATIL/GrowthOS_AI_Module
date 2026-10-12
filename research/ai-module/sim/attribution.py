"""
Causal Attribution & Pre-Policy ITT Lift Evaluator
GrowthOS Randomized Scenario Test Environment

Measures true incremental treatment lift across treated and control holdout arms
over a standardized 24-hour attribution window using two-proportion Z-tests.

Strictly NO emojis in code, docstrings, or logs.
"""

import math
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.generators.customers import CustomerProfile


class AttributionLiftReport(BaseModel):
    """Detailed causal lift evaluation and 95% confidence intervals."""
    model_config = ConfigDict(extra="forbid")

    treated_count: int
    control_count: int
    treated_conversions: int
    control_conversions: int
    treated_rate: float
    control_rate: float
    absolute_lift: float
    relative_lift_pct: float
    z_score: float
    ci_95_lower: float
    ci_95_upper: float
    is_statistically_significant: bool


class CausalLiftEvaluator:
    """
    Evaluates incremental lift with pre-policy ITT holdout guarantees.
    """

    @staticmethod
    def evaluate(
        treated_conversions: int,
        treated_total: int,
        control_conversions: int,
        control_total: int,
    ) -> AttributionLiftReport:
        if treated_total <= 0 or control_total <= 0:
            return AttributionLiftReport(
                treated_count=treated_total,
                control_count=control_total,
                treated_conversions=treated_conversions,
                control_conversions=control_conversions,
                treated_rate=0.0,
                control_rate=0.0,
                absolute_lift=0.0,
                relative_lift_pct=0.0,
                z_score=0.0,
                ci_95_lower=0.0,
                ci_95_upper=0.0,
                is_statistically_significant=False,
            )

        p_t = treated_conversions / treated_total
        p_c = control_conversions / control_total

        abs_lift = p_t - p_c
        rel_lift_pct = round((abs_lift / p_c) * 100.0, 2) if p_c > 0 else 0.0

        # Pooled standard error for two-proportion z-test
        pooled_p = (treated_conversions + control_conversions) / (treated_total + control_total)
        pooled_se = math.sqrt(pooled_p * (1.0 - pooled_p) * ((1.0 / treated_total) + (1.0 / control_total))) if (0.0 < pooled_p < 1.0) else 0.0

        z_score = (abs_lift / pooled_se) if pooled_se > 0 else 0.0

        # Unpooled standard error for 95% confidence interval on difference
        se_diff = math.sqrt((p_t * (1.0 - p_t) / treated_total) + (p_c * (1.0 - p_c) / control_total))
        ci_lower = abs_lift - (1.96 * se_diff)
        ci_upper = abs_lift + (1.96 * se_diff)

        is_sig = abs(z_score) >= 1.96  # p < 0.05

        return AttributionLiftReport(
            treated_count=treated_total,
            control_count=control_total,
            treated_conversions=treated_conversions,
            control_conversions=control_conversions,
            treated_rate=round(p_t, 4),
            control_rate=round(p_c, 4),
            absolute_lift=round(abs_lift, 4),
            relative_lift_pct=rel_lift_pct,
            z_score=round(z_score, 3),
            ci_95_lower=round(ci_lower, 4),
            ci_95_upper=round(ci_upper, 4),
            is_statistically_significant=is_sig,
        )

    @classmethod
    def simulate_planted_lift(
        cls,
        customers: List[CustomerProfile],
        planted_relative_lift: float,
        rng: np.random.Generator
    ) -> AttributionLiftReport:
        """
        Simulates conversion outcomes where treated arm receives planted_relative_lift.
        """
        treated_total = 0
        treated_conv = 0
        control_total = 0
        control_conv = 0

        for c in customers:
            base_p = c.baseline_propensity
            if c.is_control_arm:
                control_total += 1
                if rng.uniform() < base_p:
                    control_conv += 1
            else:
                treated_total += 1
                # Treated arm experiences planted lift
                treated_p = min(1.0, base_p * (1.0 + planted_relative_lift))
                if rng.uniform() < treated_p:
                    treated_conv += 1

        return cls.evaluate(
            treated_conversions=treated_conv,
            treated_total=treated_total,
            control_conversions=control_conv,
            control_total=control_total,
        )
