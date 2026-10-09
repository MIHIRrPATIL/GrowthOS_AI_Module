"""
Campaign Validation Engine for GrowthOS Ads Module
Applies deterministic safety policies, Google Ads platform constraints, and editorial checks.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from domain.plans import CampaignPlan, BiddingStrategyType, PlanStatus


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CampaignValidationEngine:
    """
    Enforces strict platform constraints and marketing safety invariants:
    1. Financial Guardrails (Minimum daily budget, target CPA bounds, integer paise consistency)
    2. Editorial Constraints (RSA character caps: 30 chars for headlines, 90 chars for descriptions)
    3. Destination Safety (HTTPS URL requirement, valid domain)
    4. Keyword Integrity (Non-empty clusters, negative keywords present)
    5. Platform Editorial Standards (No excessive exclamation marks, no spam capitalization)
    """

    MIN_DAILY_BUDGET_PAISE = 50000        # INR 500.00
    MAX_DAILY_BUDGET_PAISE = 5000000      # INR 50,000.00

    def __init__(
        self,
        min_budget_paise: int = MIN_DAILY_BUDGET_PAISE,
        max_budget_paise: int = MAX_DAILY_BUDGET_PAISE
    ):
        self.min_budget_paise = min_budget_paise
        self.max_budget_paise = max_budget_paise

    def validate(self, plan: CampaignPlan) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Budget Verification
        self._validate_budget(plan, errors, warnings)

        # 2. Bidding Strategy Consistency
        self._validate_bidding_strategy(plan, errors, warnings)

        # 3. Ad Copy & Editorial Checks
        self._validate_ad_copies(plan, errors, warnings)

        # 4. Keyword Clusters & Negative Keywords
        self._validate_keywords(plan, errors, warnings)

        # 5. Geographic Targeting
        self._validate_geography(plan, errors, warnings)

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def _validate_budget(self, plan: CampaignPlan, errors: List[str], warnings: List[str]) -> None:
        if plan.daily_budget_paise < self.min_budget_paise:
            errors.append(
                f"Daily budget of {plan.daily_budget_paise} paise (INR {plan.daily_budget_paise / 100:.2f}) "
                f"is below the platform minimum of {self.min_budget_paise} paise (INR {self.min_budget_paise / 100:.2f})."
            )

        if plan.daily_budget_paise > self.max_budget_paise:
            errors.append(
                f"Daily budget of {plan.daily_budget_paise} paise (INR {plan.daily_budget_paise / 100:.2f}) "
                f"exceeds the safety ceiling of {self.max_budget_paise} paise (INR {self.max_budget_paise / 100:.2f})."
            )

        expected_inr = round(plan.daily_budget_paise / 100.0, 2)
        if abs(plan.daily_budget_inr - expected_inr) > 0.05:
            errors.append(
                f"Budget currency discrepancy: daily_budget_inr ({plan.daily_budget_inr}) "
                f"does not match daily_budget_paise / 100 ({expected_inr})."
            )

    def _validate_bidding_strategy(self, plan: CampaignPlan, errors: List[str], warnings: List[str]) -> None:
        if plan.bidding_strategy == BiddingStrategyType.TARGET_CPA:
            if plan.target_cpa_paise is None or plan.target_cpa_paise <= 0:
                errors.append("Target CPA bidding strategy requires a positive target_cpa_paise.")
            else:
                if plan.target_cpa_paise > plan.daily_budget_paise:
                    errors.append(
                        f"Target CPA ({plan.target_cpa_paise} paise) exceeds total daily budget "
                        f"({plan.daily_budget_paise} paise)."
                    )
                if plan.target_cpa_inr is not None:
                    expected_cpa_inr = round(plan.target_cpa_paise / 100.0, 2)
                    if abs(plan.target_cpa_inr - expected_cpa_inr) > 0.05:
                        errors.append(
                            f"Target CPA currency discrepancy: target_cpa_inr ({plan.target_cpa_inr}) "
                            f"does not match target_cpa_paise / 100 ({expected_cpa_inr})."
                        )

        if plan.bidding_strategy == BiddingStrategyType.TARGET_ROAS:
            if plan.target_roas is None or plan.target_roas <= 0.0:
                errors.append("Target ROAS bidding strategy requires a positive target_roas value.")

    def _validate_ad_copies(self, plan: CampaignPlan, errors: List[str], warnings: List[str]) -> None:
        if not plan.ad_copies:
            errors.append("At least one responsive search ad copy is required.")
            return

        for idx, copy in enumerate(plan.ad_copies):
            # URL verification
            if not copy.final_url.startswith("https://"):
                errors.append(f"Ad copy #{idx+1} final_url must use HTTPS protocol: '{copy.final_url}'.")
            parsed = urlparse(copy.final_url)
            if not parsed.netloc:
                errors.append(f"Ad copy #{idx+1} final_url is missing a valid host: '{copy.final_url}'.")

            # Headline bounds
            if len(copy.headlines) < 3:
                errors.append(f"Ad copy #{idx+1} has {len(copy.headlines)} headlines; Google Ads requires at least 3.")
            if len(copy.headlines) > 15:
                errors.append(f"Ad copy #{idx+1} has {len(copy.headlines)} headlines; Google Ads allows a maximum of 15.")

            for h in copy.headlines:
                h_str = h.strip()
                if not h_str:
                    errors.append(f"Ad copy #{idx+1} contains an empty headline.")
                elif len(h_str) > 30:
                    errors.append(f"Ad copy #{idx+1} headline exceeds 30 characters: '{h_str}' ({len(h_str)} chars).")
                self._check_editorial_policy(h_str, f"Headline '{h_str}'", errors, warnings)

            # Description bounds
            if len(copy.descriptions) < 2:
                errors.append(f"Ad copy #{idx+1} has {len(copy.descriptions)} descriptions; Google Ads requires at least 2.")
            if len(copy.descriptions) > 4:
                errors.append(f"Ad copy #{idx+1} has {len(copy.descriptions)} descriptions; Google Ads allows a maximum of 4.")

            for d in copy.descriptions:
                d_str = d.strip()
                if not d_str:
                    errors.append(f"Ad copy #{idx+1} contains an empty description.")
                elif len(d_str) > 90:
                    errors.append(f"Ad copy #{idx+1} description exceeds 90 characters: '{d_str}' ({len(d_str)} chars).")
                self._check_editorial_policy(d_str, f"Description '{d_str}'", errors, warnings)

    def _check_editorial_policy(self, text: str, context: str, errors: List[str], warnings: List[str]) -> None:
        # Excessive punctuation check (e.g., !! or ???)
        if re.search(r"[!?]{2,}", text):
            errors.append(f"{context} violates Google Ads punctuation policy: repeated punctuation detected.")

        # Check for ALL CAPS words of length > 4 (e.g. FREEPIZZA)
        words = text.split()
        for w in words:
            clean_word = re.sub(r"[^A-Za-z]", "", w)
            if len(clean_word) > 4 and clean_word.isupper():
                errors.append(f"{context} violates Google Ads capitalization policy: word '{w}' is fully capitalized.")

        # Prohibited sensationalist phrasing
        prohibited_phrases = ["miracle cure", "get rich quick", "100% free win", "click here now"]
        for p in prohibited_phrases:
            if p in text.lower():
                errors.append(f"{context} contains restricted promotional phrase '{p}'.")

    def _validate_keywords(self, plan: CampaignPlan, errors: List[str], warnings: List[str]) -> None:
        if not plan.keyword_clusters:
            errors.append("Campaign must contain at least one keyword cluster.")
            return

        total_keywords = 0
        for cluster in plan.keyword_clusters:
            if not cluster.keywords:
                errors.append(f"Keyword cluster '{cluster.name}' contains zero keywords.")
            total_keywords += len(cluster.keywords)

        if total_keywords == 0:
            errors.append("Campaign contains zero targeting keywords.")

        # Negative keyword warning
        if not plan.negative_keywords:
            warnings.append("Campaign has no negative keywords configured. Negative keywords are recommended to prevent ad waste.")

    def _validate_geography(self, plan: CampaignPlan, errors: List[str], warnings: List[str]) -> None:
        geo = plan.target_geography
        if not geo.countries and not geo.cities and not geo.postal_codes:
            errors.append("Target geography must specify at least one country, city, or postal code.")
