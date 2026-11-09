from __future__ import annotations

import io
import math
import struct
import wave
from types import SimpleNamespace

import pytest

from speech import AudioValidationError, TRANSCRIPTION_KEYWORDS, transcribe_twice, validate_wav


def wav_bytes(seconds: float = 0.25, sample_rate: int = 16000, silent: bool = False) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        samples = []
        for index in range(round(seconds * sample_rate)):
            value = 0 if silent else round(1000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            samples.append(struct.pack("<h", value))
        wav.writeframes(b"".join(samples))
    return buffer.getvalue()


class FakeTranscriptions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        uploaded = kwargs["file"].read()
        self.calls.append({**kwargs, "uploaded": uploaded})
        text = "INDAIR EIGHT ZERO NINE CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO"
        return SimpleNamespace(text=text, _request_id="req_mock")


class FakeClient:
    def __init__(self) -> None:
        self.transcriptions = FakeTranscriptions()
        self.audio = SimpleNamespace(transcriptions=self.transcriptions)


def test_wav_validation_preserves_hash_and_metadata() -> None:
    audio = wav_bytes()
    result = validate_wav(audio)
    assert result.sample_rate == 16000
    assert result.duration_seconds == pytest.approx(0.25)
    assert len(result.sha256) == 64


def test_silence_and_invalid_audio_are_rejected() -> None:
    with pytest.raises(AudioValidationError):
        validate_wav(wav_bytes(silent=True))
    with pytest.raises(AudioValidationError):
        validate_wav(b"not a wav")


def test_two_transcription_calls_receive_identical_original_bytes_and_isolated_prompts() -> None:
    audio = wav_bytes()
    client = FakeClient()
    primary, verifier = transcribe_twice(audio, client=client, model="gpt-transcribe")
    assert primary.raw_text == verifier.raw_text
    assert len(client.transcriptions.calls) == 2
    assert all(call["uploaded"] == audio for call in client.transcriptions.calls)
    prompts = {call["prompt"] for call in client.transcriptions.calls}
    assert len(prompts) == 2
    assert all("3425" not in prompt and "180" not in prompt and "INDAIR" not in prompt for prompt in prompts)
    assert all(call["model"] == "gpt-transcribe" for call in client.transcriptions.calls)
    assert "INDAIR" in TRANSCRIPTION_KEYWORDS
    assert all(call["extra_body"]["keywords"] == TRANSCRIPTION_KEYWORDS for call in client.transcriptions.calls)
    assert all(
        not any(character.isdigit() for keyword in TRANSCRIPTION_KEYWORDS for character in keyword)
        for call in client.transcriptions.calls
    )
