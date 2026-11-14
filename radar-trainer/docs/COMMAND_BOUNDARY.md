# Command interpretation and trainer feedback

## Scope

The active command path is now:

`original transcript -> schema-constrained interpretation -> trainer assessment -> existing simulator adapter -> feedback/readback`

`AIClient.interpret` calls `command_interpreter.interpret` once for each nonempty
transcript. Heading instructions, information requests and procedures all use
the same boundary. The old heading shortcut and keyword-selected procedure
prompts are no longer active. Recognition still uses one hinted transcription
call; this migration does not change microphone capture, recognition, or TTS.

## Interpretation contract

`CAPABILITIES` defines each action's parameters, description, bounds and dispatch
kind. Pydantic generates the JSON Schema sent with strict Structured Outputs.
The model receives the transcript, the English extraction instructions and the
capability schema. It receives no expected exercise answer, selected aircraft,
target runway/frequency or current aircraft state.

The result contains `proposals` with the structured order, a verbatim transcript
quotation, timing (`immediate`, `on_missed_approach`, `other_condition`) and the
spoken condition. `unresolved` preserves unsupported or ambiguous clauses.
The model cannot return simulator code. Local code builds the stack commands.

Malformed JSON, unexpected fields/types and unquoted evidence block execution.
There is no prose/code-fence recovery, numeric rounding, or partial extraction
from a broken response. Structurally valid out-of-range proposals remain available
for feedback. Any unresolved clause or invalid member blocks the entire batch.

This validates shape and evidence references, not acoustic correctness or full
semantic fidelity. A quotation does not by itself prove that every extracted
number is correct. Human audio and real-model regression checks remain needed.

## Trainer findings and execution

`command_feedback.py` assesses the interpretation against observed aircraft state.
Each finding has a stable `code`, `category`, `blocking`, `message` and `evidence`.
Categories distinguish instruction inconsistencies, interpretation uncertainty,
exercise rules, simulator limitations and system failures.

For example, a transcript saying "descend to 8,000 feet" while the aircraft is
at 5,000 feet yields `vertical_direction_conflict`. Feedback explains both
values and says to use "climb" **if the target was intended**, or correct the
target/retransmit otherwise. The proposal is not rewritten or sent to the
simulator. The existing 200-foot comparison tolerance is retained.

Feedback is separate from pilot readback and is shown as "Trainer feedback" in
radio history. It is included in both the HTTP response and WebSocket exchange.
`proposed_orders` is retained even when `orders` is empty; `execution_status`
distinguishes `blocked`, `queued`, and `handled`. Queued does not mean the
aircraft has completed the maneuver. Reports use real simulator state.

Known corrective explanations are deterministic and incur no extra model call.
The structured findings provide the input boundary for a future LLM coaching
layer: it may explain supplied facts but must not alter proposals, execution
decisions, aircraft state, or claim the audio was wrong. That extra layer is not
enabled in this change. Nonblocking findings can accompany accepted instructions;
current checks remain blocking where execution cannot faithfully implement the request.

Existing exercise and simulator checks remain authoritative. Their messages are
adapted to trainer findings; this is intentionally an incremental migration of
execution policy, not a new clearance state machine. Procedure checks still run
on the simulator thread. A long-turn rejection is labelled a simulator limitation,
not automatically a trainee error. Other procedure errors include their existing
reason and, where applicable, guidance to review the procedure/state.

## Extension points and limits

To add an action, add its capability and structured parameter types, execution
adapter/handler, assessment rules and behavioral tests. Merely adding a schema
entry does not implement simulator behavior. No new keyword router is needed.

Immediate heading/altitude/speed compounds remain supported under existing
exercise checks. General compound procedure clearances, alternatives, cancellation
and arbitrary future conditions are not implemented. They must be represented
and blocked with feedback rather than silently reduced to one executable command.
Supported missed-approach assignments still reserve a single heading/altitude
through the existing simulator handler. This migration does not make the trainer
capable of executing every command BlueSky supports.

## Retained code and archive

The active interpreter no longer depends on `atc_llm`, `kb_oaci`,
`04_ner_extraction`, `03_bluesky_connector`, or the legacy sector graph prompt.
The scenario generator still uses legacy modules, separately from this boundary.
The shared `atc_callsign` normalizer and factual vocabulary, readback generation,
`simple_demo` execution policies, and simulator integration are retained.

[The reference archive](../archive/command-boundary-2026-11-12/README.md) contains
the exact pre-migration boundary and a SHA-256 manifest. No archive code is loaded
at runtime. This is not a claim of repository-wide independence from earlier code.

The provider must support strict JSON Schema in Chat Completions. Unsupported
providers fail visibly; there is no silent downgrade to a less constrained parser.
See [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).

## Verification

Verified during the 12-13 November 2026 migration:

- Full backend suite: 664 passed, 3 skipped before the final condition/revision guard.
- Final affected backend suite, including the new guard: 105 passed, 1 skipped.
- Frontend history/feed regression tests: 13 passed under Node 24.
- TypeScript checking and Vite production build passed.
- All 16 archived source/test files match their recorded SHA-256 hashes.
- Structured-output schema checks confirm closed objects and required properties.

Provider responses were mocked. No paid live model call or human microphone
accuracy test was performed for this migration. The existing backend process was
not restarted; restart it and reload the UI to use the replacement boundary.

## Product review findings (13 November 2026)

These are follow-up decisions, not implemented changes. Preserve the distinction
between a verified defect, a design preference, and an unmeasured quality claim.

1. **Verify the transcription request end to end; do not change the field names
   merely to match the SDK example.** `SttClient.transcribe` sends `prompt` as one
   multipart field, `languages[]` as `en`, and the live vocabulary as a list under
   `keywords[]` for `gpt-transcribe`. `requests` expands that list into repeated
   `keywords[]` multipart fields. This matches the documentation's cURL example;
   the Python SDK expresses the same logical inputs as `extra_body={"keywords":
   [...], "languages": [...]}`. The existing unit test checks the Python `data`
   dictionary, but no live OpenAI response or representative-radio accuracy was
   verified. Add a wire-format test and a small live evaluation with callsign and
   number errors tracked before declaring the integration reliable. For other
   models/providers, the code appends possible spellings to `prompt`; check that
   branch against each provider's actual contract. Documentation:
   https://developers.openai.com/api/docs/guides/speech-to-text#add-transcription-context

2. **Give execution policy one authoritative contract.** `simple_demo.validate`,
   `atc_app._execute_instruction`, `approach_radio.validate`, and simulator
   procedure handlers currently contribute restrictions and rejection strings.
   Define typed policy findings and their ownership in one place, then have the
   API orchestrator consume them. Keep a final state check at dispatch because
   the aircraft can move while speech is processed. Consolidation is for
   consistency and maintainability; no speed or recognition gain is established.

3. **Design the requested LLM coaching stage.** Current trainee feedback is
   deterministic: interpreter checks and `command_feedback.py` construct fixed
   findings, while `policy_feedback` classifies some legacy rejection strings by
   matching words in the message. The interpreter LLM extracts proposals and
   unresolved quotations; it does not generate feedback prose. Evaluate a
   separate coaching call given the transcript, proposed orders, typed findings,
   and relevant observed state. Its output could highlight wording and explain
   novel cases, but must not change execution decisions or invent audio evidence.
   Compare it with human-reviewed scenarios, especially numbers, negation, and
   procedure errors. This adds latency and cost; quality improvement is unproven.

4. **Simplify the interpreter prompt after evaluation.** The model needs the
   observable task: extract only supported instructions, preserve spoken values,
   conditions and corrections, quote supporting text, and mark unresolved
   clauses. Internal explanations such as "local code handles its canonical
   form", "the trainer evaluates them later", and "do not judge exercise
   state" could be replaced with direct behavioral instructions. Do not remove
   the underlying constraints against callsign inference or plausibility repair.
   A shorter prompt may be easier to maintain, but equal extraction quality and
   latency have not been demonstrated.

### Removal candidates and their limits

| Candidate | Can be removed without changing current command execution? | Performance claim |
| --- | --- | --- |
| Architecture explanations in the interpreter prompt, once their behavioral constraints remain | Yes in code structure; model behavior still needs regression evaluation | No measured speed or accuracy gain |
| Keyword matching of legacy rejection **messages** in `policy_feedback`, after producers return typed codes directly | Yes after that migration; currently it determines feedback category and wording | No measured runtime gain |
| Duplicate policy checks, after one authoritative policy check and dispatch-time state check cover the same cases | Potentially, after equivalence tests | No measured runtime gain |
| Separate `keywords[]` fields for `gpt-transcribe` | **No**; they carry recognition hints | Removing them may reduce recognition quality |
| Callsign evidence, schema validation, condition/negation guards, or final simulator state checks | **No**; they currently block unsupported execution | Removal changes behavior and risk |
| LLM coaching call | Not present yet | Adding it costs time and tokens; value needs evaluation |

There is no evidence that any prompt or policy removal is performance-neutral in
the sense of preserving recognition accuracy, interpretation accuracy, latency,
and trainer quality. The table distinguishes code-path redundancy from those
unmeasured outcomes.
