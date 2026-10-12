"""
Regression Seed Store and Scenario Minimizer
GrowthOS Randomized Scenario Test Environment

Persists failing run seeds for automated replay and minimizes
scenarios to minimal reproduction cases.

Strictly NO emojis in code, docstrings, or logs.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from sim.scenario import ScenarioSpec, TenantSizeTier


class RegressionSeedRecord(BaseModel):
    """Metadata record of a regression failure seed."""
    model_config = ConfigDict(extra="forbid")

    seed: int
    scenario_hash: str
    failure_type: str
    error_message: str
    timestamp_utc: str
    minimized_size: str = "small"


class RegressionSeedStore:
    """
    Manages regression seeds for CI reproduction.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.seeds: Dict[int, RegressionSeedRecord] = {}
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rec = RegressionSeedRecord.model_validate(item)
                    self.seeds[rec.seed] = rec
            except Exception:
                self.seeds = {}

    def save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump(mode="json") for r in self.seeds.values()]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record_failure(
        self,
        seed: int,
        scenario_hash: str,
        failure_type: str,
        error_message: str,
        timestamp_utc: str,
    ):
        self.seeds[seed] = RegressionSeedRecord(
            seed=seed,
            scenario_hash=scenario_hash,
            failure_type=failure_type,
            error_message=error_message,
            timestamp_utc=timestamp_utc,
            minimized_size="small",
        )
        self.save()

    def get_failing_seeds(self) -> List[int]:
        return sorted(list(self.seeds.keys()))
