"""
Module 3 Ads Campaign Performance Simulator
GrowthOS Randomized Scenario Test Environment

Simulates campaign impressions, clicks, spend, conversions, and true ROAS.
Executes autonomous budget rebalancing with 15% daily limits and 1-click rollback snapshots.

Strictly NO emojis in code, docstrings, or logs.
"""

import copy
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict
import numpy as np

from sim.scenario import AdsSpec, CampaignSpec, AdPlatform


class SimulatedAdCampaign(BaseModel):
    """Execution state of an ad campaign in simulation."""
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    name: str
    platform: AdPlatform
    daily_budget_paise: int
    cpc_paise: int
    impressions: int
    clicks: int
    spend_paise: int
    conversions: int
    revenue_paise: int
    observed_roas: float
    true_roas: float
    is_paused: bool = False


class AdsSimulator:
    """
    Simulates ad campaigns and enforces budget rebalancing governance.
    """

    MAX_DAILY_SHIFT_PCT = 15.0

    def __init__(self, ads_spec: AdsSpec, rng: np.random.Generator):
        self.ads_spec = ads_spec
        self.rng = rng
        self.campaigns: Dict[str, SimulatedAdCampaign] = {}
        self.budget_snapshots: List[Dict[str, int]] = []

        self._initialize_campaigns()

    def _initialize_campaigns(self):
        for c in self.ads_spec.campaigns:
            # CPC between 10 INR and 35 INR
            cpc = int(self.rng.integers(1000, 3500))
            daily_budget = c.daily_budget_paise

            # Clicks generated based on budget and CPC
            clicks = max(10, int(daily_budget / cpc))
            impressions = int(clicks / float(self.rng.uniform(0.02, 0.06)))  # 2% - 6% CTR
            spend = min(daily_budget, clicks * cpc)

            # Revenue generated based on hidden true ROAS
            revenue = int(round(spend * c.true_roas))
            conversions = max(1, int(revenue / max(1, c.target_cpa_paise)))
            observed_roas = round(revenue / spend, 2) if spend > 0 else 0.0

            self.campaigns[c.campaign_id] = SimulatedAdCampaign(
                campaign_id=c.campaign_id,
                name=c.name,
                platform=c.platform,
                daily_budget_paise=daily_budget,
                cpc_paise=cpc,
                impressions=impressions,
                clicks=clicks,
                spend_paise=spend,
                conversions=conversions,
                revenue_paise=revenue,
                observed_roas=observed_roas,
                true_roas=c.true_roas,
                is_paused=False,
            )

    def optimize_budgets(self) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Shifts budget from bleeder campaigns (ROAS < 1.0) to top-performing campaigns.
        Strictly enforces <= 15% daily change limit.
        Saves snapshot for 1-click rollback.
        """
        # Save snapshot
        snapshot = {cid: c.daily_budget_paise for cid, c in self.campaigns.items()}
        self.budget_snapshots.append(snapshot)

        proposals = []
        # Find bleeders (lowest ROAS) and winners (highest ROAS)
        active_campaigns = [c for c in self.campaigns.values() if not c.is_paused]
        if len(active_campaigns) < 2:
            return (False, [], "INSUFFICIENT_CAMPAIGNS_FOR_REBALANCE")

        sorted_by_roas = sorted(active_campaigns, key=lambda c: c.observed_roas)
        bleeder = sorted_by_roas[0]
        winner = sorted_by_roas[-1]

        if bleeder.observed_roas >= winner.observed_roas:
            return (False, [], "NO_ARBITRAGE_OPPORTUNITY")

        # Shift up to 15% of bleeder's budget
        shift_amount = int(round(bleeder.daily_budget_paise * (self.MAX_DAILY_SHIFT_PCT / 100.0)))
        if shift_amount <= 0:
            return (False, [], "SHIFT_AMOUNT_TOO_SMALL")

        # Apply shift
        bleeder.daily_budget_paise -= shift_amount
        winner.daily_budget_paise += shift_amount

        proposals.append({
            "bleeder_id": bleeder.campaign_id,
            "winner_id": winner.campaign_id,
            "shift_amount_paise": shift_amount,
            "shift_percent": self.MAX_DAILY_SHIFT_PCT,
            "reasoning": f"Shift {self.MAX_DAILY_SHIFT_PCT}% budget from bleeder ROAS={bleeder.observed_roas} to winner ROAS={winner.observed_roas}",
        })

        return (True, proposals, "OPTIMIZATION_APPLIED")

    def rollback_last_optimization(self) -> bool:
        """Restores campaign budgets from the most recent snapshot."""
        if not self.budget_snapshots:
            return False

        last_snapshot = self.budget_snapshots.pop()
        for cid, budget in last_snapshot.items():
            if cid in self.campaigns:
                self.campaigns[cid].daily_budget_paise = budget
        return True
