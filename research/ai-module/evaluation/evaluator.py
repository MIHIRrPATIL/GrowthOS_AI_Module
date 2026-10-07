"""
Benchmark Evaluator and Calibration Engine
Evaluates DecisionPort providers on Accuracy, Macro F1, Expected Calibration Error (ECE),
Brier score, Latency distributions (p50/p95/p99), and Cost per 1,000 queries.
"""

from typing import List, Dict, Any, Optional
import json
import math
from pathlib import Path

from domain.evaluation import (
    DecisionBenchmarkCase,
    ProviderPrediction,
    CalibrationMetrics,
    ProviderPerformanceSummary
)


class BenchmarkEvaluator:
    """
    Evaluation harness for decision providers.
    Runs standardized datasets and computes statistical calibration and performance scorecards.
    """

    def __init__(self, dataset_dir: Optional[str] = None):
        if dataset_dir:
            self.dataset_dir = Path(dataset_dir)
        else:
            self.dataset_dir = Path(__file__).parent / "datasets"

    def load_dataset(self, task_type: str) -> List[DecisionBenchmarkCase]:
        """
        Loads a labeled benchmark dataset by task type.
        """
        file_map = {
            "query_classification": "query_classification.json",
            "action_routing": "action_routing.json",
            "evidence_support": "evidence_support.json"
        }
        if task_type not in file_map:
            raise ValueError(f"Unknown task type '{task_type}'. Available: {list(file_map.keys())}")

        path = self.dataset_dir / file_map[task_type]
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_cases = json.load(f)

        return [DecisionBenchmarkCase.model_validate(c) for c in raw_cases]

    def evaluate_provider(
        self,
        provider_name: str,
        provider_instance: Any,
        task_type: str,
        cases: Optional[List[DecisionBenchmarkCase]] = None
    ) -> ProviderPerformanceSummary:
        """
        Runs full benchmark evaluation for a given provider on a specific task type.
        """
        benchmark_cases = cases or self.load_dataset(task_type)
        if not benchmark_cases:
            raise ValueError(f"No benchmark cases found for task '{task_type}'")

        predictions: List[ProviderPrediction] = []
        for case in benchmark_cases:
            pred = provider_instance.predict_benchmark_case(case)
            predictions.append(pred)

        return self.compute_performance_summary(
            provider_name=provider_name,
            task_type=task_type,
            cases=benchmark_cases,
            predictions=predictions
        )

    def compute_performance_summary(
        self,
        provider_name: str,
        task_type: str,
        cases: List[DecisionBenchmarkCase],
        predictions: List[ProviderPrediction]
    ) -> ProviderPerformanceSummary:
        n = len(predictions)
        if n == 0:
            raise ValueError("Predictions list cannot be empty")

        # 1. Top-1 Accuracy
        correct_count = sum(1 for p in predictions if p.is_correct)
        accuracy = correct_count / n

        # 2. Macro F1
        classes = sorted(list({c.ground_truth for c in cases}))
        f1_scores: List[float] = []

        for cls in classes:
            tp = sum(1 for c, p in zip(cases, predictions) if c.ground_truth == cls and p.selected_option == cls)
            fp = sum(1 for c, p in zip(cases, predictions) if c.ground_truth != cls and p.selected_option == cls)
            fn = sum(1 for c, p in zip(cases, predictions) if c.ground_truth == cls and p.selected_option != cls)

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            f1_scores.append(f1)

        macro_f1 = float(sum(f1_scores) / len(f1_scores)) if f1_scores else 0.0

        # 3. Calibration: ECE, MCE, Brier Score
        calibration = self._compute_calibration_metrics(predictions)

        # 4. Latency Percentiles
        latencies = sorted([p.latency_ms for p in predictions])
        p50 = self._calc_percentile(latencies, 50.0)
        p95 = self._calc_percentile(latencies, 95.0)
        p99 = self._calc_percentile(latencies, 99.0)

        # 5. Cost per 1,000 queries
        total_cost = sum(p.cost_usd for p in predictions)
        cost_per_1000 = (total_cost / n) * 1000.0

        # 6. Autonomy Gating Rule: Accuracy >= 0.90, ECE <= 0.10, p95 <= 500ms
        is_autonomous_eligible = (
            accuracy >= 0.90 and
            calibration.expected_calibration_error <= 0.10 and
            p95 <= 500.0
        )

        return ProviderPerformanceSummary(
            provider_name=provider_name,
            task_type=task_type,
            sample_count=n,
            accuracy=round(accuracy, 4),
            macro_f1=round(macro_f1, 4),
            calibration=calibration,
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            cost_per_1000_usd=round(cost_per_1000, 4),
            is_eligible_for_autonomous=is_autonomous_eligible
        )

    def _calc_percentile(self, values: List[float], p: float) -> float:
        if not values:
            return 0.0
        k = (len(values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(values[int(k)])
        return float(values[int(f)] * (c - k) + values[int(c)] * (k - f))

    def _compute_calibration_metrics(
        self,
        predictions: List[ProviderPrediction],
        num_bins: int = 10
    ) -> CalibrationMetrics:
        """
        Computes Expected Calibration Error (ECE), MCE, and Brier Score using equal-width bins.
        """
        n = len(predictions)
        bins = [i / num_bins for i in range(num_bins + 1)]
        bin_records: List[Dict[str, Any]] = []

        ece = 0.0
        mce = 0.0
        brier_sum = 0.0

        for i in range(num_bins):
            b_low = bins[i]
            b_high = bins[i + 1]

            # Collect items in bin [b_low, b_high) or [b_low, b_high] for last bin
            if i == num_bins - 1:
                items = [p for p in predictions if b_low <= p.stated_probability <= b_high]
            else:
                items = [p for p in predictions if b_low <= p.stated_probability < b_high]

            bin_size = len(items)
            if bin_size > 0:
                bin_acc = sum(1 for p in items if p.is_correct) / bin_size
                bin_conf = sum(p.stated_probability for p in items) / bin_size
                diff = abs(bin_acc - bin_conf)

                ece += (bin_size / n) * diff
                mce = max(mce, diff)

                bin_records.append({
                    "bin_range": f"[{b_low:.1f}, {b_high:.1f}]",
                    "count": bin_size,
                    "accuracy": round(bin_acc, 4),
                    "confidence": round(bin_conf, 4),
                    "gap": round(diff, 4)
                })
            else:
                bin_records.append({
                    "bin_range": f"[{b_low:.1f}, {b_high:.1f}]",
                    "count": 0,
                    "accuracy": 0.0,
                    "confidence": 0.0,
                    "gap": 0.0
                })

        # Brier Score: Mean squared error of probabilities
        for p in predictions:
            y = 1.0 if p.is_correct else 0.0
            brier_sum += (p.stated_probability - y) ** 2

        brier_score = brier_sum / n

        return CalibrationMetrics(
            expected_calibration_error=round(ece, 4),
            max_calibration_error=round(mce, 4),
            brier_score=round(brier_score, 4),
            reliability_bins=bin_records
        )
