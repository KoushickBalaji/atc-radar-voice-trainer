from __future__ import annotations

import hashlib
import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from checks import aggregate, deterministic_findings, extract_and_reconcile
from content import excerpts_for, load_scenarios, scenario_by_id
from evaluation import evaluate
from models import Attempt, Finding, Verdict
from speech import AudioValidationError, transcribe_twice, validate_wav


load_dotenv()

VERDICT_ICON = {
    Verdict.CORRECT: "✅",
    Verdict.INCORRECT: "❌",
    Verdict.UNCERTAIN: "⚠️",
    Verdict.NOT_ASSESSED: "➖",
}

COMPONENT_LABELS = {
    "callsign": "Aircraft callsign",
    "action": "Instruction wording",
    "level": "Flight level",
    "direction": "Turn direction",
    "heading": "Heading",
    "code": "Transponder code",
    "holding_point": "Holding point",
    "runway": "Runway",
    "route": "Taxi route",
    "hold_short": "Hold-short instruction",
    "correction": "Readback correction",
}

DISPLAY_STATUS = {
    Verdict.CORRECT: "Right",
    Verdict.INCORRECT: "Wrong",
    Verdict.UNCERTAIN: "Unclear",
    Verdict.NOT_ASSESSED: "Not assessed",
}


def initialize_state(state: dict) -> None:
    state.setdefault("attempts", [])
    state.setdefault("processed_events", set())
    state.setdefault("recorder_nonce", 0)


def event_key(scenario_id: str, recorder_nonce: int, audio_bytes: bytes) -> str:
    digest = hashlib.sha256(audio_bytes).hexdigest()
    return f"{scenario_id}:{recorder_nonce}:{digest}"


def reset_recorder(state: dict) -> None:
    state["recorder_nonce"] = state.get("recorder_nonce", 0) + 1


def clear_session(state: dict) -> None:
    state["attempts"] = []
    state["processed_events"] = set()
    reset_recorder(state)


def process_recording(scenario_id: str, audio_bytes: bytes) -> Attempt:
    scenario = scenario_by_id(scenario_id)
    validation = validate_wav(audio_bytes)
    attempt = Attempt(
        attempt_id=str(uuid.uuid4()),
        scenario_id=scenario_id,
        audio_sha256=validation.sha256,
        audio_bytes=audio_bytes,
        audio_mime="audio/wav",
        processing_status="processing",
    )
    primary, verification = transcribe_twice(audio_bytes)
    attempt.primary_transcript = primary
    attempt.verification_transcript = verification
    observations = extract_and_reconcile(scenario, primary, verification)
    attempt.observations = observations
    deterministic = deterministic_findings(scenario, observations)
    if primary.error_category or verification.error_category:
        attempt.evaluation = aggregate(
            deterministic,
            ["At least one transcription request failed; dependent checks remain uncertain."],
            evaluation_complete=False,
        )
    else:
        attempt.evaluation = evaluate(scenario, primary, verification, observations, deterministic)
    attempt.processing_status = "complete"
    return attempt


def component_label(finding: Finding) -> str:
    field = finding.check_id.split(".", 1)[-1]
    return COMPONENT_LABELS.get(field, field.replace("_", " ").title())


def mistake_guidance(finding: Finding) -> str:
    label = component_label(finding)
    if finding.status == Verdict.UNCERTAIN:
        return f"**{label}:** This part was unclear. Try again and say it distinctly."
    if finding.observed_text and finding.expected_value:
        return f"**{label}:** You used **{finding.observed_text}**. Use **{finding.expected_value}**."
    if finding.expected_value:
        return f"**{label}:** Include **{finding.expected_value}**."
    return f"**{label}:** This component needs to be corrected."


def render_attempt(attempt: Attempt, current: bool = False) -> None:
    scenario = scenario_by_id(attempt.scenario_id)
    approved_excerpts = {item.id: item for item in excerpts_for(scenario)}
    label = "Current result" if current else f"{attempt.scenario_id} · {attempt.attempt_id[:8]}"
    with st.container(border=True):
        st.subheader(label)
        st.audio(attempt.audio_bytes, format=attempt.audio_mime)
        if attempt.processing_status == "failed":
            st.error(attempt.error_message or "We couldn't check this attempt. Please try again.")
            return
        if not attempt.evaluation:
            st.info("Your result is not ready yet.")
            return
        result = attempt.evaluation
        st.markdown(f"## {VERDICT_ICON[result.overall_verdict]} {DISPLAY_STATUS[result.overall_verdict]}")
        st.text_area(
            "Recognized transmission",
            value=(attempt.primary_transcript.raw_text if attempt.primary_transcript else "") or "",
            disabled=True,
            key=f"recognized-{attempt.attempt_id}",
        )
        st.markdown("**Components**")
        for finding in result.findings:
            st.markdown(
                f"{VERDICT_ICON[finding.status]} **{component_label(finding)}:** "
                f"{DISPLAY_STATUS[finding.status]}"
            )
            references = [
                approved_excerpts[item].paragraph_reference
                for item in finding.excerpt_ids
                if item in approved_excerpts
            ]
            if references:
                st.caption("Reference: " + "; ".join(references))

        mistakes = [
            finding for finding in result.findings
            if finding.status in {Verdict.INCORRECT, Verdict.UNCERTAIN}
        ]
        if mistakes:
            st.markdown("**What to fix**")
            for finding in mistakes:
                st.markdown(f"- {mistake_guidance(finding)}")
        else:
            st.success("No corrections needed.")

        st.markdown("**Suggested correction**")
        st.info(scenario.acceptable_examples[0])

        with st.expander("Source excerpts"):
            for excerpt in approved_excerpts.values():
                pages = ", ".join(excerpt.printed_pages)
                st.markdown(f"**{excerpt.paragraph_reference}** — page {pages}")
                st.write(excerpt.exact_text)


def main() -> None:
    st.set_page_config(page_title="ATC Radiotelephony Trainer", page_icon="🎙️", layout="centered")
    initialize_state(st.session_state)
    st.title("ATC Radiotelephony Trainer")
    st.warning("**Training Prototype** — Not for live ATC use or certified competency assessment.")
    st.caption("Audio and recognized text are sent to the configured cloud API. Session data is kept in memory only.")

    scenarios = load_scenarios()
    scenario_ids = [item.id for item in scenarios]
    selected_id = st.selectbox(
        "Scenario",
        scenario_ids,
        format_func=lambda item: f"{item} — {scenario_by_id(item).title}",
    )
    scenario = scenario_by_id(selected_id)
    st.markdown(f"**Situation**  \n{scenario.situation}")
    st.markdown(f"**Required action**  \n{scenario.required_action}")
    if scenario.previous_clearance:
        st.markdown(f"**Previously issued clearance**  \n{scenario.previous_clearance}")
    if scenario.pilot_readback:
        st.markdown(f"**Pilot readback**  \n{scenario.pilot_readback}")

    audio = st.audio_input(
        "Record your controller transmission",
        sample_rate=16000,
        key=f"recorder-{st.session_state['recorder_nonce']}",
    )
    if audio is not None:
        audio_bytes = audio.getvalue()
        key = event_key(selected_id, st.session_state["recorder_nonce"], audio_bytes)
        if key not in st.session_state["processed_events"]:
            st.session_state["processed_events"].add(key)
            with st.status("Checking your response…", expanded=True) as status:
                try:
                    attempt = process_recording(selected_id, audio_bytes)
                    st.session_state["attempts"].append(attempt)
                    status.update(label="Feedback ready", state="complete")
                except AudioValidationError as exc:
                    failed = Attempt(
                        attempt_id=str(uuid.uuid4()),
                        scenario_id=selected_id,
                        audio_sha256=hashlib.sha256(audio_bytes).hexdigest(),
                        audio_bytes=audio_bytes,
                        audio_mime="audio/wav",
                        processing_status="failed",
                        error_message=str(exc),
                    )
                    st.session_state["attempts"].append(failed)
                    status.update(label="Recording could not be processed", state="error")
                except Exception:
                    failed = Attempt(
                        attempt_id=str(uuid.uuid4()),
                        scenario_id=selected_id,
                        audio_sha256=hashlib.sha256(audio_bytes).hexdigest(),
                        audio_bytes=audio_bytes,
                        audio_mime="audio/wav",
                        processing_status="failed",
                        error_message="We couldn't check this attempt. Please check again or record a new attempt.",
                    )
                    st.session_state["attempts"].append(failed)
                    status.update(label="Processing failed", state="error")

    current_attempts = [item for item in st.session_state["attempts"] if item.scenario_id == selected_id]
    if current_attempts:
        current_attempt = current_attempts[-1]
        render_attempt(current_attempt, current=True)
        if current_attempt.evaluation and not current_attempt.evaluation.evaluation_complete:
            if st.button("Check again"):
                with st.status("Checking your response again…") as status:
                    retried = process_recording(selected_id, current_attempt.audio_bytes)
                    st.session_state["attempts"].append(retried)
                    status.update(label="Retry complete", state="complete")
                st.rerun()
        if st.button("Try again", type="primary"):
            reset_recorder(st.session_state)
            st.rerun()

    previous = st.session_state["attempts"][:-1] if st.session_state["attempts"] else []
    if previous:
        with st.expander(f"Previous session attempts ({len(previous)})"):
            for attempt in reversed(previous):
                render_attempt(attempt)
    if st.session_state["attempts"] and st.button("Clear session data"):
        clear_session(st.session_state)
        st.rerun()


if __name__ == "__main__":
    main()
