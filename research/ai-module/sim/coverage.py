"""
All-Pairs Categorical & Numerical Dimension Coverage Tracker
GrowthOS Randomized Scenario Test Environment

Tracks coverage across:
- Tenant verticals
- Size tiers
- Run modes
- Loyalty cooldown rules
- Ad platforms
- Fault types

Reports aggregate pairwise coverage percentage across test batches.

Strictly NO emojis in code, docstrings, or logs.
"""

import json
from pathlib import Path
from typing import Dict, Set, List, Tuple, Any
from sim.scenario import ScenarioSpec


class CoverageTracker:
    """
    Maintains all-pairs combination tracking and coverage metrics.
    """

    DIMENSIONS = {
        "vertical": ["qsr", "fashion", "electronics", "grocery", "d2c_subscription"],
        "size": ["small", "standard", "stress"],
        "mode": ["random", "edge", "coverage", "golden", "stress"],
        "loyalty_cooldown": ["24h", "48h", "72h", "168h"],
        "has_timeout_fault": ["true", "false"],
        "ad_platform": ["google", "meta"],
    }

    def __init__(self, persistence_file: Optional[Path] = None):
        self.persistence_file = persistence_file
        self.seen_values: Dict[str, Set[str]] = {k: set() for k in self.DIMENSIONS}
        self.seen_pairs: Set[Tuple[str, str, str, str]] = set()  # (d1, v1, d2, v2)
        self.all_possible_pairs = self._compute_all_possible_pairs()

    def _compute_all_possible_pairs(self) -> Set[Tuple[str, str, str, str]]:
        all_pairs = set()
        dim_keys = sorted(list(self.DIMENSIONS.keys()))
        for i in range(len(dim_keys)):
            d1 = dim_keys[i]
            for j in range(i + 1, len(dim_keys)):
                d2 = dim_keys[j]
                for v1 in self.DIMENSIONS[d1]:
                    for v2 in self.DIMENSIONS[d2]:
                        all_pairs.add((d1, v1, d2, v2))
        return all_pairs

    def extract_scenario_dimensions(self, scenario: ScenarioSpec) -> Dict[str, str]:
        tenant = scenario.tenants[0] if scenario.tenants else None
        vertical = tenant.vertical.value if tenant else "qsr"
        cooldown = f"{tenant.loyalty.waiver_cooldown_hours}h" if (tenant and tenant.loyalty) else "48h"
        if cooldown not in self.DIMENSIONS["loyalty_cooldown"]:
            cooldown = "48h"

        has_timeout = "true" if scenario.faults.adapter_timeout_after_success else "false"
        platform = scenario.ads.campaigns[0].platform.value if scenario.ads.campaigns else "google"

        return {
            "vertical": vertical,
            "size": scenario.size.value,
            "mode": scenario.mode.value,
            "loyalty_cooldown": cooldown,
            "has_timeout_fault": has_timeout,
            "ad_platform": platform,
        }

    def record_scenario(self, scenario: ScenarioSpec):
        """Records scenario values and updates pairwise combinations."""
        dims = self.extract_scenario_dimensions(scenario)

        for d, v in dims.items():
            if d in self.seen_values:
                self.seen_values[d].add(v)

        dim_keys = sorted(list(dims.keys()))
        for i in range(len(dim_keys)):
            d1 = dim_keys[i]
            v1 = dims[d1]
            for j in range(i + 1, len(dim_keys)):
                d2 = dim_keys[j]
                v2 = dims[d2]
                pair = (d1, v1, d2, v2)
                if pair in self.all_possible_pairs:
                    self.seen_pairs.add(pair)

    def get_coverage_percentage(self) -> float:
        """Computes current pairwise coverage percentage."""
        if not self.all_possible_pairs:
            return 100.0
        return round((len(self.seen_pairs) / len(self.all_possible_pairs)) * 100.0, 2)

    def save(self, filepath: Path):
        data = {
            "seen_values": {k: list(v) for k, v in self.seen_values.items()},
            "seen_pairs_count": len(self.seen_pairs),
            "total_pairs_count": len(self.all_possible_pairs),
            "coverage_pct": self.get_coverage_percentage(),
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
