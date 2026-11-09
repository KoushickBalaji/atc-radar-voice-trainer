# ATC Radiotelephony Trainer - Local MVP

Voice-only local Streamlit prototype for formative ATC radiotelephony practice. It uses five fixed scenarios and a curated set of Chapter 12 excerpts from the supplied Airports Authority of India manual.

> **Training and demonstration only. Not for live ATC use or certified competency assessment.** Audio and recognized text are sent to the configured OpenAI API. Session attempts are retained only in Streamlit memory unless the user clears them or the session ends.

## Implemented flow

1. Select S1-S5.
2. Read the synthetic situation and required action.
3. Record a controller transmission with Streamlit's native microphone widget.
4. Stop recording. Processing starts automatically; there is no transcript review or submission gate.
5. The original WAV is validated and sent in two separate `gpt-transcribe` requests with isolated generic prompts.
6. The application preserves both raw transcripts, extracts per-pass evidence, reconciles it conservatively, freezes deterministic findings, and requests source-grounded structured assessment from `gpt-6.1-sol` at medium reasoning effort.
7. The trainee-facing result shows audio playback, one read-only recognized transcript, whether each component was right, wrong, or unclear, mistakes to fix, one curated suggested correction, and the relevant manual citations/source excerpts. Dual-pass and model-call details remain internal.

There is no typed trainee input, transcript editing, confirmation checkbox, database, RAG, embeddings, authentication, deployment layer, or runtime agent framework.

## Source boundary

Runtime grading can use only `data/manual_excerpts.json`, curated from rendered Chapter 12 pages of `Manual of Air Traffic Services, Part-1 Edition 7.pdf` (AAI, Edition 7.0, 9 May 2025). The recorded source SHA-256 is:

```text
1DE3FE5E2D2087C4C170D281D1913FE19DA8F5205A29EFAF5C6BCEE75C7868F8
```

The full PDF is never uploaded or searched at runtime. Each scenario supplies only its approved excerpt IDs. Citation validation checks that the model used those IDs and that normative supporting quotations occur in the curated text.

The manual and product plan leave one explicit interpretation question unresolved: 12.8.7-12.8.8 describe correction of an error in an operator's own transmission, while S5 corrects a pilot readback. The MVP uses 12.9.5 for the duty to correct the discrepancy and does not invent a universally mandatory correction sentence.

## Requirements

- Windows with Python 3.12
- A browser with microphone permission
- Network access and an OpenAI API key with access to the configured models
- Human-recorded validation fixtures for the live acceptance gate (not included)

Versions installed and used for the offline verification in this workspace:

- Python 3.12.4
- Streamlit 1.51.0
- OpenAI Python SDK 2.7.1
- Pydantic 2.12.4
- python-dotenv 1.2.1
- pytest 8.4.2

Current official OpenAI documentation and the installed SDK were checked before integration. The configured IDs remain `gpt-transcribe` and `gpt-6.1-sol`; the application does not silently substitute another model.

## Setup

In PowerShell:

```powershell
Set-Location D:\ATC
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. Keep the two model IDs unchanged unless a reviewed product decision explicitly changes them:

```dotenv
OPENAI_API_KEY=
OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe
OPENAI_EVALUATION_MODEL=gpt-6.1-sol
```

## Run

```powershell
Set-Location D:\ATC
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address localhost
```

Open the local URL printed by Streamlit, allow microphone access, choose a scenario, record, and stop. Stopping is the grading trigger.

## Test

Offline and mocked tests make no paid API calls:

```powershell
Set-Location D:\ATC
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
```

Live tests are deliberately opt-in:

```powershell
Set-Location D:\ATC
$env:RUN_LIVE_EVALS = "1"
.\.venv\Scripts\python.exe -m pytest -q -m live
```

Pytest loads `OPENAI_API_KEY` and the configured model IDs from `.env`. This command runs a paid live structured-evaluation smoke test. The recorded-audio test skips until `ATC_APPROVED_AUDIO_FIXTURES` points to a reviewed fixture directory; recordings are optional for the API smoke check.

PowerShell environment variables apply only to the current PowerShell process. Set `RUN_LIVE_EVALS` and invoke pytest in the same window. To verify it without exposing the key:

```powershell
Write-Output $env:RUN_LIVE_EVALS
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; import os; load_dotenv(); print(bool(os.getenv('OPENAI_API_KEY')))"
```

Useful non-paid checks:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py models.py content.py speech.py checks.py evaluation.py tests
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address localhost
```

### Reproduce an end-to-end WAV run

Any WAV can be sent through the same post-recording function used by the Streamlit app. This makes two paid transcription requests followed by the paid structured-evaluation request:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_e2e_wav D:\path\to\recording.wav --scenario S1
```

The command prints audio metadata, both untouched transcripts, reconciled observations, deterministic/model findings, dimension verdicts, limitations, and total pipeline latency. Synthetic speech is useful for integration testing but is not a substitute for the deferred human-audio validation gate.

## Design invariants

- The same original audio bytes go to both transcription requests through separate file objects.
- STT prompts receive no scenario numbers, target level/heading/code/runway, prior clearance, pilot readback, or other transcript. Both calls receive the same fixed domain vocabulary (including the shared telephony designator `INDAIR`) to reduce spelling errors; no complete expected transmission is supplied.
- Raw transcript substrings, expression kinds, and canonical values are separate fields.
- Identifiers and number-bearing aviation values remain strings; incomplete codes are not padded toward expected answers.
- Both-pass agreement freezes a value; disagreement, a failed pass, or ambiguous extraction stays Uncertain.
- Deterministic mismatches and recognition uncertainty cannot be overridden by the evaluator.
- Numeric agreement does not prove the spoken wording. Grouped wording is not graded acoustically.
- Evaluation failure preserves valid deterministic findings and marks remaining checks incomplete/uncertain.
- API failures are never labeled as trainee errors, and no text fallback is offered.

## Scenario references

- S1 Climb clearance: 12.16.1.1(a), 12.16.1.2(a)(i), maintain note under 12.16.2.3, plus shared number/callsign/flight-level passages.
- S2 Heading 080: 12.17 applicability note, 12.17.1.3(e), reason note after 12.17.1.5, and 12.5.1.
- S3 Squawk 3425: 12.17.3.3-12.17.3.6 and the 12.9.4 example.
- S4 Detailed taxi: 12.16.4.7(c)/(e)/(h), 12.16.4.8(d) and note, plus shared alphabet/number/callsign passages.
- S5 Incorrect readback: 12.9.4-12.9.5, selected 12.6.1 terms, and the S1 climb/level passages.

## Known limitations and unverified gates

- Number representations are preserved after recognition, but recognition itself is probabilistic.
- Two matching transcriptions can share the same error; agreement is not a confidence score.
- Normalized digits do not establish how a number was spoken.
- No pronunciation, accent, pace, emphasis, loudness, or microphone-technique scoring is performed.
- The deterministic parsers cover these five bounded scenarios, not arbitrary radiotelephony.
- Valid structured output and valid citations do not prove correct interpretation of the source.
- Session data is temporary; inference needs network connectivity and account/model access.
- The live `gpt-6.1-sol` structured-evaluation path has been verified with the local credential. Real STT accuracy, browser microphone behavior, end-to-end voice latency, and the two-run recorded-audio gate remain unverified because recordings and labels are deferred.

## SME questions

1. How should 12.5.1's general digit-by-digit rule be reconciled with the same table's grouped-number examples for FL200 and squawk 1000?
2. Which readback-correction constructions should be accepted for S5, and do 12.8.7-12.8.8 apply to correcting another station's readback?
3. Is the fictional S4 situation and its explicit runway-27 hold-short boundary suitable for demonstration?
4. Which additional source-supported variants should be curated without weakening the scenario requirements?
