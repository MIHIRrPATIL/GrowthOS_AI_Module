"""
GrowthOS Module 4: Component 2 — Digest Engine
Scheduled / threshold-based comparator comparing current period to prior period.
Flags any metric that moved more than a configurable percentage (default: 10%).
Outputs structured flags with zero text generation at this stage.
"""

from typing import Dict, List, Optional, Literal, Any
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from metrics_engine import MetricsEngine, MetricResult


class DigestFlag(BaseModel):
    flag_id: str
    metric_name: str
    vertical_template_id: str
    current_value: float
    prior_value: float
    delta_pct: float              # Signed percentage (e.g. +16.19% or -14.30%)
    current_sample_size: int
    prior_sample_size: int
    unit: str                     # "percentage", "count", "currency_inr"
    severity: Literal["low", "medium", "high"]
    period: str                   # e.g. "week_over_week"
    flagged_at: str
    status: Literal["active", "acknowledged", "resolved"] = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DigestReport(BaseModel):
    report_id: str
    vertical_template_id: str
    period: str
    threshold_pct: float
    generated_at: str
    total_metrics_evaluated: int
    flags_count: int
    flags: List[DigestFlag]
    baseline_metrics: Dict[str, MetricResult] = Field(default_factory=dict)


class DigestEngine:
    """
    Executes scheduled periodic metric comparisons and generates structured flags.
    """

    def __init__(self, metrics_engine: Optional[MetricsEngine] = None):
        self.metrics_engine = metrics_engine or MetricsEngine()
        self.history: List[DigestReport] = []

    @staticmethod
    def calculate_delta(current: float, prior: float) -> float:
        """
        Calculates signed percentage change between current and prior values.
        Guards against division by zero.
        """
        if prior == 0:
            if current == 0:
                return 0.0
            return 100.0 if current > 0 else -100.0

        delta = ((current - prior) / abs(prior)) * 100.0
        return round(delta, 2)

    @staticmethod
    def determine_severity(abs_delta_pct: float) -> Literal["low", "medium", "high"]:
        if abs_delta_pct >= 35.0:
            return "high"
        elif abs_delta_pct >= 20.0:
            return "medium"
        return "low"

    def run_digest(
        self,
        vertical_template_id: str = "ecommerce",
        timeframe: str = "7d",
        period: str = "week_over_week",
        threshold_pct: float = 10.0
    ) -> DigestReport:
        """
        Runs the digest comparison for the given vertical against prior period.
        """
        current_metrics = self.metrics_engine.query_all_metrics(
            vertical_template_id=vertical_template_id,
            timeframe=timeframe,
            prior=False
        )

        prior_metrics = self.metrics_engine.query_all_metrics(
            vertical_template_id=vertical_template_id,
            timeframe=timeframe,
            prior=True
        )

        flags: List[DigestFlag] = []

        for metric_name, curr_metric in current_metrics.items():
            prior_metric = prior_metrics.get(metric_name)
            if not prior_metric:
                continue

            delta_pct = self.calculate_delta(curr_metric.value, prior_metric.value)
            abs_delta = abs(delta_pct)

            if abs_delta >= threshold_pct:
                severity = self.determine_severity(abs_delta)
                flag = DigestFlag(
                    flag_id=f"flag_{uuid.uuid4().hex[:10]}",
                    metric_name=metric_name,
                    vertical_template_id=vertical_template_id,
                    current_value=curr_metric.value,
                    prior_value=prior_metric.value,
                    delta_pct=delta_pct,
                    current_sample_size=curr_metric.sample_size,
                    prior_sample_size=prior_metric.sample_size,
                    unit=curr_metric.unit,
                    severity=severity,
                    period=period,
                    flagged_at=datetime.now(timezone.utc).isoformat(),
                    metadata=curr_metric.metadata
                )
                flags.append(flag)

        report = DigestReport(
            report_id=f"dig_{uuid.uuid4().hex[:10]}",
            vertical_template_id=vertical_template_id,
            period=period,
            threshold_pct=threshold_pct,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_metrics_evaluated=len(current_metrics),
            flags_count=len(flags),
            flags=flags,
            baseline_metrics=current_metrics
        )

        self.history.append(report)
        return report

    def get_latest_report(self, vertical_template_id: Optional[str] = None) -> Optional[DigestReport]:
        if not self.history:
            return None
        if not vertical_template_id:
            return self.history[-1]
        for report in reversed(self.history):
            if report.vertical_template_id == vertical_template_id:
                return report
        return None
