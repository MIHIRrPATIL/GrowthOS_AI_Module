"""
Campaign Planning Engine for GrowthOS Ads Module
Transforms natural language growth intents into structured, compliant Google Search campaign plans.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Dict, Any, Optional
import re
import uuid
from datetime import datetime, timezone

from domain.plans import (
    CampaignPlan,
    PlanGenerationRequest,
    PlanStatus,
    ObjectiveType,
    BiddingStrategyType,
    TargetGeography,
    KeywordCluster,
    KeywordMatch,
    KeywordMatchType,
    AdCopy
)


class CampaignPlanningEngine:
    """
    Synthesizes compliant Google Search campaign plans from merchant goals.
    Extracts intents, constructs keyword clusters, generates character-bounded ad copy,
    and calculates financial limits in strict integer paise.
    """

    DEFAULT_NEGATIVE_KEYWORDS = [
        "free recipes",
        "jobs vacancies",
        "career hiring",
        "wholesale vendor",
        "wikipedia",
        "diy tutorial",
        "customer care complaint",
        "torrent download"
    ]

    def __init__(self):
        pass

    def generate_plan(self, request: PlanGenerationRequest) -> CampaignPlan:
        """
        Creates a structured CampaignPlan ready for validation and approval.
        """
        # 1. Budget and Strategy Calculation
        daily_budget_inr = request.daily_budget_inr if request.daily_budget_inr is not None else 2000.0
        daily_budget_paise = int(round(daily_budget_inr * 100))

        target_cpa_inr = request.target_cpa_inr
        target_cpa_paise = int(round(target_cpa_inr * 100)) if target_cpa_inr else None

        # 2. Extract Niche / Keywords from prompt & store name
        niche = self._extract_niche(request.goal_prompt, request.product_category)
        city = request.target_cities[0] if request.target_cities else "India"

        # 3. Build Keyword Clusters
        keyword_clusters = self._build_keyword_clusters(
            store_name=request.store_name,
            niche=niche,
            city=city
        )

        # 4. Generate Responsive Search Ad Copy (Strictly obeying character limits)
        ad_copies = [
            self._generate_ad_copy(
                store_name=request.store_name,
                niche=niche,
                city=city,
                store_url=request.store_url
            )
        ]

        # 5. Build Clean Campaign Name
        safe_store = request.store_name.strip()[:20]
        safe_city = city.strip()[:15]
        campaign_name = f"{safe_store} - {safe_city} {niche.title()} Search"
        if len(campaign_name) > 120:
            campaign_name = campaign_name[:120]

        # 6. Assemble CampaignPlan
        plan = CampaignPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            workspace_id=request.workspace_id,
            account_id=request.account_id,
            name=campaign_name,
            objective=ObjectiveType.SALES,
            channel_type="SEARCH",
            daily_budget_paise=daily_budget_paise,
            daily_budget_inr=daily_budget_inr,
            bidding_strategy=BiddingStrategyType.TARGET_CPA if target_cpa_paise else BiddingStrategyType.MAXIMIZE_CONVERSIONS,
            target_cpa_paise=target_cpa_paise,
            target_cpa_inr=target_cpa_inr,
            target_geography=TargetGeography(
                countries=["IN"],
                cities=request.target_cities
            ),
            keyword_clusters=keyword_clusters,
            negative_keywords=list(self.DEFAULT_NEGATIVE_KEYWORDS),
            ad_copies=ad_copies,
            status=PlanStatus.DRAFT,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )

        return plan

    def _extract_niche(self, prompt: str, category_hint: Optional[str]) -> str:
        prompt_lower = prompt.lower()
        if "pizza" in prompt_lower:
            return "pizza"
        if "burger" in prompt_lower:
            return "burgers"
        if "coffee" in prompt_lower:
            return "coffee"
        if "grocery" in prompt_lower or "groceries" in prompt_lower:
            return "groceries"
        if "apparel" in prompt_lower or "clothing" in prompt_lower or "fashion" in prompt_lower:
            return "fashion"

        if category_hint and category_hint.strip():
            first_word = category_hint.strip().split()[0].lower()
            return first_word

        return "delivery"

    def _build_keyword_clusters(
        self,
        store_name: str,
        niche: str,
        city: str
    ) -> List[KeywordCluster]:
        clean_store = store_name.strip().lower()
        clean_niche = niche.strip().lower()
        clean_city = city.strip().lower()

        # 1. High Intent
        high_intent = [
            KeywordMatch(text=f"order {clean_niche} online", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"best {clean_niche} delivery", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"{clean_niche} near me", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"fast {clean_niche} delivery {clean_city}", match_type=KeywordMatchType.EXACT)
        ]

        # 2. Brand Intent
        brand_intent = [
            KeywordMatch(text=f"{clean_store} online order", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"{clean_store} menu deals", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"{clean_store} {clean_city}", match_type=KeywordMatchType.EXACT)
        ]

        # 3. Location / Delivery
        location_intent = [
            KeywordMatch(text=f"{clean_niche} in {clean_city}", match_type=KeywordMatchType.PHRASE),
            KeywordMatch(text=f"late night {clean_niche} {clean_city}", match_type=KeywordMatchType.PHRASE)
        ]

        return [
            KeywordCluster(name="High Intent", keywords=high_intent),
            KeywordCluster(name="Brand Terms", keywords=brand_intent),
            KeywordCluster(name="Local Delivery", keywords=location_intent)
        ]

    def _generate_ad_copy(
        self,
        store_name: str,
        niche: str,
        city: str,
        store_url: str
    ) -> AdCopy:
        """
        Generates headlines and descriptions with strict character limits.
        Headlines: <= 30 chars
        Descriptions: <= 90 chars
        """
        clean_store = store_name.strip()
        niche_cap = niche.title()
        city_cap = city.title()

        raw_headlines = [
            f"Order {clean_store} Online",
            f"Hot Fresh {niche_cap} Delivery",
            f"Best {niche_cap} in {city_cap}",
            "Lightning-Fast Delivery",
            "Exclusive Online Deals",
            "Fresh Ingredients Daily"
        ]

        # Enforce strict <= 30 char clipping and safety
        safe_headlines: List[str] = []
        for h in raw_headlines:
            if len(h) > 30:
                h = h[:30].rstrip()
            safe_headlines.append(h)

        raw_descriptions = [
            f"Craving delicious {niche}? Order online now for fast doorstep delivery in {city_cap}.",
            f"Enjoy chef-crafted {niche} made fresh to order. Authentic flavors and combo savings.",
            "Order directly from our official store for exclusive discounts and live order tracking."
        ]

        safe_descriptions: List[str] = []
        for d in raw_descriptions:
            if len(d) > 90:
                d = d[:90].rstrip()
            safe_descriptions.append(d)

        final_url = store_url.strip()
        if not final_url.startswith("https://"):
            final_url = "https://" + final_url.lstrip("http://")

        return AdCopy(
            headlines=safe_headlines,
            descriptions=safe_descriptions,
            final_url=final_url,
            display_path_1="Order",
            display_path_2=niche.capitalize()[:15]
        )
