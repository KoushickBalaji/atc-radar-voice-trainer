from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Verdict(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNCERTAIN = "uncertain"
    NOT_ASSESSED = "not_assessed"


class Dimension(str, Enum):
    PHRASEOLOGY = "phraseology"
    INFORMATION = "information"
    PROCEDURE = "procedure"


class RecognitionStatus(str, Enum):
    AGREED = "agreed"
    DISPUTED = "disputed"
    MISSING = "missing"
    UNRESOLVED = "unresolved"


class ExpressionKind(str, Enum):
    DIGIT_WORDS = "digit_words"
    GROUPED_WORDS = "grouped_number_words"
    NUMERAL = "numeral_text"
    LEXICAL = "lexical"
    UNRESOLVED = "unresolved"


class ManualExcerpt(StrictModel):
    id: str
    paragraph_reference: str
    printed_pages: list[str]
    pdf_pages: list[int]
    circumstance_text: str = ""
    exact_text: str
    notes: list[str] = Field(default_factory=list)


class ManualCollection(StrictModel):
    document_title: str
    edition: str
    document_date: str
    sha256: str
    curation_notes: list[str]
    excerpts: list[ManualExcerpt]


class Scenario(StrictModel):
    id: str
    title: str
    situation: str
    required_action: str
    previous_clearance: str | None = None
    pilot_readback: str | None = None
    expected_information: dict[str, str]
    mandatory_elements: list[str]
    acceptable_examples: list[str]
    incorrect_examples: list[dict[str, str]]
    permitted_variation_notes: list[str]
    assessment_scope: str
    excerpt_ids: list[str]
    check_dimensions: dict[str, Dimension]


class ScenarioCollection(StrictModel):
    scenarios: list[Scenario]


class TranscriptPass(StrictModel):
    name: str
    raw_text: str | None = None
    error_category: str | None = None
    request_id: str | None = None
    elapsed_ms: int | None = None


class FieldEvidence(StrictModel):
    raw_substring: str | None = None
    value: str | None = None
    expression_kind: ExpressionKind = ExpressionKind.UNRESOLVED


class Observation(StrictModel):
    field: str
    primary_evidence: FieldEvidence
    verification_evidence: FieldEvidence
    canonical_value: str | None = None
    expression_kind: ExpressionKind = ExpressionKind.UNRESOLVED
    recognition_status: RecognitionStatus


class Finding(StrictModel):
    check_id: str
    dimension: Dimension
    status: Verdict
    observed_text: str | None = None
    expected_value: str | None = None
    explanation: str
    excerpt_ids: list[str] = Field(default_factory=list)
    supporting_quote: str | None = None
    origin: str = "model"


class ModelFinding(StrictModel):
    check_id: str
    dimension: Dimension
    status: Verdict
    observed_text: str | None = None
    expected_value: str | None = None
    explanation: str
    excerpt_ids: list[str] = Field(default_factory=list)
    supporting_quote: str | None = None


class ModelEvaluation(StrictModel):
    findings: list[ModelFinding]
    limitations: list[str] = Field(default_factory=list)


class AssessmentResult(StrictModel):
    findings: list[Finding]
    dimension_verdicts: dict[Dimension, Verdict]
    overall_verdict: Verdict
    limitations: list[str] = Field(default_factory=list)
    evaluation_complete: bool = True


class Attempt(StrictModel):
    attempt_id: str
    scenario_id: str
    audio_sha256: str
    audio_bytes: bytes
    audio_mime: str
    primary_transcript: TranscriptPass | None = None
    verification_transcript: TranscriptPass | None = None
    observations: list[Observation] = Field(default_factory=list)
    processing_status: str = "recording"
    evaluation: AssessmentResult | None = None
    error_message: str | None = None


class AudioValidation(StrictModel):
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int
    sha256: str


def public_model_dump(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(mode="json", exclude={"audio_bytes"})
