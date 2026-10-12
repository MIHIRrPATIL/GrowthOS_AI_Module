"""
Simulation Run Storage and Artifact Persistence
GrowthOS Randomized Scenario Test Environment

Saves run artifacts under runs/DATE_SEED/:
- scenario.json
- card.txt
- report.json

Strictly NO emojis in code, docstrings, or logs.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .scenario import ScenarioSpec


def save_run_artifacts(
    scenario: ScenarioSpec,
    card_text: str,
    report: Optional[Dict[str, Any]] = None,
    base_dir: str = "runs"
) -> Path:
    """
    Saves scenario specification, formatted card, and execution report.
    Returns the created directory Path.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = Path(base_dir) / f"{date_str}_{scenario.seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. scenario.json
    scenario_path = run_dir / "scenario.json"
    with open(scenario_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(scenario.model_dump(mode="json"), indent=2))

    # 2. card.txt
    card_path = run_dir / "card.txt"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card_text + "\n")

    # 3. report.json
    report_path = run_dir / "report.json"
    report_data = report or {
        "seed": scenario.seed,
        "scenario_hash": scenario.scenario_hash(),
        "catalog_version": scenario.catalog_version,
        "mode": scenario.mode.value,
        "size": scenario.size.value,
        "status": "initialized",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(report_data, indent=2))

    return run_dir
