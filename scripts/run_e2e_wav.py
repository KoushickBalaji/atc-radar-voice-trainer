from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app import process_recording
from speech import validate_wav


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one WAV through the complete ATC grading pipeline.")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--scenario", default="S1")
    args = parser.parse_args()

    audio = args.wav.read_bytes()
    validation = validate_wav(audio)
    started = time.perf_counter()
    attempt = process_recording(args.scenario, audio)
    elapsed = time.perf_counter() - started

    result = {
        "input": {
            "scenario_id": args.scenario,
            "synthetic_audio_path": str(args.wav.resolve()),
            "bytes": len(audio),
            "duration_seconds": round(validation.duration_seconds, 3),
            "sample_rate": validation.sample_rate,
            "sha256": validation.sha256,
        },
        "pipeline": {
            "elapsed_seconds": round(elapsed, 3),
            "processing_status": attempt.processing_status,
            "primary_transcript": attempt.primary_transcript.model_dump(mode="json") if attempt.primary_transcript else None,
            "verification_transcript": attempt.verification_transcript.model_dump(mode="json") if attempt.verification_transcript else None,
            "observations": [item.model_dump(mode="json") for item in attempt.observations],
            "evaluation": attempt.evaluation.model_dump(mode="json") if attempt.evaluation else None,
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
