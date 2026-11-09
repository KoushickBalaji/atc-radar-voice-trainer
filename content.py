from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from models import ManualCollection, ManualExcerpt, Scenario, ScenarioCollection


ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_manual_collection(path: Path | None = None) -> ManualCollection:
    target = path or ROOT / "data" / "manual_excerpts.json"
    collection = ManualCollection.model_validate_json(target.read_text(encoding="utf-8"))
    ids = [item.id for item in collection.excerpts]
    if len(ids) != len(set(ids)):
        raise ValueError("Manual excerpt IDs must be unique")
    if not collection.sha256 or len(collection.sha256) != 64:
        raise ValueError("Manual metadata must include a SHA-256")
    return collection


@lru_cache(maxsize=1)
def load_scenarios(path: Path | None = None) -> list[Scenario]:
    target = path or ROOT / "data" / "scenarios.json"
    collection = ScenarioCollection.model_validate_json(target.read_text(encoding="utf-8"))
    scenarios = collection.scenarios
    if len(scenarios) != 5 or {item.id for item in scenarios} != {"S1", "S2", "S3", "S4", "S5"}:
        raise ValueError("Exactly scenarios S1-S5 are required")
    excerpt_ids = {item.id for item in load_manual_collection().excerpts}
    for scenario in scenarios:
        missing = set(scenario.excerpt_ids) - excerpt_ids
        if missing:
            raise ValueError(f"{scenario.id} references unknown excerpts: {sorted(missing)}")
        if len(scenario.acceptable_examples) < 1 or len(scenario.incorrect_examples) < 2:
            raise ValueError(f"{scenario.id} needs one acceptable and two incorrect examples")
        if set(scenario.mandatory_elements) != set(scenario.check_dimensions):
            raise ValueError(f"{scenario.id} mandatory/check-dimension IDs differ")
    return scenarios


def scenario_by_id(scenario_id: str) -> Scenario:
    return next(item for item in load_scenarios() if item.id == scenario_id)


def excerpts_for(scenario: Scenario) -> list[ManualExcerpt]:
    by_id = {item.id: item for item in load_manual_collection().excerpts}
    return [by_id[item] for item in scenario.excerpt_ids]
