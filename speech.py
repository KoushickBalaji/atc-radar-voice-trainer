from __future__ import annotations

import hashlib
import io
import logging
import os
import struct
import time
import wave
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

from models import AudioValidation, TranscriptPass


LOGGER = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_DURATION_SECONDS = 60.0

PRIMARY_PROMPT = (
    "Transcribe the aviation radio transmission faithfully. Preserve spoken number words, "
    "repetitions, corrections, and nonstandard wording. Do not improve or complete the instruction."
)
VERIFICATION_PROMPT = (
    "Transcribe exactly what is audible. Preserve digit order and distinguish individually spoken "
    "digits from grouped number words. Do not infer missing callsign characters or numbers. "
    "Do not repair incorrect phraseology."
)

# Fixed domain vocabulary shared by every scenario. It deliberately contains no
# scenario numbers, targets, routes, or complete expected transmission.
TRANSCRIPTION_KEYWORDS = [
    "INDAIR",
    "flight level",
    "heading",
    "squawk",
    "runway",
    "holding point",
    "hold short",
    "ALFA",
]


class AudioValidationError(ValueError):
    pass


def validate_wav(audio_bytes: bytes) -> AudioValidation:
    if not audio_bytes:
        raise AudioValidationError("No recording data was received.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioValidationError("Recording exceeds the 10 MB limit.")
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise AudioValidationError("The recording is not a readable WAV file.") from exc
    if sample_rate <= 0 or frame_count <= 0 or channels <= 0 or sample_width not in {1, 2, 3, 4}:
        raise AudioValidationError("The WAV recording has invalid audio parameters.")
    duration = frame_count / sample_rate
    if duration > MAX_DURATION_SECONDS:
        raise AudioValidationError("Recording exceeds the 60 second limit.")
    if duration < 0.15:
        raise AudioValidationError("Recording is too short to contain a transmission.")
    if not _has_signal(frames, sample_width):
        raise AudioValidationError("No usable speech signal was detected in the recording.")
    return AudioValidation(
        duration_seconds=duration,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        sha256=hashlib.sha256(audio_bytes).hexdigest(),
    )


def _has_signal(frames: bytes, sample_width: int) -> bool:
    if sample_width == 1:
        return any(abs(value - 128) > 2 for value in frames)
    if sample_width == 2:
        count = len(frames) // 2
        return count > 0 and max(abs(value) for value in struct.unpack(f"<{count}h", frames[: count * 2])) > 8
    # For 24/32-bit input, a non-zero byte test is intentionally conservative.
    return any(value not in {0, 128} for value in frames)


def _error_category(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    for category in ("authentication", "ratelimit", "timeout", "connection", "permission"):
        if category in name:
            return category
    return "api_error"


def _transcribe_one(client: OpenAI, audio_bytes: bytes, name: str, prompt: str, model: str) -> TranscriptPass:
    started = time.perf_counter()
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"attempt-{name}.wav"
        response = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            prompt=prompt,
            extra_body={
                "languages": ["en"],
                "keywords": TRANSCRIPTION_KEYWORDS,
            },
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return TranscriptPass(
            name=name,
            raw_text=response.text,
            request_id=getattr(response, "_request_id", None),
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # SDK exception subclasses vary by version.
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        category = _error_category(exc)
        LOGGER.warning("transcription_failed pass=%s model=%s category=%s elapsed_ms=%s", name, model, category, elapsed_ms)
        return TranscriptPass(name=name, error_category=category, elapsed_ms=elapsed_ms)


def transcribe_twice(audio_bytes: bytes, client: OpenAI | None = None, model: str | None = None) -> tuple[TranscriptPass, TranscriptPass]:
    selected_model = model or os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-transcribe")
    try:
        api_client = client or OpenAI(timeout=60.0, max_retries=1)
    except Exception as exc:
        category = "configuration" if not os.getenv("OPENAI_API_KEY") else _error_category(exc)
        LOGGER.warning("transcription_client_failed model=%s category=%s", selected_model, category)
        return (
            TranscriptPass(name="primary", error_category=category),
            TranscriptPass(name="verification", error_category=category),
        )
    with ThreadPoolExecutor(max_workers=2) as executor:
        primary_future = executor.submit(_transcribe_one, api_client, audio_bytes, "primary", PRIMARY_PROMPT, selected_model)
        verifier_future = executor.submit(_transcribe_one, api_client, audio_bytes, "verification", VERIFICATION_PROMPT, selected_model)
        return primary_future.result(), verifier_future.result()
