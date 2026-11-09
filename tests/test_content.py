from __future__ import annotations

import hashlib
from pathlib import Path

from content import load_manual_collection, load_scenarios


ROOT = Path(__file__).resolve().parents[1]


def test_five_scenarios_and_examples_resolve() -> None:
    scenarios = load_scenarios()
    assert [item.id for item in scenarios] == ["S1", "S2", "S3", "S4", "S5"]
    assert all(item.acceptable_examples for item in scenarios)
    assert all(len(item.incorrect_examples) >= 2 for item in scenarios)
    excerpt_ids = {item.id for item in load_manual_collection().excerpts}
    assert all(set(item.excerpt_ids) <= excerpt_ids for item in scenarios)


def test_manual_metadata_matches_supplied_pdf() -> None:
    collection = load_manual_collection()
    digest = hashlib.sha256((ROOT / "Manual of Air Traffic Services, Part-1 Edition 7.pdf").read_bytes()).hexdigest().upper()
    assert collection.sha256 == digest
    assert collection.edition == "7.0"
    assert all(321 <= page <= 376 for excerpt in collection.excerpts for page in excerpt.pdf_pages)


def test_stable_check_ids_are_scenario_scoped() -> None:
    for scenario in load_scenarios():
        assert all(check_id.startswith(f"{scenario.id}.") for check_id in scenario.mandatory_elements)
        assert set(scenario.mandatory_elements) == set(scenario.check_dimensions)
