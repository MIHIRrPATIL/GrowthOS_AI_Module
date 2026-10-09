"""
Engines package for GrowthOS Module 4
"""

from .vertical_templates import (
    VerticalTemplate,
    MetricDefinition,
    get_vertical_template,
    TEMPLATE_REGISTRY,
    ECOMMERCE_TEMPLATE,
    QSR_DELIVERY_TEMPLATE,
    SAAS_SUBSCRIPTION_TEMPLATE,
    TRAVEL_HOSPITALITY_TEMPLATE,
    FINTECH_LENDING_TEMPLATE,
    SUBSCRIPTION_BOX_TEMPLATE,
)
from .metrics_engine import MetricsEngine
from .digest_engine import DigestEngine
from .heuristic_scoring import (
    HeuristicWeightsConfig,
    PropensityScoreResult,
    ChurnScoreResult,
    CLTVScoreResult,
    score_purchase_propensity,
    score_churn_risk,
    score_customer_cltv,
    DEFAULT_HEURISTIC_CONFIG,
)

__all__ = [
    "VerticalTemplate",
    "MetricDefinition",
    "get_vertical_template",
    "TEMPLATE_REGISTRY",
    "ECOMMERCE_TEMPLATE",
    "QSR_DELIVERY_TEMPLATE",
    "SAAS_SUBSCRIPTION_TEMPLATE",
    "TRAVEL_HOSPITALITY_TEMPLATE",
    "FINTECH_LENDING_TEMPLATE",
    "SUBSCRIPTION_BOX_TEMPLATE",
    "MetricsEngine",
    "DigestEngine",
    "HeuristicWeightsConfig",
    "PropensityScoreResult",
    "ChurnScoreResult",
    "CLTVScoreResult",
    "score_purchase_propensity",
    "score_churn_risk",
    "score_customer_cltv",
    "DEFAULT_HEURISTIC_CONFIG",
]
