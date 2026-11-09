from __future__ import annotations

from pathlib import Path

from app import clear_session, component_label, event_key, initialize_state, mistake_guidance, reset_recorder
from models import Dimension, Finding, Verdict


def test_duplicate_completed_audio_event_is_stable_within_recorder_attempt() -> None:
    state = {}
    initialize_state(state)
    first = event_key("S1", state["recorder_nonce"], b"audio")
    second = event_key("S1", state["recorder_nonce"], b"audio")
    assert first == second
    reset_recorder(state)
    assert event_key("S1", state["recorder_nonce"], b"audio") != first


def test_scenario_switch_prevents_stale_event_attachment() -> None:
    assert event_key("S1", 0, b"audio") != event_key("S2", 0, b"audio")


def test_clear_session_releases_retained_attempts() -> None:
    state = {"attempts": [object()], "processed_events": {"x"}, "recorder_nonce": 2}
    clear_session(state)
    assert state["attempts"] == []
    assert state["processed_events"] == set()
    assert state["recorder_nonce"] == 3


def test_app_has_no_typed_trainee_input_or_review_gate() -> None:
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "st.audio_input" in source
    assert "st.text_input" not in source
    assert "st.chat_input" not in source
    assert "st.checkbox" not in source
    assert "Submit for grading" not in source


def test_results_ui_hides_pipeline_and_evidence_details() -> None:
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    for hidden_text in (
        "Recognition details",
        "Primary transcript:",
        "Verification transcript:",
        "Transcribing and grading",
        "Retry processing",
    ):
        assert hidden_text not in source
    assert "st.audio(" in source
    assert '"Recognized transmission"' in source
    assert 'with st.expander("Source excerpts")' in source
    assert 'st.caption("Reference: "' in source
    assert "**Components**" in source
    assert "**What to fix**" in source
    assert "**Suggested correction**" in source


def test_component_labels_and_mistake_guidance_are_plain_language() -> None:
    wrong = Finding(
        check_id="S2.heading",
        dimension=Dimension.INFORMATION,
        status=Verdict.INCORRECT,
        observed_text="090",
        expected_value="080",
        explanation="internal detail",
    )
    unclear = Finding(
        check_id="S1.callsign",
        dimension=Dimension.INFORMATION,
        status=Verdict.UNCERTAIN,
        expected_value="INDAIR 809",
        explanation="internal detail",
    )
    assert component_label(wrong) == "Heading"
    assert "You used **090**. Use **080**." in mistake_guidance(wrong)
    assert component_label(unclear) == "Aircraft callsign"
    assert "This part was unclear" in mistake_guidance(unclear)
    assert "model" not in mistake_guidance(unclear).lower()
    assert "transcript" not in mistake_guidance(unclear).lower()
