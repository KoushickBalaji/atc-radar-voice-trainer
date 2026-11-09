from __future__ import annotations

import pytest

from checks import aggregate, deterministic_findings, extract_and_reconcile
from content import scenario_by_id
from models import ExpressionKind, RecognitionStatus, TranscriptPass, Verdict


def passes(text: str) -> tuple[TranscriptPass, TranscriptPass]:
    return TranscriptPass(name="primary", raw_text=text), TranscriptPass(name="verification", raw_text=text)


@pytest.mark.parametrize(
    ("scenario_id", "text"),
    [
        ("S1", "INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO"),
        ("S2", "INDAIR EIGHT ZERO NINE TURN LEFT HEADING ZERO EIGHT ZERO"),
        ("S3", "INDAIR EIGHT ZERO NINE FOR DEPARTURE SQUAWK THREE FOUR TWO FIVE"),
        ("S4", "INDAIR EIGHT ZERO NINE TAXI TO HOLDING POINT ONE RUNWAY TWO SEVEN VIA ALFA HOLD SHORT OF RUNWAY TWO SEVEN"),
        ("S5", "INDAIR EIGHT ZERO NINE NEGATIVE I SAY AGAIN CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO"),
    ],
)
def test_canonical_responses_pass_deterministic_checks(scenario_id: str, text: str) -> None:
    scenario = scenario_by_id(scenario_id)
    observations = extract_and_reconcile(scenario, *passes(text))
    result = aggregate(deterministic_findings(scenario, observations))
    assert result.overall_verdict == Verdict.CORRECT


@pytest.mark.parametrize(
    ("scenario_id", "text", "check_id"),
    [
        ("S1", "INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE NINE ZERO", "S1.level"),
        ("S1", "INDAIR EIGHT ZERO NINE MAINTAIN FLIGHT LEVEL ONE EIGHT ZERO", "S1.action"),
        ("S2", "INDAIR EIGHT ZERO NINE TURN RIGHT HEADING ZERO EIGHT ZERO", "S2.direction"),
        ("S3", "INDAIR EIGHT ZERO NINE SQUAWK THREE FOUR TWO SIX", "S3.code"),
        ("S3", "INDAIR EIGHT ZERO NINE CONFIRM SQUAWK THREE FOUR TWO FIVE", "S3.action"),
        ("S4", "INDAIR EIGHT ZERO NINE TAXI TO HOLDING POINT ONE RUNWAY TWO SEVEN VIA BRAVO HOLD SHORT OF RUNWAY TWO SEVEN", "S4.route"),
        ("S4", "INDAIR EIGHT ZERO NINE TAXI TO HOLDING POINT ONE RUNWAY TWO SEVEN VIA ALFA CROSS RUNWAY TWO SEVEN", "S4.hold_short"),
        ("S5", "INDAIR EIGHT ZERO NINE CORRECT", "S5.correction"),
        ("S5", "INDAIR EIGHT ZERO NINE NEGATIVE CLIMB TO FLIGHT LEVEL TWO EIGHT ZERO", "S5.level"),
        ("S2", "EIGHT ZERO NINE TURN LEFT HEADING ZERO EIGHT ZERO", "S2.callsign"),
    ],
)
def test_deliberate_errors_never_pass(scenario_id: str, text: str, check_id: str) -> None:
    scenario = scenario_by_id(scenario_id)
    findings = deterministic_findings(scenario, extract_and_reconcile(scenario, *passes(text)))
    finding = next(item for item in findings if item.check_id == check_id)
    assert finding.status == Verdict.INCORRECT


def test_heading_value_and_wording_are_separate() -> None:
    scenario = scenario_by_id("S2")
    digit_words = extract_and_reconcile(scenario, *passes("INDAIR EIGHT ZERO NINE TURN LEFT HEADING ZERO EIGHT ZERO"))
    grouped = extract_and_reconcile(scenario, *passes("INDAIR EIGHT ZERO NINE TURN LEFT HEADING EIGHTY"))
    numeral = extract_and_reconcile(scenario, *passes("INDAIR 809 TURN LEFT HEADING 080"))
    by_field = lambda observations: next(item for item in observations if item.field == "heading")
    assert by_field(digit_words).canonical_value == "080"
    assert by_field(digit_words).expression_kind == ExpressionKind.DIGIT_WORDS
    assert by_field(grouped).canonical_value == "080"
    assert by_field(grouped).expression_kind == ExpressionKind.GROUPED_WORDS
    assert by_field(numeral).canonical_value == "080"
    assert by_field(numeral).expression_kind == ExpressionKind.NUMERAL


def test_primary_verifier_disagreement_is_uncertain() -> None:
    scenario = scenario_by_id("S3")
    observations = extract_and_reconcile(
        scenario,
        TranscriptPass(name="primary", raw_text="INDAIR EIGHT ZERO NINE SQUAWK THREE FOUR TWO FIVE"),
        TranscriptPass(name="verification", raw_text="INDAIR EIGHT ZERO NINE SQUAWK THREE FOUR TWO SIX"),
    )
    code = next(item for item in observations if item.field == "code")
    assert code.recognition_status == RecognitionStatus.DISPUTED
    assert code.canonical_value is None
    assert next(item for item in deterministic_findings(scenario, observations) if item.check_id == "S3.code").status == Verdict.UNCERTAIN


def test_one_failed_pass_makes_all_dependent_fields_unresolved() -> None:
    scenario = scenario_by_id("S1")
    observations = extract_and_reconcile(
        scenario,
        TranscriptPass(name="primary", raw_text="INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO"),
        TranscriptPass(name="verification", error_category="timeout"),
    )
    assert all(item.recognition_status == RecognitionStatus.UNRESOLVED for item in observations)
    assert all(item.status == Verdict.UNCERTAIN for item in deterministic_findings(scenario, observations))


def test_incomplete_squawk_is_not_padded_toward_expected_value() -> None:
    scenario = scenario_by_id("S3")
    observations = extract_and_reconcile(scenario, *passes("INDAIR EIGHT ZERO NINE SQUAWK THREE FOUR TWO"))
    code = next(item for item in observations if item.field == "code")
    assert code.canonical_value == "342"
    assert code.canonical_value != "3425"


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("THREE FOUR TWO FIVE", "3425"),
        ("THREE FOUR FIVE TWO", "3452"),
        ("THREE FOUR TWO SIX", "3426"),
        ("THREE FOUR TWO", "342"),
        ("THREE FOUR TWO FIVE FIVE", "34255"),
    ],
)
def test_squawk_digit_order_repetition_and_truncation_are_preserved(spoken: str, expected: str) -> None:
    scenario = scenario_by_id("S3")
    observations = extract_and_reconcile(scenario, *passes(f"INDAIR EIGHT ZERO NINE SQUAWK {spoken}"))
    assert next(item for item in observations if item.field == "code").canonical_value == expected


def test_conflicting_self_correction_is_unresolved_not_answer_selected() -> None:
    scenario = scenario_by_id("S1")
    text = "INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO CORRECTION FLIGHT LEVEL ONE NINE ZERO"
    observations = extract_and_reconcile(scenario, *passes(text))
    level = next(item for item in observations if item.field == "level")
    assert level.recognition_status == RecognitionStatus.UNRESOLVED
    assert level.canonical_value is None


def test_flight_level_is_not_extracted_from_scenario_or_prior_readback() -> None:
    scenario = scenario_by_id("S5")
    observations = extract_and_reconcile(scenario, *passes("INDAIR EIGHT ZERO NINE NEGATIVE"))
    level = next(item for item in observations if item.field == "level")
    assert level.recognition_status == RecognitionStatus.MISSING
