# ATC Radiotelephony Trainer — Voice-Only Local MVP

Status: Ready for implementation; application not yet implemented.

Plan date: 2026-11-04.

This is the authoritative implementation reference. Read [AGENT_COORDINATION.md](AGENT_COORDINATION.md) for task ownership, dependencies, validation evidence, and session handoffs.

## 1. Objective and fixed product requirements

Build a local training prototype for trainee Air Traffic Controllers to practice spoken radiotelephony and receive formative feedback grounded in Chapter 12 of the supplied Airports Authority of India manual. Demonstrate technical feasibility to an ATC professional.

Prioritize end-to-end functionality, accurate information handling, traceable feedback, and simplicity. This is not a production or validated safety-critical assessment system.

### User journey

1. Select one of five predefined scenarios.
2. Read the operational situation.
3. Record a controller transmission.
4. Stop recording.
5. Automatically transcribe, check, evaluate, and display the result.
6. Select **Try again** to record another attempt.

**Voice is the only trainee input mode.** Do not implement typed responses, editable transcripts, confirmation checkboxes, a transcript-review gate, or a separate transcription/grading submission button. Stopping a recording initiates processing automatically.

Show the recognized transmission and audio playback as part of the result. Inspection is optional and never required for grading. If recognition is ambiguous, return **Uncertain** immediately for the affected checks. Do not ask the trainee to resolve the ambiguity. Retry is optional.

### Exclusions

Do not introduce Supabase, an application database, vector databases, embeddings, RAG, LangChain, LangGraph, runtime multi-agent orchestration, Docker, Kubernetes, authentication, cloud deployment, a complex frontend, real-time pilot simulation, persistent progress reporting, or a generic configurable rules engine.

Implementation agents and work packages are development coordination only; they are not part of the application architecture.

## 2. Technical decisions

| Component | Decision |
| --- | --- |
| Runtime | Python 3.12 |
| Local UI | Streamlit |
| Microphone | Native `st.audio_input(sample_rate=16000)` |
| Speech-to-text (STT) | OpenAI `gpt-transcribe` |
| Recognition cross-check | Two separate transcription requests over the same original recording |
| Evaluation | OpenAI `gpt-6.1-sol`, medium reasoning |
| Structured output | Pydantic through `client.responses.parse()` |
| Content | Local JSON scenario and excerpt collections |
| State | Streamlit session memory |
| Tests | `pytest`, mocked services, separately enabled live audio/evaluation tests |

`gpt-transcribe` is an STT model, not an alternative category to STT. It is the selected OpenAI baseline, not a claim of proven superiority for aviation speech. Validate critical-field recognition on representative recordings before declaring the voice flow verified.

The two transcription calls are a bounded consistency check using one provider. They are not statistically independent evidence: the same model may repeat the same error. Do not describe agreement as proof of accuracy or a calibrated confidence score.

Official references checked during planning:

- [OpenAI file transcription](https://developers.openai.com/api/docs/guides/speech-to-text)
- [OpenAI transcription testing guidance](https://developers.openai.com/api/docs/guides/transcription)
- [OpenAI transcription API reference](https://developers.openai.com/api/reference/python/resources/audio/subresources/transcriptions/methods/create)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [Streamlit audio input](https://docs.streamlit.io/develop/api-reference/widgets/st.audio_input)

Before implementation, confirm the configured models and SDK calls remain available. Do not silently substitute a model. Document any required change and rerun the relevant fixtures. Model/API availability and account access were not live-tested during planning.

### Minimal project organization

Use a flat, small project with responsibilities divided between:

- `app.py`: Streamlit UI, automatic processing trigger, and session state.
- `models.py`: typed content, recognition, and evaluation contracts.
- `content.py`: loading and validating local scenario/excerpt data.
- `speech.py`: audio validation and the two STT requests.
- `checks.py`: field extraction, reconciliation, deterministic comparison, and verdict aggregation.
- `evaluation.py`: source-grounded structured LLM request and response validation.
- `data/scenarios.json` and `data/manual_excerpts.json`: curated content.
- `tests/`: unit, mocked integration, content, and opt-in live tests.
- `requirements.txt`, `.env.example`, `.gitignore`, and `README.md`.

Use `streamlit`, `openai`, `pydantic`, `python-dotenv`, and `pytest`. Pin versions successfully tested during implementation. PDF extraction is an authoring activity, not a runtime dependency; put extraction tooling in development requirements only if retaining a helper.

Do not add a backend HTTP server, repository layer, dependency-injection framework, or provider abstraction.

## 3. Authoritative manual and curation

Source: [Manual of Air Traffic Services, Part-1 Edition 7.pdf](Manual%20of%20Air%20Traffic%20Services%2C%20Part-1%20Edition%207.pdf), AAI, Edition 7.0, dated 9 May 2025.

Use Chapter 12 only as the phraseology authority for this prototype. Printed pages **12-1–12-56** correspond exactly to **one-based PDF pages 321–376**. The complete chapter was read during planning and the key selected tables, notation, and supporting paragraphs were visually inspected. Exact runtime excerpt data has not yet been authored.

### Curation requirements

Extract exact passages into local data before implementing the grader. Preserve:

- Paragraph and table identifiers.
- Relevant circumstance-column text alongside each phraseology.
- Parentheses, brackets, alternatives, and pilot-transmission markers.
- Notes affecting applicability.
- Printed and one-based PDF page numbers.

Compare every grading excerpt with the rendered source page. Correct extraction artifacts such as broken wrapping only after visual verification. Do not silently correct questionable wording in the source. Record genuine ambiguity separately.

Store document title, edition, date, and SHA-256 in collection metadata. Compute the hash from the supplied file during curation. Runtime evaluation loads the curated data and never uploads or searches the whole PDF.

### Shared reference inventory

| Passage | Printed pages / PDF pages | Purpose |
| --- | --- | --- |
| 12.2.1–12.2.3 | 12-1–12-2 / 321–322 | Informational transmitting guidance; no acoustic scoring |
| 12.4.1, Table 12-1 | 12-2 / 322 | Number pronunciation reference |
| 12.4.2, Table 12-2 | 12-3 / 323 | Spelling alphabet, particularly ALFA |
| 12.5.1–12.5.2, Tables 12-3–12-4 | 12-4–12-5 / 324–325 | Number transmission, examples, and exceptions |
| 12.6.1, selected Table 12-5 entries | 12-5–12-7 / 325–327 | NEGATIVE, CORRECT, CORRECTION, I SAY AGAIN, READ BACK, ROGER |
| 12.7.2.1–12.7.2.2 | 12-8–12-9 / 328–329 | Callsign forms and abbreviation restrictions |
| 12.8.7–12.8.8 | 12-10 / 330 | Correction wording; retain applicability uncertainty |
| 12.9.4–12.9.5 | 12-10 / 330 | Readback obligations and correcting discrepancies |
| 12.13.3 | 12-12 / 332 | Standard phraseology where prescribed |
| 12.14.1 and 12.14.4 | 12-13 / 333 | Callsigns, pilot markers, flight-level terminology |
| Unnumbered note after 12.15.3 | 12-14 / 334 | Meaning of parentheses and square brackets |

Supply only applicable excerpts to each evaluation. The inventory is not an instruction to send every passage for every scenario.

### Interpretation safeguards

- Section 12.14.1 requires appropriate callsigns even when the tables omit them.
- Asterisks identify pilot transmissions; do not teach them as controller instructions.
- The note after 12.15.3 permits parentheses to represent inserted information or alternative optional phrases. Do not mechanically treat every parenthetical item as mandatory.
- Square-bracketed information can become necessary in a specific situation. Do not treat it as universally ignorable.
- Section 12.5.1's digit-by-digit wording appears alongside explicit examples such as FL200 → “flight level two hundred” and code 1000 → “squawk one thousand.” Preserve these examples; do not extrapolate an unsupported blanket rule.
- Section 12.9.5 requires discrepancy correction but does not supply a universal correction sentence.
- Do not apply the conditional-clearance reply in 12.16.4.10(k) universally to ordinary readback correction.
- Do not infer acoustic pronunciation from spelling or normalized digits. Speech rate, accent, microphone technique, emphasis, and acoustic pronunciation are outside assessment scope.

## 4. Five scenario specifications

### Shared assumptions

Use the manual's example callsign **INDAIR 809**, spoken as **INDAIR EIGHT ZERO NINE**. It is a type-(c) callsign; do not accept abbreviation to “809.”

Communications are established and the aircraft is unambiguously identified. Operational clearance decisions have already been made. Trainees practice communication, not separation, terrain clearance, runway availability, or airspace suitability. All situations are synthetic.

Examples use ordinary written number words. Recognize relevant phonetic spellings, such as NINER, without inferring a pronunciation fault from ordinary transcription spelling.

### S1 — Climb clearance

**Situation:** INDAIR 809 is maintaining FL160. Instruct commencement of climb to FL180. No SID restriction, conditional timing, or climb-rate instruction applies.

**Mandatory:** Full callsign, climb action, flight-level designation, target 180.

**Acceptable:**

> INDAIR EIGHT ZERO NINE, CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO.

**References:** 12.16.1.1(a) and 12.16.1.2(a)(i), printed 12-15 / PDF 335; note under 12.16.2.3, printed 12-27 / PDF 347; shared callsign, number, and flight-level passages.

**Incorrect fixtures:**

1. `INDAIR EIGHT ZERO NINE, CLIMB TO FLIGHT LEVEL ONE NINE ZERO.` Wrong target, 190 rather than 180.
2. `INDAIR EIGHT ZERO NINE, MAINTAIN FLIGHT LEVEL ONE EIGHT ZERO.` MAINTAIN does not substitute for CLIMB when instructing a level change; cite the explicit note.

Do not require REPORT REACHING. WHEN READY changes the requested timing and is not an interchangeable variant here.

### S2 — Left turn to heading 080

**Situation:** Under ATS surveillance control, INDAIR 809 is flying heading 120. Instruct a left turn to heading 080 for spacing.

**Mandatory:** Full callsign, turn instruction, left direction, heading 080.

**Acceptable:**

> INDAIR EIGHT ZERO NINE, TURN LEFT HEADING ZERO EIGHT ZERO.

> INDAIR EIGHT ZERO NINE, TURN LEFT HEADING ZERO EIGHT ZERO FOR SPACING.

**References:** 12.17 introductory applicability note and 12.17.1.3(e), printed 12-47 / PDF 367; reason-for-vectoring note after 12.17.1.5, printed 12-48 / PDF 368; 12.5.1, including its heading-080 example.

**Incorrect fixtures:**

1. `INDAIR EIGHT ZERO NINE, TURN RIGHT HEADING ZERO EIGHT ZERO.` Wrong direction.
2. `INDAIR EIGHT ZERO NINE, TURN LEFT HEADING EIGHTY.` Numeric value is 080; number wording is incorrect only when the recognition pipeline has retained sufficient wording evidence under Section 5.

A transcript containing only 080 does not establish how its digits were spoken. Do not grade number wording from reconstructed canonical digits.

### S3 — Departure squawk assignment

**Situation:** Before departure, assign INDAIR 809 new transponder code 3425. This is not a reselection, confirmation, or IDENT request.

**Mandatory:** Full callsign, setting instruction, complete code 3425.

**Acceptable:**

> INDAIR EIGHT ZERO NINE, SQUAWK THREE FOUR TWO FIVE.

> INDAIR EIGHT ZERO NINE, FOR DEPARTURE SQUAWK THREE FOUR TWO FIVE.

**References:** 12.17.3.3(a)–(b), printed 12-54 / PDF 374; adjacent 12.17.3.4 and 12.17.3.6 distinguish resetting/confirmation from assignment; 12.9.4's squawk-3425 example and 12.5.1.

**Incorrect fixtures:**

1. `INDAIR EIGHT ZERO NINE, SQUAWK THREE FOUR TWO SIX.` Wrong code.
2. `INDAIR EIGHT ZERO NINE, CONFIRM SQUAWK THREE FOUR TWO FIVE.` A confirmation request does not issue the required setting instruction.

Do not require FOR DEPARTURE or IDENT.

### S4 — Detailed taxi instruction

**Situation:** At a fictional aerodrome, INDAIR 809 is at Stand 3. ATIS is available. Instruct taxi via taxiway A to holding point 1 for runway 27, explicitly holding short of runway 27. No intervening runway crossing exists.

**Mandatory:** Full callsign, taxi action, holding point 1, runway 27, route A, explicit hold-short restriction for runway 27.

**Acceptable:**

> INDAIR EIGHT ZERO NINE, TAXI TO HOLDING POINT ONE RUNWAY TWO SEVEN VIA ALFA, HOLD SHORT OF RUNWAY TWO SEVEN.

**References:** 12.16.4.7 heading/context and item (e), printed 12-34–12-35 / PDF 354–355; 12.16.4.8(d) and acknowledgement note, printed 12-36 / PDF 356; 12.4.2, 12.5.1, 12.9.4(b), and 12.14.1.

**Incorrect fixtures:**

1. Replace VIA ALFA with VIA BRAVO. Wrong route.
2. Replace HOLD SHORT OF RUNWAY TWO SEVEN with CROSS RUNWAY TWO SEVEN. Contradicts the required restriction.

The explicit hold-short instruction is required by this exercise. Do not claim it is universally mandatory in every taxi instruction. Accept ALPHA as a transcription spelling equivalent to ALFA without inventing a pronunciation fault.

### S5 — Incorrect level readback

**Previously issued clearance:**

> INDAIR EIGHT ZERO NINE, CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO.

**Pilot readback:**

> CLIMB TO FLIGHT LEVEL TWO EIGHT ZERO, INDAIR EIGHT ZERO NINE.

Display both transmissions. The clearance remains FL180; the trainee must correct the discrepancy.

**Mandatory:** Address the aircraft, correct the readback to FL180, and avoid confirming or adopting FL280.

**Acceptable:**

> INDAIR EIGHT ZERO NINE, NEGATIVE, CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO.

> INDAIR EIGHT ZERO NINE, NEGATIVE, I SAY AGAIN, CLIMB TO FLIGHT LEVEL ONE EIGHT ZERO.

**References:** 12.9.4(c)–12.9.5, printed 12-10 / PDF 330; NEGATIVE and I SAY AGAIN in 12.6.1, printed 12-6 / PDF 326; S1's climb and level passages.

**Incorrect fixtures:**

1. `INDAIR EIGHT ZERO NINE, CORRECT.` Confirms the erroneous readback.
2. `INDAIR EIGHT ZERO NINE, NEGATIVE, CLIMB TO FLIGHT LEVEL TWO EIGHT ZERO.` Repeats the wrong target.

Do not require the exact sample sentence or make NEGATIVE/CORRECTION universally mandatory. NEGATIVE alone is insufficient because the correct clearance remains unstated. Assess other constructions from the supplied passages; unresolved applicability of 12.8.7–12.8.8 must remain uncertain.

## 5. Recognition pipeline and number preservation

### Processing sequence

```text
Original recording
  -> Audio validation
  -> Two separate STT requests over identical original bytes
  -> Independent observation extraction from each transcript
  -> Compare values, wording, and instruction-bearing elements
  -> Freeze agreed observations; mark disagreements uncertain
  -> Deterministic comparison and source-grounded LLM evaluation
  -> Validate and display result
```

There is no intervening user action.

### Audio intake and execution

- Preserve the native WAV bytes in session state.
- Maximum recording: 60 seconds and 10 MB.
- Validate WAV readability, duration, and nonempty samples. Silence is not a valid transmission.
- Do not aggressively denoise, trim silence, or transform audio in ways that may remove short digits.
- Start processing when a new completed recording appears.
- Use attempt ID, scenario ID, and audio SHA-256 to prevent reruns from duplicating successful requests.
- A new recording creates a new attempt. An intentional retry remains distinct even if its bytes match an earlier recording.
- Two independent STT calls can execute concurrently. Each gets its own file object over the identical bytes; do not share a mutable file cursor.

### STT prompts and context isolation

Both requests receive English language context and generic aviation vocabulary only. Neither receives the expected callsign, target heading/level/code/runway, scenario answer, prior clearance, or pilot readback. The verifier must not receive the primary transcript.

Primary prompt:

> Transcribe the aviation radio transmission faithfully. Preserve spoken number words, repetitions, corrections, and nonstandard wording. Do not improve or complete the instruction.

Verification prompt:

> Transcribe exactly what is audible. Preserve digit order and distinguish individually spoken digits from grouped number words. Do not infer missing callsign characters or numbers. Do not repair incorrect phraseology.

These are prompt requests, not guaranteed verbatim behavior. Verify number-word preservation with audio fixtures. Do not make the implementation depend on log probabilities: current documentation does not establish `gpt-transcribe` support in the same way it documents the feature for older models.

### Separate raw evidence, expression, and value

Retain three representations for every field:

1. Exact raw substring from each transcript.
2. Observed expression type: digit words, grouped-number words, numeral text, or unresolved.
3. Canonical value for comparison.

| Expression | Canonical heading | Wording evidence |
| --- | --- | --- |
| zero eight zero | `"080"` | Digit words retained |
| eighty | `"080"` | Grouped-number expression retained |
| 080 | `"080"` | Spoken form unavailable |
| 80 | `"080"` | Spoken form unavailable; retain original width |
| zero nine zero | `"090"` | Different heading |

Formatting 80 as canonical 080 does not establish that a leading zero was spoken. Never reconstruct claimed spoken words from canonical values.

Additional invariants:

- Store callsign suffixes, headings, runway identifiers, and squawk codes as strings.
- Never pad an incomplete squawk into the expected four-digit code.
- Keep flight levels distinct from altitudes; do not silently equate FL180 with “eighteen thousand feet.”
- Recognize relevant number spellings such as TREE, FIFE, and NINER for value extraction.
- Preserve negations, correction markers, direction words, and instruction verbs.
- Never fuzzy-match values to expected answers or select whichever STT output matches the answer.
- Never run an LLM cleanup pass that repairs the transcript.
- The evaluator must not regenerate or replace extracted values.

Use small field-specific parsers around cues such as FLIGHT LEVEL, HEADING, SQUAWK, RUNWAY, and HOLDING POINT. Parse only trainee transcripts, never scenario text or the displayed pilot readback. Do not create a generic rules engine or unrestricted natural-language parser.

### Reconciliation states

| State | Meaning |
| --- | --- |
| `agreed` | Both transcripts produce the same unambiguous observation |
| `disputed` | Observations disagree |
| `missing` | Both transcripts clearly omit a required element |
| `unresolved` | Parsing, unusable audio, or conflicting instructions prevent interpretation |

Track value agreement separately from wording availability. Agreement on a numeric value does not imply agreement on spoken form.

Examples:

- Both recognize squawk 3426: compare against 3425 and report the mismatch.
- One recognizes 3425 and the other 3426: code accuracy is Uncertain.
- Both imply heading 080, but one says “eighty” and one “zero eight zero”: value can pass; number wording is Uncertain.
- Both output only 080: value can pass; spoken number wording is Uncertain.
- Both retain “eighty”: assess the recognized wording only after recorded-fixture validation establishes that the pipeline preserves this distinction. Do not claim acoustic certainty.
- Ambiguous self-corrections or conflicting clearances: Uncertain, without choosing the answer-compatible occurrence.

Apply the same conservative evidence principle to callsigns, action verbs, directions, negations, and correction behavior. An LLM may not convert disputed instruction wording into a definitive procedural fault.

If one STT request fails after its allowed retry, display the available transcript but mark dependent recognition findings uncertain. Never silently downgrade to single-pass verified grading.

No STT model guarantees recognition. The enforceable guarantee is that subsequent application processing preserves recorded evidence and does not silently alter observed values. Never display invented confidence percentages.

## 6. Data contracts and evaluation

### Local content contracts

```text
ManualExcerpt
  id
  paragraph_reference
  printed_pages[]
  pdf_pages[]
  circumstance_text
  exact_text
  notes[]

Scenario
  id, title
  situation, required_action
  previous_clearance?, pilot_readback?
  expected_information
  mandatory_elements[]
  acceptable_examples[]
  permitted_variation_notes[]
  assessment_scope
  excerpt_ids[]

Attempt
  attempt_id, scenario_id, audio_sha256
  audio_bytes, audio_mime
  primary_transcript, verification_transcript
  observations[]
  processing_status
  evaluation?

Observation
  field
  primary_evidence, verification_evidence
  primary_value?, verification_value?
  canonical_value?
  expression_kind
  recognition_status
```

The implementation may use per-pass expression kinds where needed to preserve disagreement. Freeze observations after reconciliation. There are no edited-transcript or user-confirmation fields.

`assessment_scope` is a short scenario-specific description, not an executable rule language. Collection-level metadata holds the document identity, hash, and curation notes.

### Assessment dimensions

**Phraseology:** Assess prescribed terminology, construction, and permitted variations. Number wording is assessable only when retained by recognition. No acoustic pronunciation scoring.

**Information:** Compare agreed observed values to scenario values deterministically. An LLM cannot override a supported mismatch. Missing and unresolved observations must remain distinct.

**Procedure:** Assess only source-supported behavior within the scenario. Taxi covers the stated hold-short boundary; readback covers correction of the supplied discrepancy. Broader operational procedure for ordinary climb, heading, and squawk is **Not assessed**.

### Structured findings

```text
Finding
  check_id
  dimension: phraseology | information | procedure
  status: correct | incorrect | uncertain | not_assessed
  observed_text?
  expected_value?
  explanation
  excerpt_ids[]
  supporting_quote?
```

Application code adds finding origin (deterministic, model, evidence limitation) and computes verdicts. Use stable scenario-specific IDs for callsign, target level, direction, heading, code, route, destination, hold-short restriction, instruction wording, number wording, and readback correction.

The LLM returns findings and limitations, not the authoritative overall verdict. Use Pydantic structured outputs rather than extracting JSON from free-form text.

### Evaluation input

Provide only:

- The selected scenario and assessment scope.
- Relevant approved excerpts.
- Both machine transcripts, explicitly marked as untrusted data.
- Frozen observations and evidence limitations.
- Deterministic findings and permitted-variation notes.

No whole PDF, search tools, previous attempts, or external aviation knowledge as authority. Spoken instructions aimed at the grader are untrusted data.

Require the evaluator to accept supported alternatives, distinguish wording from value, preserve recognition uncertainty, avoid inventing mandatory words/procedures, and avoid acoustic judgments. It must not attribute missing information to the trainee when recognition is unresolved.

### Validation and aggregation

Before displaying results:

1. Validate the structured schema.
2. Validate check IDs against the scenario.
3. Resolve citations only from the supplied local excerpt IDs.
4. Validate supporting quotes against excerpt text, ignoring whitespace differences only.
5. Require source support for normative phraseology/procedure findings.
6. Preserve frozen values, deterministic mismatches, and recognition uncertainty.
7. Reject contradictory or unsupported model assessment and mark affected checks incomplete/uncertain.

Citation validation checks provenance, not logical entailment. Tests and SME review remain necessary to catch misapplication of a real paragraph.

Within each dimension: a supported incorrect finding makes the dimension Incorrect; otherwise unresolved required checks make it Uncertain; otherwise assessed checks pass. Out-of-scope dimensions are Not assessed.

Overall verdict:

- **Incorrect** if any sufficiently supported finding is incorrect.
- Otherwise **Uncertain** if any required assessment remains unresolved.
- Otherwise **Correct**.

Not-assessed dimensions do not force uncertainty. Preserve an uncertain finding visibly even when a different established error makes the overall result Incorrect.

Use a curated scenario example as **One acceptable transmission**. Do not generate new operational instructions for the corrected example or imply that the example is the only acceptable response.

## 7. UI, state, and failure behavior

### Single-page layout

1. Application title and prominent **Training Prototype** label.
2. Scenario dropdown.
3. Situation and required action; both prior transmissions for S5.
4. Microphone recorder.
5. Automatic processing status.
6. Feedback panel.
7. Try again control.

Keep answer examples hidden until feedback or explicit reveal. Do not require manual transcript review.

Feedback shows overall verdict, read-only recognized transmission, three dimension summaries, individual findings, observed/expected values where relevant, explanations, citations, one acceptable transmission, and playback. Include optional collapsed source excerpts and recognition details. Use text and icons as well as color.

Example uncertainty wording:

> Could not reliably distinguish heading 080 from 090. Heading accuracy was not graded.

Do not append a request to confirm or edit the transcript.

Display:

> Training and demonstration only. Not for live ATC use or certified competency assessment. Audio and submitted text are sent to the configured cloud API.

### Session behavior

Use explicit attempt state, such as recording, processing, complete, and failed, to prevent reruns from duplicating work. Associate responses with the original attempt/scenario so switching scenarios cannot attach stale feedback to the new scenario.

Retry resets the recorder with a fresh attempt ID while retaining the selected scenario. Keep previous session recordings, both transcripts, and feedback available in a collapsed review area. This is in-memory inspection, not a progress dashboard. A clear-session control releases retained attempts; session termination also removes them.

Do not cache attempt audio/transcripts globally across Streamlit sessions or persist them to disk by default.

### Errors

Handle missing credentials, microphone denial, invalid/empty audio, silence or unusable recognition, authentication errors, rate limits, timeouts, refusals, incomplete structured responses, and invalid citations.

- Preserve the recording and completed stages where possible.
- Show an actionable processing/error result.
- Offer recording or processing retry as appropriate.
- Never add a text-input fallback.
- Never label an API/service failure as a trainee mistake.
- Never silently switch models.
- Use a 60-second timeout per API request and at most one SDK retry for transient failures.
- Log only sanitized operational details such as request ID, error category, model, and elapsed time; do not log secrets or full audio/transcripts by default.

If evaluation fails, retain valid deterministic findings but label the remaining evaluation incomplete/uncertain. Do not represent a partial fallback as successful complete grading.

## 8. Implementation work packages

| Order | Deliverable | Completion gate |
| --- | --- | --- |
| 1 | Curated excerpts, scenarios, and ground-truth fixtures | Exact wording, source applicability, references, examples verified |
| 2 | Typed models, extraction, and reconciliation | Lossless representations and uncertainty tests pass |
| 3 | Two-pass STT integration | Representative audio preserves critical values or abstains |
| 4 | Structured evaluator and aggregation | Model cannot override numeric findings or recognition uncertainty |
| 5 | Automatic voice-only Streamlit flow | Recording completion reaches feedback without a review step |
| 6 | End-to-end validation and README | Actual tested behavior, latency, and limitations recorded |

Freeze shared contracts after package 1/early package 2. Coordinate through AGENT_COORDINATION.md. Do not add infrastructure to support the work packages.

## 9. Verification and acceptance

### Offline tests

Normal tests make no paid API calls. Internal text fixtures are appropriate for tests and do not create a typed application mode.

Cover:

- Exactly five scenarios, unique IDs, resolved citations, source metadata/hash, and at least one acceptable/two incorrect examples each.
- All five canonical responses and ten deliberate errors from Section 4.
- Leading-zero headings/squawks; missing, repeated, transposed, and truncated digits.
- Wrong or missing callsign; runway 27 versus 20/07; wrong route and direction.
- “eighty” versus “zero eight zero” versus “080”; phonetic spellings without pronunciation claims.
- FL versus altitude distinction and conflicting self-corrections.
- Primary/verifier disagreement and one STT request failing.
- Expected values present only in scenario context cannot satisfy missing trainee fields.
- Model attempts to override mismatches, uncertainty, or frozen observations.
- Permitted FOR SPACING, FOR DEPARTURE, and I SAY AGAIN variants.
- Missing taxi hold-short restriction; ROGER alone after the incorrect readback.
- Prompt injection and an otherwise valid answer with an unsupported extra clearance.
- Invalid schema, citations, quotations, refusals, and timeouts.
- Not-assessed dimensions and partial/incomplete evaluations.
- Streamlit reruns, duplicate completed-audio events, scenario switching, retry, and session isolation.

### Recorded-audio validation

Build a small labeled audio set containing:

- Fifteen scenario recordings: five acceptable and ten deliberately incorrect.
- Approved optional variants.
- Number contrasts 080/090, 180/190/280, and 3425/3426/3452.
- Missing callsign and incomplete code.
- Grouped-number versus digit-by-digit wording.
- Silence, clipped speech, and moderate background noise.

Use human recordings from at least two speakers, including the intended demonstration accent. Label actual words and values during test preparation. This is development ground truth, not a trainee review step. Synthetic speech can supplement but not replace human-audio validation.

No recorded fixtures were provided during planning. Do not fabricate human recordings, labels, or successful validation. If unavailable during implementation, report that gate as unverified and complete unaffected offline work.

Measure exact critical-field recognition, answer-directed repair errors, wrong-value false passes, correct-answer false failures, uncertainty frequency, preservation of number wording, and end-to-end latency.

### Demo gate

Run the live recorded set twice. Require:

- Clean canonical recordings preserve critical values.
- Approved variants are not rejected.
- Deliberate wrong values never become Correct.
- Clear wrong-value recordings return Incorrect rather than universal uncertainty.
- Ambiguous recordings abstain on affected fields.
- Number wording is graded only where recorded fixtures establish preservation of that distinction.
- Neither recognition nor later processing repairs an error using the expected answer.
- All citations resolve to approved excerpts.
- Recording completion produces feedback with no typing, editing, confirmation, or second submit action.

Record inconsistencies as defects. A small passing set does not establish safety-critical validation. If gates fail, do not restore user confirmation as a workaround; record the limitation and fix or explicitly leave the voice grading capability unverified.

### Manual end-to-end check

With credentials and microphone access:

1. Launch locally and verify all scenarios.
2. Record an approved response and a wrong-value response.
3. Verify automatic processing and citations without review steps.
4. Exercise grouped-number wording and ambiguous recognition.
5. Complete the readback correction exercise.
6. Retry, switch scenarios, and inspect retained session audio/transcripts.
7. Test microphone denial and API failure behavior without a typing fallback.

Browser microphone behavior requires a manual check; mocks cannot verify it. Without credentials, complete offline/mocked checks and report real STT/LLM behavior as unverified.

## 10. Setup, delivery, and limitations

### Required setup commands

Document these PowerShell commands in README:

```powershell
Set-Location D:\ATC
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Environment template:

```dotenv
OPENAI_API_KEY=
OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe
OPENAI_EVALUATION_MODEL=gpt-6.1-sol
```

After setting the API key:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address localhost
```

Offline tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
```

Live tests:

```powershell
$env:RUN_LIVE_EVALS = "1"
.\.venv\Scripts\python.exe -m pytest -q -m live
```

Register the live marker and require the environment flag so normal runs never invoke paid APIs accidentally. Ignore `.env`, virtual environments, caches, and development recordings unless explicitly approved as reusable fixtures. Runtime recordings stay in memory.

### Final implementation handoff

Provide implemented-feature summary, exact commands, scenario references, dependency/model versions, test results, observed latency, and unverified functionality. State which gates passed, failed, or could not run.

Known limitations to document:

- Number representations can be preserved after recognition; recognition itself remains probabilistic.
- Two matching transcriptions can share an error.
- Normalized digits do not establish spoken wording.
- No acoustic pronunciation, accent, pace, or microphone-technique scoring.
- Deterministic parsing covers this bounded scenario set, not arbitrary radiotelephony.
- Valid schema and citations do not guarantee correct interpretation of the source.
- Session data is temporary and cloud inference requires connectivity/API access.
- Automated feedback is formative and not a validated competency assessment.

### SME review items

- Relationship between 12.5.1's general rule and grouped-number examples.
- Acceptable readback-correction constructions and applicability of 12.8.7–12.8.8.
- Fictional taxi scenario and its explicit hold-short restriction.
- Any further source-supported variants that should be included.

Unresolved SME questions remain explicit uncertainties, not invented requirements. SME curation review does not introduce a user-review gate into the application.
