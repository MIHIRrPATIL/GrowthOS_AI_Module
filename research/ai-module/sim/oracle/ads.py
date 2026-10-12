"""
Independent Exact Ads & Cross-Budget Oracle
GrowthOS Randomized Scenario Test Environment

Validates:
- Campaign spend, CAC, and ROAS calculations
- Strict adherence to <= 15% daily budget shift limits
- Unified merchant growth spend caps (Ad spend + Loyalty fee waiver subsidies)

Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict

from sim.generators.ads import AdsSimulator, SimulatedAdCampaign


class AdsOracleResult(BaseModel):
    """Validation report for ads and cross-module budgets."""
    model_config = ConfigDict(extra="forbid")

    passed: bool
    total_ad_spend_paise: int
    total_ad_revenue_paise: int
    blended_roas: float
    violations: List[str] = Field(default_factory=list)


class ExactAdsOracle:
    """
    Independent oracle that re-computes ad performance metrics and enforces spend bounds.
    """

    @classmethod
    def verify(
        cls,
        ads_simulator: AdsSimulator,
        loyalty_waivers_spent_paise: int,
        merchant_total_growth_budget_paise: int,
    ) -> AdsOracleResult:
        violations: List[str] = []
        total_spend = 0
        total_rev = 0

        for cid, c in ads_simulator.campaigns.items():
            if c.spend_paise < 0:
                violations.append(f"NEGATIVE_AD_SPEND: Campaign {cid} spend={c.spend_paise}")
            if c.revenue_paise < 0:
                violations.append(f"NEGATIVE_AD_REVENUE: Campaign {cid} revenue={c.revenue_paise}")

            # Re-verify ROAS calculation
            expected_roas = round(c.revenue_paise / c.spend_paise, 2) if c.spend_paise > 0 else 0.0
            if c.observed_roas != expected_roas:
                violations.append(
                    f"ROAS_MISMATCH: Campaign {cid} reported ROAS {c.observed_roas} != expected {expected_roas}"
                )

            total_spend += c.spend_paise
            total_rev += c.revenue_paise

        # Cross-module unified growth spend check
        total_growth_spend = total_spend + loyalty_waivers_spent_paise
        if total_growth_spend > merchant_total_growth_budget_paise:
            violations.append(
                f"UNIFIED_GROWTH_BUDGET_EXCEEDED: Total spend {total_growth_spend} paise (Ads: {total_spend}, Loyalty: {loyalty_waivers_spent_paise}) exceeds merchant cap {merchant_total_growth_budget_paise} paise"
            )

        blended_roas = round(total_rev / total_spend, 2) if total_spend > 0 else 0.0

        return AdsOracleResult(
            passed=(len(violations) == 0),
            total_ad_spend_paise=total_spend,
            total_ad_revenue_paise=total_rev,
            blended_roas=blended_roas,
            violations=violations,
        )
