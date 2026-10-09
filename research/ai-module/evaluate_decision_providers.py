#!/usr/bin/env python3
"""
Multi-Provider Benchmark Evaluation Harness
GrowthOS Module 4: AI Growth Brain

Executes non-circular evaluation across 200 ground-truth cases comparing:
1. RuleDecisionProvider (Deterministic Heuristics + Policy Baseline)
2. JevDecisionProvider (Fast System 1 Calibrated Probability Classifier)
3. GeminiDecisionProvider (Direct Google Gemini Free-Tier Multi-Model Rotation)

Evaluates:
- Top-1 Accuracy with 95% Wilson Score Confidence Intervals
- Macro F1 Score
- Expected Calibration Error (ECE) and Brier Score
- Latency Distributions: p50, p95, p99 (ms)
- Cost per 1,000 decisions ($0.00 Free-Tier verification)
- Autonomy Gating Eligibility (Accuracy >= 90%, ECE <= 0.10, p95 <= 500ms)

Strictly NO emojis in code, docstrings, or output.
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from domain.evaluation import (
    DecisionBenchmarkCase,
    ProviderPrediction,
    ProviderPerformanceSummary
)
from engines.rule_decision_provider import RuleDecisionProvider
from adapters.jev_decision_provider import JevDecisionProvider
from adapters.gemini_decision_provider import GeminiDecisionProvider
from adapters.gemini_client import GeminiClient
from evaluation.evaluator import BenchmarkEvaluator


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Provider Benchmark Evaluation Harness")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(SCRIPT_DIR / "data" / "benchmarks" / "ground_truth_decisions.jsonl"),
        help="Path to ground truth JSONL dataset"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=200,
        help="Number of cases to evaluate (default: 200)"
    )
    parser.add_argument(
        "--gemini-sample-size",
        type=int,
        default=10,
        help="Number of cases for live Gemini LLM to avoid exceeding free-tier daily rate limits (default: 10)"
    )
    parser.add_argument(
        "--skip-gemini",
        action="store_true",
        help="Skip Gemini LLM evaluation (evaluates Rule and Jev only)"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=str(SCRIPT_DIR / "evaluation" / "benchmark_results_multi_provider.json"),
        help="Path to save evaluation summary JSON"
    )
    return parser.parse_args()


def format_markdown_table(summaries: List[ProviderPerformanceSummary]) -> str:
    """
    Renders comparative performance scorecard in Markdown.
    """
    lines = [
        "| Provider | Sample | Accuracy (95% Wilson CI) | Macro F1 | ECE | Brier | p50 (ms) | p95 (ms) | Cost / 1k | Autonomous? |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for s in summaries:
        ci_str = f"[{s.accuracy_ci_lower_95:.3f}, {s.accuracy_ci_upper_95:.3f}]" if s.accuracy_ci_lower_95 is not None else "N/A"
        acc_str = f"{s.accuracy * 100:.1f}% {ci_str}"
        ece_str = f"{s.calibration.expected_calibration_error:.4f}"
        brier_str = f"{s.calibration.brier_score:.4f}"
        cost_str = f"${s.cost_per_1000_usd:.4f}"
        auton_str = "YES" if s.is_eligible_for_autonomous else "NO"

        lines.append(
            f"| **{s.provider_name}** | {s.sample_count} | {acc_str} | {s.macro_f1:.4f} | {ece_str} | {brier_str} | {s.p50_latency_ms:.1f} | {s.p95_latency_ms:.1f} | {cost_str} | {auton_str} |"
        )
    return "\n".join(lines)


def run_benchmark():
    args = parse_args()
    evaluator = BenchmarkEvaluator()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}")
        sys.exit(1)

    print("====================================================================================================")
    print("                     GROWTHOS MODULE 4: MULTI-PROVIDER BENCHMARK EVALUATION                        ")
    print("====================================================================================================")
    print(f"Dataset: {dataset_path.name}")
    
    all_cases = evaluator.load_jsonl(dataset_path)
    total_loaded = len(all_cases)
    print(f"Loaded {total_loaded} total ground-truth benchmark cases.")

    target_cases = all_cases[:args.sample_size]
    print(f"Evaluating {len(target_cases)} cases across candidate decision providers.")
    print("----------------------------------------------------------------------------------------------------")

    summaries: List[ProviderPerformanceSummary] = []

    # 1. Evaluate RuleDecisionProvider
    print(f"1. Evaluating RuleDecisionProvider on {len(target_cases)} cases...")
    rule_provider = RuleDecisionProvider()
    rule_summary = evaluator.evaluate_provider(
        provider_name="RuleDecisionProvider",
        provider_instance=rule_provider,
        task_type="cart_abandonment_decision",
        cases=target_cases
    )
    summaries.append(rule_summary)
    print(f"   Accuracy: {rule_summary.accuracy * 100:.1f}% (Wilson 95% CI: [{rule_summary.accuracy_ci_lower_95:.3f}, {rule_summary.accuracy_ci_upper_95:.3f}])")
    print(f"   p95 Latency: {rule_summary.p95_latency_ms:.2f}ms | Cost/1k: ${rule_summary.cost_per_1000_usd:.4f}")

    # 2. Evaluate JevDecisionProvider (System 1 fast calibrated classifier)
    print(f"\n2. Evaluating JevDecisionProvider on {len(target_cases)} cases...")
    jev_provider = JevDecisionProvider(temperature_calibration=True)
    jev_summary = evaluator.evaluate_provider(
        provider_name="JevDecisionProvider (Calibrated)",
        provider_instance=jev_provider,
        task_type="cart_abandonment_decision",
        cases=target_cases
    )
    summaries.append(jev_summary)
    print(f"   Accuracy: {jev_summary.accuracy * 100:.1f}% (Wilson 95% CI: [{jev_summary.accuracy_ci_lower_95:.3f}, {jev_summary.accuracy_ci_upper_95:.3f}])")
    print(f"   ECE: {jev_summary.calibration.expected_calibration_error:.4f} | Brier: {jev_summary.calibration.brier_score:.4f}")
    print(f"   p95 Latency: {jev_summary.p95_latency_ms:.2f}ms | Cost/1k: ${jev_summary.cost_per_1000_usd:.4f}")

    # 3. Evaluate GeminiDecisionProvider (Direct Google Gemini Free-Tier Rotation)
    if not args.skip_gemini:
        gemini_count = min(args.gemini_sample_size, len(target_cases))
        print(f"\n3. Evaluating GeminiDecisionProvider on {gemini_count} cases (Free-Tier quota protection)...")
        try:
            gemini_provider = GeminiDecisionProvider()
            gemini_cases = target_cases[:gemini_count]
            gemini_summary = evaluator.evaluate_provider(
                provider_name="GeminiDecisionProvider (gemini-2.5-flash)",
                provider_instance=gemini_provider,
                task_type="cart_abandonment_decision",
                cases=gemini_cases
            )
            summaries.append(gemini_summary)
            print(f"   Accuracy: {gemini_summary.accuracy * 100:.1f}% (Wilson 95% CI: [{gemini_summary.accuracy_ci_lower_95:.3f}, {gemini_summary.accuracy_ci_upper_95:.3f}])")
            print(f"   ECE: {gemini_summary.calibration.expected_calibration_error:.4f} | Cost/1k: ${gemini_summary.cost_per_1000_usd:.4f}")
        except Exception as e:
            print(f"   Notice: Live Gemini evaluation bypassed ({e}). Operating in 100% Free Tier fallback mode.")
    else:
        print("\n3. Gemini live evaluation skipped via --skip-gemini flag.")

    # Render Markdown Scorecard Table
    print("\n====================================================================================================")
    print("                                  COMPARATIVE BENCHMARK SCORECARD                                   ")
    print("====================================================================================================")
    table_md = format_markdown_table(summaries)
    print(table_md)
    print("====================================================================================================")

    # Save to JSON
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in summaries], f, indent=2)
    print(f"Saved evaluation scorecard JSON to {out_path}")


if __name__ == "__main__":
    run_benchmark()
