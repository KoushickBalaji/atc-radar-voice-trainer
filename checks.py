from __future__ import annotations

import re
from collections.abc import Iterable

from models import (
    AssessmentResult,
    Dimension,
    ExpressionKind,
    FieldEvidence,
    Finding,
    Observation,
    RecognitionStatus,
    Scenario,
    TranscriptPass,
    Verdict,
)


DIGITS = {
    "ZERO": "0", "OH": "0", "WUN": "1", "ONE": "1", "TOO": "2", "TWO": "2",
    "TREE": "3", "THREE": "3", "FOUR": "4", "FOWER": "4", "FIFE": "5", "FIVE": "5",
    "SIX": "6", "SEVEN": "7", "EIGHT": "8", "AIT": "8", "NINE": "9", "NINER": "9",
}
GROUPED = {
    "TEN": "10", "TWENTY": "20", "THIRTY": "30", "FORTY": "40", "FIFTY": "50",
    "SIXTY": "60", "SEVENTY": "70", "EIGHTY": "80", "NINETY": "90",
    "HUNDRED": "00", "THOUSAND": "000",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Z0-9]+", text.upper())


def _find_sequence(tokens: list[str], sequence: list[str], start: int = 0) -> int | None:
    for index in range(start, len(tokens) - len(sequence) + 1):
        if tokens[index:index + len(sequence)] == sequence:
            return index
    return None


def _parse_number_tokens(tokens: list[str], start: int, max_digits: int, width: int | None) -> FieldEvidence:
    if start >= len(tokens):
        return FieldEvidence()
    first = tokens[start]
    if first.isdigit():
        raw = first
        value = raw.zfill(width) if width and len(raw) <= width else raw
        return FieldEvidence(raw_substring=raw, value=value, expression_kind=ExpressionKind.NUMERAL)
    if first in GROUPED:
        raw = first
        value = GROUPED[first]
        if width and len(value) <= width:
            value = value.zfill(width)
        return FieldEvidence(raw_substring=raw, value=value, expression_kind=ExpressionKind.GROUPED_WORDS)
    digits: list[str] = []
    raw_tokens: list[str] = []
    for token in tokens[start:]:
        if token not in DIGITS:
            break
        digits.append(DIGITS[token])
        raw_tokens.append(token)
    if not digits:
        return FieldEvidence()
    value = "".join(digits)
    if width and len(value) == width:
        canonical = value
    else:
        canonical = value
    return FieldEvidence(raw_substring=" ".join(raw_tokens), value=canonical, expression_kind=ExpressionKind.DIGIT_WORDS)


def _number_after(tokens: list[str], cue: list[str], max_digits: int, width: int | None = None, start: int = 0) -> FieldEvidence:
    matches: list[FieldEvidence] = []
    cursor = start
    while True:
        index = _find_sequence(tokens, cue, cursor)
        if index is None:
            break
        matches.append(_parse_number_tokens(tokens, index + len(cue), max_digits, width))
        cursor = index + len(cue)
    matches = [item for item in matches if item.raw_substring is not None]
    if not matches:
        return FieldEvidence()
    values = {item.value for item in matches}
    if len(values) > 1 or None in values:
        return FieldEvidence(
            raw_substring=" | ".join(item.raw_substring or "" for item in matches),
            expression_kind=ExpressionKind.UNRESOLVED,
        )
    return matches[0]


def _lexical(tokens: list[str], options: dict[str, str]) -> FieldEvidence:
    matches = [(token, value) for token, value in options.items() if token in tokens]
    values = {value for _, value in matches}
    if len(values) > 1:
        return FieldEvidence(raw_substring=" | ".join(token for token, _ in matches), expression_kind=ExpressionKind.UNRESOLVED)
    if matches:
        token, value = matches[0]
        return FieldEvidence(raw_substring=token, value=value, expression_kind=ExpressionKind.LEXICAL)
    return FieldEvidence()


def extract_pass_observations(scenario: Scenario, transcript: TranscriptPass) -> dict[str, FieldEvidence]:
    if transcript.error_category or not transcript.raw_text:
        return {check_id.split(".", 1)[1]: FieldEvidence() for check_id in scenario.mandatory_elements}
    tokens = _tokens(transcript.raw_text)
    fields: dict[str, FieldEvidence] = {}

    indair = _find_sequence(tokens, ["INDAIR"])
    callsign = _parse_number_tokens(tokens, indair + 1, 3, None) if indair is not None else FieldEvidence()
    if callsign.value is not None:
        callsign = FieldEvidence(
            raw_substring=f"INDAIR {callsign.raw_substring}",
            value=f"INDAIR {callsign.value}",
            expression_kind=callsign.expression_kind,
        )
    fields["callsign"] = callsign

    if scenario.id in {"S1", "S5"}:
        fields["action"] = _lexical(tokens, {"CLIMB": "climb", "MAINTAIN": "maintain", "DESCEND": "descend"})
        fields["level"] = _number_after(tokens, ["FLIGHT", "LEVEL"], 3)
    elif scenario.id == "S2":
        fields["action"] = _lexical(tokens, {"TURN": "turn", "FLY": "fly", "CONTINUE": "continue"})
        fields["direction"] = _lexical(tokens, {"LEFT": "left", "RIGHT": "right"})
        fields["heading"] = _number_after(tokens, ["HEADING"], 3, width=3)
    elif scenario.id == "S3":
        if "CONFIRM" in tokens:
            fields["action"] = FieldEvidence(raw_substring="CONFIRM SQUAWK", value="confirm", expression_kind=ExpressionKind.LEXICAL)
        elif "RESET" in tokens:
            fields["action"] = FieldEvidence(raw_substring="RESET SQUAWK", value="reset", expression_kind=ExpressionKind.LEXICAL)
        else:
            fields["action"] = _lexical(tokens, {"SQUAWK": "squawk"})
        fields["code"] = _number_after(tokens, ["SQUAWK"], 4)
    elif scenario.id == "S4":
        fields["action"] = _lexical(tokens, {"TAXI": "taxi", "CROSS": "cross"})
        fields["holding_point"] = _number_after(tokens, ["HOLDING", "POINT"], 2)
        fields["runway"] = _number_after(tokens, ["RUNWAY"], 2)
        via = _find_sequence(tokens, ["VIA"])
        route = tokens[via + 1] if via is not None and via + 1 < len(tokens) else None
        route_value = "A" if route in {"A", "ALFA", "ALPHA"} else ("B" if route in {"B", "BRAVO"} else route)
        fields["route"] = FieldEvidence(raw_substring=route, value=route_value, expression_kind=ExpressionKind.LEXICAL if route else ExpressionKind.UNRESOLVED)
        fields["hold_short"] = _number_after(tokens, ["HOLD", "SHORT", "OF", "RUNWAY"], 2)
        if fields["hold_short"].value is None and _find_sequence(tokens, ["CROSS", "RUNWAY"]) is not None:
            cross = _number_after(tokens, ["CROSS", "RUNWAY"], 2)
            fields["hold_short"] = FieldEvidence(raw_substring=f"CROSS RUNWAY {cross.raw_substring}", value=f"cross:{cross.value}", expression_kind=cross.expression_kind)

    if scenario.id == "S5":
        if "CORRECT" in tokens and "CORRECTION" not in tokens:
            fields["correction"] = FieldEvidence(raw_substring="CORRECT", value="confirm", expression_kind=ExpressionKind.LEXICAL)
        elif "NEGATIVE" in tokens or "CORRECTION" in tokens:
            marker = "NEGATIVE" if "NEGATIVE" in tokens else "CORRECTION"
            fields["correction"] = FieldEvidence(raw_substring=marker, value="correction", expression_kind=ExpressionKind.LEXICAL)
        else:
            fields["correction"] = FieldEvidence()
    return fields


def reconcile_field(field: str, primary: FieldEvidence, verification: FieldEvidence, pass_failed: bool = False) -> Observation:
    if pass_failed:
        status = RecognitionStatus.UNRESOLVED
        canonical = None
        expression = ExpressionKind.UNRESOLVED
    elif (
        (primary.value is None and primary.raw_substring is not None)
        or (verification.value is None and verification.raw_substring is not None)
    ):
        status = RecognitionStatus.UNRESOLVED
        canonical = None
        expression = ExpressionKind.UNRESOLVED
    elif primary.value is None and verification.value is None:
        status = RecognitionStatus.MISSING
        canonical = None
        expression = ExpressionKind.UNRESOLVED
    elif primary.value is None or verification.value is None or primary.value != verification.value:
        status = RecognitionStatus.DISPUTED
        canonical = None
        expression = ExpressionKind.UNRESOLVED
    else:
        status = RecognitionStatus.AGREED
        canonical = primary.value
        expression = primary.expression_kind if primary.expression_kind == verification.expression_kind else ExpressionKind.UNRESOLVED
    return Observation(
        field=field,
        primary_evidence=primary,
        verification_evidence=verification,
        canonical_value=canonical,
        expression_kind=expression,
        recognition_status=status,
    )


def extract_and_reconcile(scenario: Scenario, primary: TranscriptPass, verification: TranscriptPass) -> list[Observation]:
    primary_fields = extract_pass_observations(scenario, primary)
    verification_fields = extract_pass_observations(scenario, verification)
    pass_failed = bool(primary.error_category or verification.error_category)
    field_names = [item.split(".", 1)[1] for item in scenario.mandatory_elements]
    return [
        reconcile_field(field, primary_fields.get(field, FieldEvidence()), verification_fields.get(field, FieldEvidence()), pass_failed)
        for field in field_names
    ]


def deterministic_findings(scenario: Scenario, observations: Iterable[Observation]) -> list[Finding]:
    findings: list[Finding] = []
    expected = scenario.expected_information
    for observation in observations:
        check_id = f"{scenario.id}.{observation.field}"
        dimension = scenario.check_dimensions[check_id]
        expected_value = expected[observation.field]
        if observation.recognition_status in {RecognitionStatus.DISPUTED, RecognitionStatus.UNRESOLVED}:
            status = Verdict.UNCERTAIN
            explanation = "The two recognition passes did not provide consistent evidence for this field."
        elif observation.recognition_status == RecognitionStatus.MISSING:
            if scenario.id == "S5" and observation.field == "correction":
                status = Verdict.UNCERTAIN
                explanation = "No explicit correction marker was recognized; the source does not prescribe one universal correction sentence."
            else:
                status = Verdict.INCORRECT
                explanation = "Both transcripts omit this required element."
        elif observation.canonical_value == expected_value:
            status = Verdict.CORRECT
            explanation = "Both recognition passes agree on the required value or instruction element."
        else:
            status = Verdict.INCORRECT
            explanation = "Both recognition passes agree on a value or instruction element that does not match the scenario requirement."
        findings.append(Finding(
            check_id=check_id,
            dimension=dimension,
            status=status,
            observed_text=observation.canonical_value,
            expected_value=expected_value,
            explanation=explanation,
            origin="deterministic",
        ))
    return findings


def aggregate(findings: list[Finding], limitations: list[str] | None = None, evaluation_complete: bool = True) -> AssessmentResult:
    dimensions: dict[Dimension, Verdict] = {}
    for dimension in Dimension:
        relevant = [finding for finding in findings if finding.dimension == dimension]
        if not relevant:
            dimensions[dimension] = Verdict.NOT_ASSESSED
        elif any(item.status == Verdict.INCORRECT for item in relevant):
            dimensions[dimension] = Verdict.INCORRECT
        elif any(item.status == Verdict.UNCERTAIN for item in relevant):
            dimensions[dimension] = Verdict.UNCERTAIN
        elif all(item.status == Verdict.NOT_ASSESSED for item in relevant):
            dimensions[dimension] = Verdict.NOT_ASSESSED
        else:
            dimensions[dimension] = Verdict.CORRECT
    if Verdict.INCORRECT in dimensions.values():
        overall = Verdict.INCORRECT
    elif Verdict.UNCERTAIN in dimensions.values() or not evaluation_complete:
        overall = Verdict.UNCERTAIN
    else:
        overall = Verdict.CORRECT
    return AssessmentResult(
        findings=findings,
        dimension_verdicts=dimensions,
        overall_verdict=overall,
        limitations=limitations or [],
        evaluation_complete=evaluation_complete,
    )
