# Voice-controlled approach radar trainer: feasibility and requirements

Date: 5 November 2026. Status: analysis and proposed requirements, not an implementation commitment.

## 1. Recommendation

The SME's proposal is feasible and materially expands the usefulness of the current trainer. The product becomes a simulated approach-control position: the trainee observes moving traffic, speaks instructions, hears pilot readbacks, manages the approach sequence, transfers aircraft to tower, and receives evidence-based feedback.

**First evaluate Vice with the SME, then select the implementation foundation.** Vice already documents spoken aircraft commands and synthesized pilot responses. It is the closest existing demonstration of the requested interaction. If its US-oriented workflows or adaptation requirements are unsuitable, use **BlueSky as the preferred engine for a custom AAI-focused trainer**. Keep **openScope** as the browser-first alternative. Treat an **Endless ATC bridge as a bounded feasibility experiment**, rather than assuming it is the best long-term platform.

The main engineering requirement is a trustworthy relationship between speech, an identified aircraft, a clearance, pilot response, and observed simulator state. Speech recognition alone does not provide that relationship. Separate:

1. Recognition: what was said, and what remains uncertain.
2. Execution: what instruction the simulated aircraft actually accepted.
3. Assessment: whether the words and operational decision were appropriate.

This remains a formative simulation, not live ATC equipment or validated competency assessment.

## 2. Evidence and limitations of this analysis

### Locally inspected

- `README.md`, `IMPLEMENTATION_PLAN.md`, `AGENT_COORDINATION.md`, `speech.py`, `checks.py`, `models.py`, and the curated manual-excerpt collection.
- The supplied 534-page AAI manual. Its SHA-256 matches the existing recorded hash: `1DE3FE5E2D2087C4C170D281D1913FE19DA8F5205A29EFAF5C6BCEE75C7868F8`.
- Text extraction for locating relevant sections; visual inspection of PDF pages 100, 236, 337, 367-371 for the additional requirements discussed below. Source page numbers in this report are one-based.
- `D:\ATC\Endless ATC` contains a `Play Games` installation, including its Windows client and emulator infrastructure. The workspace also contains `Install-Endless ATC Lite-GooglePlayGames.exe`. This is evidence of the Google Play installation route, not of a standalone PC game/API.
- The open window inventory exposed Google Play Games, but the UI inspection did not yield a reliable playable radar view. No aircraft control, installed game version, keyboard support, or state-export interface was verified locally. No separate game APK or game source was identified in the inspected directory listing; that does not prove it is absent from managed storage.

### Researched from upstream sources

Developer instructions for Endless ATC, Vice documentation and repository, openScope documentation/source/license, BlueSky documentation/source, and one related BlueSky voice project. Links appear beside the relevant findings. No alternative simulator was installed, built, or benchmarked in this analysis. Upstream speech accuracy claims are not acceptance evidence for this project.

The current plan's opening status still says the application is unimplemented; the code and coordination ledger demonstrate otherwise. Treat that line as stale. The report proposes a new phase without rewriting the existing product contract.

## 3. Endless ATC: what can be reused and what must be proved

Endless ATC models vectoring arriving aircraft onto an ILS, using heading, altitude and speed controls, with tower handoff and traffic/separation gameplay. Its developer documents keyboard support for the PC edition: selecting a callsign and entering commands, including altitude, speed, approach and holding; F7 exposes controls. Therefore, the available integration choices extend beyond mouse clicks. These capabilities must be checked against the exact edition being used. [Developer instructions](https://startgrid.blogspot.com/2013/11/endless-atc-instructions.html)

### Integration choices

| Route | Required proof | Assessment |
| --- | --- | --- |
| Developer-supported command/state interface | Documented command submission, aircraft identity, state/events and licensing terms | Best Endless ATC option if available. No such public interface was established by this review. Ask the developer before relying on it. |
| Native PC keyboard bridge | Full callsign selection; exact target commands; forced turn direction; application focus; confirmation semantics; state verification | Plausible short demonstration. Prefer absolute targets over repeated increment/decrement keys. PC documentation does not establish compatibility with Android/Lite. |
| Google Play Games mouse/keyboard automation | Reliable screenshots/labels, coordinates across DPI/zoom, selection state, menus, timing and command acknowledgement | Highest fragility. The launcher/emulator adds another integration boundary. Avoid making this the foundation of assessed exercises. |
| Own adapter inside an open-source simulator | Direct aircraft state and supported command hooks | Most control over correctness, replay and AAI adaptation. Requires more initial integration work. |

A bridge must verify the selected callsign before dispatch, read back the assigned target afterwards, and distinguish an accepted target from the aircraft gradually reaching it. Sending a key is not evidence of execution. OCR may confuse identifiers, actual versus assigned values, or overlapping labels. A screen-only bridge also struggles to recover pilot/readback events and exact handoff state.

Do not retry an uncertain UI action blindly: a second relative heading change could produce a different command. On loss of focus or uncertain state, stop dispatch and flag an integration fault. Do not grade that fault as a trainee error.

Custom airport files can help author environments, but configuration support does not establish a runtime command API. Game scoring and simplified handoff rules must not become AAI assessment rules. Confirm the exact game's input/state capabilities and permitted integration/distribution approach before committing to a bridge. Do not infer that bundled open-source library notices make the whole game open-source.

**Time-boxed bridge exit criterion:** control two distinct aircraft by callsign, independently set heading/level/speed, verify target values, perform approach and handoff, and repeat after focus/zoom changes without mis-targeting. If reliable state verification is unavailable, retain it only as a clearly limited demonstration and move to an open engine.

## 4. Open-source options

| Candidate | Verified upstream evidence | Fit and additional work |
| --- | --- | --- |
| **Vice** | Radar simulator with verbal commands and synthesized pilot responses; US STARS/ERAM-oriented; GPL-3.0 repository. Speech documentation calls recognition a work in progress and notes hardware sensitivity. [Docs](https://pharr.org/vice/) · [Repository](https://github.com/mmp/vice) | Best first SME trial. Assess AAI phraseology, Indian callsigns, scenario authoring, evidence capture and scoring. Existing recognition can act on an incorrect interpretation, so audit dispatch before adopting it. GPL distribution implications need review against the intended delivery model. |
| **BlueSky** | MIT-licensed Python traffic simulator with plugins, aircraft performance and conflict functionality. Commands can be used in scenarios, plugins, UI and network communication. [Repository](https://github.com/TUDelft-CNS-ATM/bluesky) · [Command reference](https://github.com/TUDelft-CNS-ATM/bluesky/wiki/Command-Reference) | Preferred custom engine: good fit with the current Python code and deterministic exercise control. Build the training UI, radio dialogue, approach/handoff lifecycle and assessment. It is a simulation toolkit, not a finished AAI approach trainer. |
| **openScope** | Browser radar simulator; commands cover heading, altitude, speed, ILS, routing and more. MIT license. Its `AircraftCommander` dispatches aircraft commands and generates readback output. [Commands](https://github.com/openscope/openscope/blob/develop/documentation/aircraft-commands.md) · [Source](https://raw.githubusercontent.com/openscope/openscope/develop/src/assets/scripts/client/aircraft/AircraftCommander.js) · [License](https://raw.githubusercontent.com/openscope/openscope/develop/LICENSE.md) | Strong browser-first candidate. Add an internal typed adapter and AAI dialogue/assessment. Budget for dependency modernization: the inspected manifest declares Node 11.3/npm 6.4 and older build tooling; this is not proof it cannot run on newer versions. [Manifest](https://raw.githubusercontent.com/openscope/openscope/develop/package.json) |
| **Gotman08/simulateur-controleur-aerien** | MIT repository describing voice-to-BlueSky commands and synthesized readbacks, with published benchmark limitations. [Repository](https://github.com/Gotman08/simulateur-controleur-aerien) | Useful reference implementation, not a drop-in validated product. Its reported fixed-text parser result is 102/116; neither that nor its voice experiments establish this project's accuracy. Audit code, assets/model terms and test reproducibility before reuse. Do not import its RAG/voice-cloning architecture by default. |

Selection order: SME trial in Vice; bounded BlueSky technical spike; openScope spike if browser delivery is the stronger requirement. A new flight-dynamics engine is unnecessary for the first version. Check source, dependency, navigation-data, voice and model licenses separately before distribution; a repository license does not settle every bundled asset's terms.

## 5. What carries forward from the current implementation

Retain voice-only trainee clearances, automatic processing when recording ends, original audio, raw recognition evidence, explicit uncertainty, source-grounded feedback and deterministic findings that an LLM cannot override. No transcript editing, typing a replacement clearance, or user confirmation of guessed recognition.

Reuse the concepts in `models.py`, WAV validation and independent transcription requests in `speech.py`, source loading/citation validation, and evidence-verdict tests. The current `checks.py` branches on S1-S5 and explicitly parses INDAIR; it is not a multi-aircraft command parser. Fixed `expected_information` works for prescribed exercises but cannot grade free control as though only one vector or speed is valid.

The coordination ledger records a 10.59-second synthetic end-to-end attempt with disputed callsign recognition. This is historical local evidence, not a new measurement or a human-voice benchmark. Human-audio accuracy and browser microphone gates remain unverified in that ledger. The batch grading path should not block every radar action.

The larger scenario necessarily changes previous exclusions: pilot simulation, a continuously updating radar and an engine integration boundary are now needed. A local service and modest interactive frontend are justified. Database, accounts, cloud deployment, runtime agent orchestration, unrestricted RAG and generic rule-building UI remain unnecessary for the initial version. Preserve the existing S1-S5 trainer as a regression baseline.

## 6. Bounded first release

Proposed initial exercise: one synthetic, SME-approved approach sector; one active runway with an ILS; fixed weather/QNH; fixed transition configuration; initially two aircraft, increasing to four to six; 10-15 minute repeatable sessions. Start aircraft already identified and in communication to keep the first slice focused. Display these assumptions in the briefing.

The trainee must be able to:

- Identify aircraft from radar labels and address each by its spoken callsign without clicking it first.
- Issue left/right heading, climb/descend/maintain level, and speed instructions.
- Issue approach clearance and request/report relevant approach status.
- Hear pilot readbacks and correct scripted readback errors.
- Transfer communications to the specified tower at the appropriate stage.
- Review a timeline showing what was said, accepted, flown and assessed.

Retain mouse use for scope pan/zoom, scenario selection and instructor pause; aircraft clearances remain voice-only. Start with one aircraft per transmission. Support a defined set of compound instructions only after single-command behavior passes. Explicitly reject unsupported conditions rather than partially interpreting them.

Defer full tower/ground control, taxi, takeoff/landing clearances, multiplayer coordination, emergencies, weather variability, full SID/STAR management and certification. Holding, direct-to and go-around handling can follow once the approach lifecycle is stable. A simulator's built-in capability does not automatically enter the assessed curriculum.

## 7. Functional and technical requirements

| Area | Required behavior |
| --- | --- |
| Radar state | Stable aircraft IDs; callsign; position; actual/assigned heading, level and speed; vertical trend; aircraft type/wake category; approach/runway; ownership/frequency; timestamps and state version. Never confuse ground track with heading or groundspeed with instructed airspeed. |
| Voice capture | Headset and push-to-talk, recording ends on release, visible listening/processing state, no transcript gate. Prevent synthesized pilot audio from becoming trainee input. Define half-duplex radio and interrupted-readback behavior. |
| Recognition | Preserve original audio and untouched passes; parse numbers, units, direction, negation and correction markers. Agreement between passes is not a calibrated confidence score. Deadline/cancel behavior must replace unbounded waiting in the live loop. |
| Callsign resolution | Data-driven telephony/identifier lexicon, leading zeros preserved, all plausible candidates considered, no silent nearest-match or selected-aircraft default. Similar callsigns must produce uncertainty when evidence is insufficient. |
| Command parser | Bounded typed intents with per-field evidence. Distinguish heading-to from turn-by; speed-to from speed-by; altitude from flight level; maintain from climb/descend; immediate from conditional. Unsupported wording has an explicit outcome. |
| Dispatch | Allowlisted engine operations, ownership and capability checks, current state revalidation, idempotent transmission IDs, ordering and expiry. Never feed arbitrary model text into a simulator console, shell or code evaluator. |
| Pilot model | Readbacks from accepted clearance data; controllable response delay; deterministic scripted errors; correction state. An LLM may not invent clearances or update aircraft state through dialogue. |
| Aircraft response | Gradual turns, climb/descent and acceleration; explicit unit conversions; forced turn direction; supported performance limits; approach capture and missed-approach limitations documented. Test engine behavior instead of assuming a command name guarantees semantics. |
| Handoff | Separate transfer of communications, transfer of control/ownership, and approach status. Track instruction, acknowledgement and transfer outcome; do not substitute disappearance of a game label for a recorded handoff. |
| Assessment | Separate recognition uncertainty, phraseology, information, readback discipline, operational outcome and integration failure. Accept multiple valid traffic solutions; use state/time constraints rather than a single expected sentence. |
| Instructor/debrief | Seeded/resettable exercises; pause; scripted readback mistakes; event timeline; source citations; audio playback; distinct training-system failure markers. Keep detailed feedback off the busy radar view until appropriate. |
| Data/privacy | Session-memory default. Optional local export must be explicit, with retention/delete behavior. Keep provider keys server-side; disclose cloud audio processing. No need to persist all audio to build the first slice. |

Keep the recognition passes isolated from expected answers and each other. The current generic vocabulary can become an SME-reviewed domain lexicon. Using a live traffic roster to bias recognition would change the existing context-isolation design: benchmark and document that separately rather than introducing it silently. Resolve identifiers after recognition without replacing the raw transcript.

## 8. Proposed execution architecture

```text
Push-to-talk audio
    -> isolated recognition passes
    -> evidence-preserving parser and callsign resolution
    -> typed clearance + recognition status
    -> dispatch checks against current simulator state
    -> simulator adapter -> accepted/rejected/unknown outcome
    -> pilot readback queue and subsequent aircraft response

Audio + evidence + state snapshots + events
    -> deterministic assessment
    -> asynchronous source-grounded explanation
    -> instructor timeline and debrief
```

Use one simulation owner and clock. A speech job includes session ID, transmission ID, audio hash, capture timestamps, aircraft identity evidence and snapshot version. Revalidate when recognition completes: aircraft may have been handed off, the exercise may have reset, or a newer clearance may supersede it. Reject stale results. Log both wall time and simulation time.

The adapter should expose a small contract: `get_snapshot`, `submit_clearance`, `get_command_outcome`, `subscribe_events`, `pause`, and `reset_scenario`. Outcomes distinguish received, accepted, rejected, unknown and completed. Require explicit per-clause results if an engine is not atomic. For the first compound-command implementation, validate all clauses before dispatch and do not silently execute the recognizable subset.

Critical recognition uncertainty means **no command dispatch**. Show Unclear and permit a fresh spoken transmission; do not require transcript adjudication. A system fault may pause an assisted exercise without penalizing the trainee. In a timed exercise, track invalidated time explicitly.

Conversely, a confidently understood but operationally poor instruction should not automatically be rewritten into the correct answer. Proposed modes: assisted practice can block and explain selected errors; assessment mode permits supported, unambiguous trainee mistakes within the simulation and scores their consequences. Machine-integrity checks always apply. The SME must decide this policy before implementation.

Pilot readback is evidence of the simulated pilot's interpretation, not proof of trainee intent. Scripted readback errors need a defined consequence: whether the aircraft follows the erroneous interpretation after a delay or awaits correction. Log issued, read-back and flown values separately. Do not let injected errors masquerade as recognition failures.

## 9. Manual requirements and expansion of source coverage

Authority: the supplied AAI Manual of Air Traffic Services, Part 1, Edition 7.0, 9 May 2025. This is the user's designated source; this analysis does not establish whether later amendments exist. Chapter 12 remains the phraseology authority. Operational scoring also requires curated procedural passages and scenario-specific local assumptions.

| Requirement | Source in supplied PDF | Product implication |
| --- | --- | --- |
| Callsigns, numbers and level terminology | Existing curated 12.5, 12.7, 12.14; 4.11.7.5.1 note, PDF 100 / printed 4-10 | Keep raw wording and canonical values separate; pressure-reference distinctions matter. No pronunciation grading from normalized text. |
| Readback and correction | Existing 12.9.4-12.9.5; 4.11.7.5.1-3, PDF 100 / 4-10 | Add pilot readbacks and hearback/correction assessment, including heading and speed. |
| Separate frequency transfer | 4.11.7.5.4, PDF 100 / 4-10 | Do not teach a combined speed/level clearance plus tower frequency as a single normal transmission. |
| Heading and direction | 12.17.1.3, PDF 367 / 12-47 | Preserve left/right and absolute versus relative turns. |
| Speed control phraseology | 12.17.1.6, PDF 368-369 / 12-48-49 | Curate exact target, limit and cancellation variants; distinguish pilot-marked replies from controller commands. |
| Approach vectors and clearance | 12.17.2.1-2, PDF 371 / 12-51; continuation needs curation | Separate vectoring, clearance and established status; include runway and approach type as applicable. |
| Frequency change | 12.16.1.4, PDF 337-338 / 12-17-18 | Represent unit/frequency and immediate versus conditional transfer; do not treat CONTACT, MONITOR and STAND BY as synonyms. |
| Position before tower transfer | 8.11.2, PDF 236 / 8-16 | Scenario dialogue must account for position relative to touchdown before frequency change. |
| Operational suitability | Chapters 4, 6 and 8: speed control, approach procedures, vectoring, minimum levels, surveillance separation and transfer | Additional curation/SME validation is required before assigning procedural grades. A heading phraseology table cannot establish safe vector geometry. |

Operational curation queue: 4.8, 4.11.7.5, 4.12-4.13, relevant 6.5 provisions, 8.9, 8.11-8.12, 8.16-8.17 and 8.20. These are review targets, not a claim that all their exceptions are already encoded or verified. Also obtain approved runway geometry, frequencies, transition level/altitude, QNH, vectoring minima, wake/separation applicability and local transfer arrangements for any real aerodrome.

Do not hard-code a universal separation minimum or import a game's defaults as a manual rule. Do not equate an approach clearance with a landing clearance. If the simulator cannot represent an operational requirement, label that dimension Not assessed rather than awarding correctness.

Extend the curated JSON authoring process: preserve circumstance columns, alternatives, notes, pilot markers, page references and source hash; visually check new excerpts; obtain SME interpretation decisions; provide only applicable excerpts at runtime. The existing grouped-number and readback-correction ambiguities remain open. No full-PDF runtime retrieval is necessary.

## 10. Concrete exercise

Synthetic conditions, not a real-airport procedure: INDAIR 809 is identified and controlled, heading 120, level and speed appropriate to the briefing. Another aircraft has a deliberately similar callsign. The trainee sequences it toward runway 27.

1. Trainee: “INDAIR EIGHT ZERO NINE, TURN LEFT HEADING ZERO EIGHT ZERO.” Resolve the callsign, preserve LEFT and 080, submit once, observe the assigned heading and subsequent left turn. Phraseology reference: 12.17.1.3(e).
2. Trainee issues the exercise's appropriate speed instruction. The simulated pilot deliberately reads back a different speed. Record the discrepancy and assess whether the trainee corrects it; the corrected value must not be inferred from the exercise answer.
3. Trainee vectors and clears the aircraft for the ILS at an appropriate state. The simulator separately records clearance and establishment; it must not report established merely because clearance was issued.
4. At the configured transfer stage, provide applicable position information and transmit the tower-contact instruction separately from readback-requiring control instructions. The synthetic tower frequency comes from the scenario, not the language model.
5. Debrief shows recognition evidence, accepted clearances, pilot error/correction, trajectory and transfer events with relevant manual citations.

If recognition disagrees between 809 and 890, neither aircraft changes course. If the trainee clearly addresses 890 and that aircraft exists, this is not automatically an STT fault: interpret the spoken identity faithfully and assess against the exercise context.

## 11. Validation and release gates

Proposed targets below are engineering goals for SME agreement, not measured results or certification criteria.

| Gate | Proposed evidence |
| --- | --- |
| Adapter correctness | Deterministic tests for identity, units, left/right wraparound, accepted targets, approach state and transfer; no duplicate action on retry; reset invalidates queued work. |
| Human speech | At least 300 labelled utterances across five or more representative speakers, including the demonstration accent, similar callsigns, leading zeros, negation, corrections, noise and compound commands. Keep development and held-out evaluation recordings separate. |
| Critical accuracy | Report callsign, action, value, unit and direction accuracy individually and as exact-clearance execution. Proposed controlled-demo target: at least 95% exact completion on supported held-out utterances, with uncertainty/repetition reported separately. |
| Wrong dispatch | Zero observed wrong-aircraft or wrong-critical-value executions in the release corpus; all known ambiguous/disputed cases produce no dispatch. Zero observed events is not proof of zero risk; expand coverage and report corpus size. |
| Timing | Proposed p95 push-to-talk release to accepted command/readback start of 2 seconds under the selected load; report full-readback completion separately. If this fails, reduce traffic or use explicitly paced training. Do not claim real-time readiness from average latency. |
| Dialogue | Correct readback generation, scripted error/correction, no TTS feedback loop, no stale pilot response after reset, no grading failure blocking simulator control. |
| Procedure | SME reviews successful and unsuccessful approaches, tower transfer, applicable minima and simulator limitations; every normative finding traces to approved material. |
| Integrated session | Repeated 15-minute exercises at two and six aircraft, including provider timeout, lost focus where applicable, out-of-order STT completion, and pause/reset. Separate tool failures from trainee performance. |

Track speech and interpretation errors separately from adapter errors. Word error rate alone is insufficient: one incorrect digit can matter more than many harmless word substitutions. Dual-pass agreement must be tested for shared errors. Synthetic speech is useful for regression testing but cannot replace the human corpus.

Operational scoring should use observable events and trajectories: loss of applicable separation, minimum-level breaches, unsupported approach geometry, unresolved readback discrepancies and handoff timing. Delay/efficiency is secondary to those dimensions. Avoid claiming causation solely because an incident followed a transmission; retain state and event evidence for review.

## 12. Delivery plan and effort

Planning estimates for one experienced engineer with regular SME access, existing engine reuse and one bounded scenario; not quotes or guaranteed schedules. Do not add estimates for mutually exclusive engine paths.

| Stage | Deliverable and exit decision | Effort estimate |
| --- | --- | --- |
| Discovery and selection | SME trial of Vice; verify exact Endless edition; BlueSky or openScope adapter spike; chosen scope and simulator limitations | 3-5 working days |
| Vertical slice | Two aircraft; voice heading/level/speed; pilot readback; evidence timeline; uncertainty/no-dispatch and stale-job safeguards | 2-3 weeks |
| Approach training | Approach lifecycle, separate tower transfer, scripted readback errors, curated additions, repeatable exercises | 2-3 weeks |
| Validation and packaging | Representative recordings, latency/error analysis, SME corrections, installer/startup and demo rehearsals | 2-3 weeks |

A custom-engine path is approximately **7-10 working weeks** under those assumptions, with substantial variance. A successful existing Vice workflow could produce the SME interaction demonstration much earlier, but AAI assessment and adaptation remain separate work. A mouse-only Endless bridge may look quick initially and still consume significant reliability work; do not quote it as a shortcut until its state-verification gate passes.

Cost drivers: engineering and SME time, licensed scenario/data assets if needed, recording/annotation, hardware for local speech, and inference usage. For cloud speech, model usage scales approximately as two transcription passes per controller audio minute, plus pilot speech generation and explanation calls. Use actual selected-provider rates and measured audio/token volume at implementation; no unverified price forecast is included. Local speech trades usage cost for hardware and deployment work.

## 13. Decisions the SME should settle next

1. Is matching the exact Endless ATC interface essential, or is a stronger approach-control simulation acceptable?
2. Is the first objective radiotelephony in moving traffic, or operational separation/approach competence as well?
3. Should clear but unsafe simulated instructions be executed and scored, or blocked in assisted practice?
4. Which sector/runway, local rules and trainee accent/callsign vocabulary define the first approved exercise?
5. Is a desktop tool acceptable, and is cloud speech permitted, or is browser delivery/offline operation required?
6. What pilot readback-error behavior and correction timing should the first curriculum use?

These decisions do not prevent the feasibility conclusion. They determine which simulator to adopt and how much operational assessment can honestly be included in the first release.
