"""
Evaluation & Benchmark Domain Schemas
Defines data structures for evaluating DecisionPort providers across
accuracy, calibration (ECE, Brier), latency distributions, and cost per decision.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class DecisionBenchmarkCase(BaseModel):
    """
    An individual labeled test case for evaluating decision providers.
    """
    model_config = ConfigDict(extra="ignore")

    case_id: str
    task_type: Literal["query_classification", "action_routing", "evidence_support", "cart_abandonment_decision"]
    input_context: Dict[str, Any]
    ground_truth: str
    allowed_options: List[str]
    description: str
    category: Optional[str] = None
    rationale: Optional[str] = None


class ProviderPrediction(BaseModel):
    """
    Result of a single decision prediction by a provider.
    """
    model_config = ConfigDict(extra="ignore")

    case_id: str
    selected_option: str
    stated_probability: float = Field(ge=0.0, le=1.0)
    is_correct: bool
    latency_ms: float = Field(ge=0.0)
    cost_usd: float = Field(ge=0.0)


class CalibrationMetrics(BaseModel):
    """
    Statistical calibration evaluation metrics.
    Expected Calibration Error (ECE) and Brier Score.
    """
    model_config = ConfigDict(extra="ignore")

    expected_calibration_error: float = Field(..., ge=0.0, le=1.0, description="ECE (lower is better)")
    max_calibration_error: float = Field(..., ge=0.0, le=1.0, description="MCE")
    brier_score: float = Field(..., ge=0.0, le=1.0, description="Mean squared error of probabilities")
    reliability_bins: List[Dict[str, Any]] = Field(default_factory=list)


class ProviderPerformanceSummary(BaseModel):
    """
    Comprehensive performance scorecard for a decision provider.
    """
    model_config = ConfigDict(extra="ignore")

    provider_name: str
    task_type: str
    sample_count: int
    accuracy: float = Field(..., ge=0.0, le=1.0)
    macro_f1: float = Field(..., ge=0.0, le=1.0)
    calibration: CalibrationMetrics
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cost_per_1000_usd: float
    is_eligible_for_autonomous: bool = Field(
        ...,
        description="True if accuracy >= 90% and ECE <= 0.10, making confidence reliable for autonomy gating"
    )
    accuracy_ci_lower_95: Optional[float] = None
    accuracy_ci_upper_95: Optional[float] = None
