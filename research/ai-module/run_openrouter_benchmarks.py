#!/usr/bin/env python3
"""
OpenRouter Benchmark Runner
GrowthOS Module 4: AI Growth Brain

Evaluates frontier LLM models on OpenRouter against standardized benchmark suites:
1. Action Routing (20 labeled scenarios): Telemetry anomaly -> optimal business action
2. Query Classification (20 labeled queries): Merchant question -> catalog metric mapping
3. Evidence Support (20 labeled claims): Claim verification -> anti-hallucination checking

Computes:
- Top-1 Accuracy (%)
- Macro F1 Score
- Expected Calibration Error (ECE)
- Max Calibration Error (MCE)
- Brier Score
- Latency Distribution: p50, p95, p99 (ms)
- Token Consumption & Cost per 1,000 queries ($)
- Autonomous Gating Eligibility (Accuracy >= 90%, ECE <= 0.10, p95 <= 500ms)

Strictly NO emojis used in logs or output.
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from domain.evaluation import (
    DecisionBenchmarkCase,
    ProviderPrediction,
    ProviderPerformanceSummary
)
from adapters.openrouter_client import OpenRouterClient, load_dotenv_if_present
from adapters.openrouter_decision_provider import OpenRouterDecisionProvider
from adapters.llm_decision_provider import LLMDecisionProvider
from adapters.jev_decision_provider import JevDecisionProvider
from engines.rule_decision_provider import RuleDecisionProvider
from evaluation.evaluator import BenchmarkEvaluator


RECOMMENDED_MODELS = [
    {
        "model_id": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "Free MoE (120B params, 12B active), 262k context, $0.00/1M tokens (Recommended)",
        "recommended": True
    },
    {
        "model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "description": "Free MoE (550B params, 55B active), 1,000,000 context, $0.00/1M tokens",
        "recommended": True
    },
    {
        "model_id": "dots-studio/dots-3-note-preview:free",
        "description": "Free MoE (280B params, 16B active), 512,000 context, $0.00/1M tokens",
        "recommended": False
    },
    {
        "model_id": "inclusionai/ling-3.0-flash-sante:free",
        "description": "Free MoE (124B params, 5.1B active), 262,144 context, $0.00/1M tokens",
        "recommended": False
    },
    {
        "model_id": "poolside/laguna-s-2.1:free",
        "description": "Free MoE (118B params, 8B active), 262,144 context, $0.00/1M tokens",
        "recommended": False
    },
    {
        "model_id": "nvidia/nemotron-3.5-lightning:free",
        "description": "Free MoE (30B params, 3B active), 1,000,000 context, $0.00/1M tokens",
        "recommended": False
    },
    {
        "model_id": "cohere/north-mini-code:free",
        "description": "Free MoE (30B params, 3B active), 256,000 context, $0.00/1M tokens",
        "recommended": False
    },
    {
        "model_id": "anthropic/claude-3.5-haiku",
        "description": "Fast & high-tier calibration, $0.80/$4.00 per 1M tokens",
        "recommended": False
    },
    {
        "model_id": "anthropic/claude-3.5-sonnet",
        "description": "Frontier gold-standard reasoning, $3.00/$15.00 per 1M tokens",
        "recommended": False
    },
    {
        "model_id": "meta-llama/llama-3.3-70b-instruct",
        "description": "Premier open-weights model, $0.12/$0.30 per 1M tokens",
        "recommended": False
    },
    {
        "model_id": "openai/gpt-4o-mini",
        "description": "Compact commercial baseline, $0.15/$0.60 per 1M tokens",
        "recommended": False
    },
    {
        "model_id": "deepseek/deepseek-chat",
        "description": "Ultra cost-effective frontier, $0.14/$0.28 per 1M tokens",
        "recommended": False
    }
]


def print_banner(text: str, width: int = 110):
    print("=" * width)
    print(text.center(width))
    print("=" * width)


def print_section(text: str, width: int = 110):
    print("\n" + "-" * width)
    print(text)
    print("-" * width)


def print_scorecard(summaries: List[ProviderPerformanceSummary]):
    """Prints a clean ASCII scorecard table comparing all evaluated providers."""
    print("\n" + "=" * 115)
    print("BENCHMARK EVALUATION SCORECARD")
    print("=" * 115)
    header = (
        f"{'Provider / Model':<35} | "
        f"{'Task':<20} | "
        f"{'Accuracy':<8} | "
        f"{'Macro F1':<8} | "
        f"{'ECE':<6} | "
        f"{'Brier':<6} | "
        f"{'p50 ms':<7} | "
        f"{'p95 ms':<7} | "
        f"{'Cost/1k':<9} | "
        f"{'Autonomous'}"
    )
    print(header)
    print("-" * 115)

    for s in summaries:
        name = s.provider_name
        if len(name) > 35:
            name = name[:32] + "..."
        row = (
            f"{name:<35} | "
            f"{s.task_type:<20} | "
            f"{s.accuracy * 100.0:>6.1f}% | "
            f"{s.macro_f1:>8.3f} | "
            f"{s.calibration.expected_calibration_error:>6.3f} | "
            f"{s.calibration.brier_score:>6.3f} | "
            f"{s.p50_latency_ms:>7.1f} | "
            f"{s.p95_latency_ms:>7.1f} | "
            f"${s.cost_per_1000_usd:>8.4f} | "
            f"{'QUALIFIED' if s.is_eligible_for_autonomous else 'GATED'}"
        )
        print(row)

    print("-" * 115)
    print("Autonomy Criteria: Top-1 Accuracy >= 90.0%, ECE <= 0.100, and p95 Latency <= 500.0 ms.")
    print("=" * 115)


def check_openrouter_key() -> tuple[bool, str]:
    """Checks if OPENROUTER_API_KEY is configured in the environment."""
    load_dotenv_if_present()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return bool(key), key


def print_missing_key_guidance():
    """Prints explicit instructions on how to set up OpenRouter API keys and models."""
    print_banner("OPENROUTER API KEY NOT CONFIGURED")
    print(
        "\n[NOTICE] OPENROUTER_API_KEY was not found in your environment variables.\n"
        "To run live benchmark evaluations against OpenRouter models, configure your key:\n"
        "\n"
        "  Bash / Zsh:\n"
        "    export OPENROUTER_API_KEY=\"sk-or-v1-xxxxxxxxxxxxxxxx\"\n"
        "\n"
        "  Single-command execution:\n"
        "    OPENROUTER_API_KEY=\"sk-or-v1-...\" python run_openrouter_benchmarks.py\n"
        "\n"
        "Configured / Recommended OpenRouter Models:"
    )
    for m in RECOMMENDED_MODELS:
        rec_tag = " [RECOMMENDED DEFAULT]" if m["recommended"] else ""
        print(f"  - {m['model_id']:<38} {m['description']}{rec_tag}")
    print("\nProceeding with DRY-RUN simulation mode to demonstrate benchmark scorecard...")
    print("=" * 110 + "\n")


def run_benchmarks(
    models: List[str],
    tasks: List[str],
    include_baselines: bool = True,
    dry_run: bool = False,
    output_path: Optional[str] = None
) -> List[ProviderPerformanceSummary]:
    evaluator = BenchmarkEvaluator()
    all_summaries: List[ProviderPerformanceSummary] = []

    has_key, api_key = check_openrouter_key()
    is_live = has_key and not dry_run

    if not is_live and not dry_run:
        print_missing_key_guidance()

    mode_label = "LIVE OPENROUTER EVALUATION" if is_live else "DRY-RUN SIMULATED EVALUATION"
    print_banner(f"{mode_label} (GrowthOS Module 4)")

    # 1. Baseline providers (if requested)
    if include_baselines:
        print_section("EVALUATING BASELINE BENCHMARKS (Rules vs Jev vs Offline Mock LLM)")
        rule_provider = RuleDecisionProvider()
        llm_provider = LLMDecisionProvider()
        jev_calibrated = JevDecisionProvider(temperature_calibration=True)
        jev_uncalibrated = JevDecisionProvider(temperature_calibration=False)

        baselines = [
            ("rules", rule_provider),
            ("mock_llm", llm_provider),
            ("jev_calibrated", jev_calibrated),
            ("jev_uncalibrated", jev_uncalibrated),
        ]

        for task in tasks:
            print(f"Running baseline suites on task: '{task}'...")
            cases = evaluator.load_dataset(task)
            for name, prov in baselines:
                t0 = time.perf_counter()
                summary = evaluator.evaluate_provider(name, prov, task, cases=cases)
                elapsed = time.perf_counter() - t0
                all_summaries.append(summary)
                print(f"  [{name:<18}] Task: {task:<22} Accuracy: {summary.accuracy*100:>5.1f}% | ECE: {summary.calibration.expected_calibration_error:.3f} | Elapsed: {elapsed:.2f}s")

    # 2. OpenRouter Models
    print_section(f"EVALUATING OPENROUTER MODELS: {', '.join(models)}")

    for model_name in models:
        for task in tasks:
            cases = evaluator.load_dataset(task)
            print(f"\nEvaluating Model '{model_name}' on task '{task}' ({len(cases)} cases)...")

            if is_live:
                client = OpenRouterClient(api_key=api_key, model=model_name)
                provider = OpenRouterDecisionProvider(client=client, model=model_name)
                display_name = f"openrouter/{model_name}"
            else:
                # Dry run simulation mode with realistic model latency & pricing
                cost_rates = OpenRouterClient().get_model_rates(model_name)
                provider = LLMDecisionProvider()
                display_name = f"simulated/{model_name}"

            t0 = time.perf_counter()
            summary = evaluator.evaluate_provider(display_name, provider, task, cases=cases)
            elapsed = time.perf_counter() - t0
            all_summaries.append(summary)

            print(f"  Results for {display_name} on {task}:")
            print(f"    - Accuracy: {summary.accuracy * 100.0:.1f}%")
            print(f"    - Macro F1: {summary.macro_f1:.3f}")
            print(f"    - Expected Calibration Error (ECE): {summary.calibration.expected_calibration_error:.3f}")
            print(f"    - Brier Score: {summary.calibration.brier_score:.3f}")
            print(f"    - Latency: p50={summary.p50_latency_ms:.1f}ms, p95={summary.p95_latency_ms:.1f}ms")
            print(f"    - Estimated Cost per 1k Queries: ${summary.cost_per_1000_usd:.4f}")
            print(f"    - Autonomous Qualification: {'YES' if summary.is_eligible_for_autonomous else 'NO'}")
            print(f"    - Evaluation Run Time: {elapsed:.2f}s")

    # 3. Print Final Scorecard
    print_scorecard(all_summaries)

    # 4. Save JSON Report
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        serializable = [s.model_dump() for s in all_summaries]
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode": "live" if is_live else "dry_run",
                "evaluated_models": models,
                "tasks": tasks,
                "summaries": serializable
            }, f, indent=2)
        print(f"\n[REPORT SAVED] Detailed benchmark scorecard saved to: {out_file.resolve()}")

    return all_summaries


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run live and baseline benchmarks on OpenRouter models for GrowthOS AI Module."
    )
    parser.add_argument(
        "--models", "-m",
        type=str,
        default="google/gemini-2.0-flash-001",
        help="Comma-separated OpenRouter model IDs (default: 'google/gemini-2.0-flash-001')"
    )
    parser.add_argument(
        "--tasks", "-t",
        type=str,
        default="all",
        help="Comma-separated task types: 'action_routing', 'query_classification', 'evidence_support', or 'all' (default: 'all')"
    )
    parser.add_argument(
        "--no-baselines",
        action="store_true",
        help="Skip running local baseline comparisons (rules, mock LLM, Jev)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force simulated dry-run mode even if API key is present"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="evaluation/benchmark_results_openrouter.json",
        help="Output JSON report filepath (default: 'evaluation/benchmark_results_openrouter.json')"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]

    if args.tasks.strip().lower() == "all":
        tasks = ["action_routing", "query_classification", "evidence_support"]
    else:
        tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]

    run_benchmarks(
        models=models,
        tasks=tasks,
        include_baselines=not args.no_baselines,
        dry_run=args.dry_run,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
