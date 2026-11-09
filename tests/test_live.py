from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from checks import deterministic_findings, extract_and_reconcile
from content import scenario_by_id
from evaluation import evaluate
from models import TranscriptPass, Verdict


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_EVALS") != "1",
        reason="RUN_LIVE_EVALS=1 is required for paid live checks",
    ),
]


def _require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.fail("RUN_LIVE_EVALS=1 but OPENAI_API_KEY is missing from the process environment and .env")


def test_live_source_grounded_evaluation() -> None:
    """Exercise the configured Responses model without requiring an audio fixture."""
    _require_api_key()
    scenario = scenario_by_id("S1")
    text = "INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO"
    primary = TranscriptPass(name="primary", raw_text=text)
    verifier = TranscriptPass(name="verification", raw_text=text)
    observations = extract_and_reconcile(scenario, primary, verifier)
    frozen = deterministic_findings(scenario, observations)

    result = evaluate(scenario, primary, verifier, observations, frozen)

    assert result.evaluation_complete, result.limitations
    assert result.overall_verdict == Verdict.CORRECT, result.model_dump(mode="json")
    assert not any("did not complete" in item.lower() for item in result.limitations)


def test_live_recorded_audio_manifest_when_available() -> None:
    """Leave human-audio validation optional until a reviewed manifest is supplied."""
    fixture_dir = os.getenv("ATC_APPROVED_AUDIO_FIXTURES")
    if not fixture_dir:
        pytest.skip("Approved human-recorded audio fixtures were deferred")
    manifest = Path(fixture_dir) / "manifest.json"
    if not manifest.is_file():
        pytest.skip("Audio fixture directory exists but has no reviewed manifest.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not data.get("recordings"):
        pytest.skip("Audio fixture manifest contains no reviewed recordings")
    pytest.skip("Recorded-audio runner remains deferred until the manifest contract is approved")
