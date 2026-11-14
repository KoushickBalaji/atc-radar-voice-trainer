# Local voice radar prototype

This is a local adaptation of [Gotman08/simulateur-controleur-aerien](https://github.com/Gotman08/simulateur-controleur-aerien), based on commit `ca929437f29926a6459b1265d7f9b6d0b8c3be48`. Its MIT license and attribution are retained in LICENSE. BlueSky supplies the aircraft simulation; the upstream canvas supplies the radar. This is a separate checkout from the existing Streamlit trainer.

## Run

Double-click `D:\ATC\Start-Radar-Trainer.cmd`, keep its window open, and visit http://127.0.0.1:8000 in Chrome. First startup can take about a minute while BlueSky loads. The scenario starts paused. If the server is already running, simply open the URL.

Choose an airport from the Airport selector (124 available; 73 have modeled ILS). Coimbatore (VOCB) is the worked example below. Switching airports resets and pauses the exercise; Reset keeps the selected airport. Click **Start / Resume** and **Enable microphone**. Once **Hold to talk** appears, hold **V** or the mic button while speaking; release to send. The radio keeps the last 200 ms of mic input locally so a word starting at the keypress is included. No audio is uploaded while idle. **Switch mic off** or leave the tab to release the microphone. Use headphones. Wait for processing to finish before the next transmission. **Reset exercise** returns to the initial aircraft and clears the display.

The demo snapshots live simulator traffic when a recording reaches the voice handler. One transcription call receives spelling hints: current aircraft IDs and their spoken forms, operator names represented in that traffic, phonetic alphabet terms, and airport/fix vocabulary. The list refreshes for each transmission and is independent of screen zoom or aircraft selection. Hints are optional recognition context; an unlisted callsign must remain unlisted, and flight-number digits must not be changed to match the roster. Expected clearances and target values are excluded. The transcript must support the addressed aircraft and pass local command validation before the simulator acts.

The sidebar generates instructions for the selected airport. For Coimbatore, try these separately:

1. “Air France one two three, turn right heading two five five.”
2. “Air France one two three, descend to three thousand two hundred feet.”
3. “Air France one two three, reduce speed to one eight zero knots.”
4. “Air France one two three, cleared ILS approach runway two three.”
5. Once the glide slope is captured, say “Air France one two three, contact tower one one eight decimal one five zero.” Coimbatore continues flying until handover. At 6 NM from the runway threshold the pilot asks once for confirmation. At 2 NM without handover the pilot announces a go-around and flies the modeled missed approach. A valid handover ends the normal exercise.

These are Coimbatore training distances. The airport profile’s `exercise.tower_handover` sets `request_nm` and `go_around_nm`. The rule requires a verified tower channel and a modeled missed approach. Coimbatore’s SMAC check allows the cleared, aligned localizer segment at intercept altitude and normal glide-slope descent. It resumes on deviation or go-around.

The pilot reads back the instruction aloud. The aircraft turns, descends and slows over simulated time; values do not jump immediately. Instructions may also be given while paused, then observed on resume.

## Configuration and scope

`run_openai.py` reads `OPENAI_API_KEY` directly from `D:\ATC\.env`, without copying it into the frontend or repository. All three providers use `https://api.openai.com`: `gpt-transcribe` (or the workspace transcription model), `gpt-4.1-mini` for interpretation, and `gpt-4o-mini-tts` for pilot speech. These are paid API calls. Model overrides are `ATC_STT_MODEL`, `ATC_LLM_MODEL`, and `ATC_TTS_MODEL`. The launcher does not use the upstream custom fine-tuned server. Model availability can change; the current speech model has a published January 2027 retirement, so replace it before then.

The scenario has one A320, AFR123, initially heading 240 at 5,000 ft and 220 kt CAS, near Coimbatore airport (VOCB), modeled from the supplied AAI charts. Supported actions are immediate heading, altitude/flight-level and speed changes. Speed is bounded to 160–300 kt and level to 3,000–18,000 ft. The radar's upstream label shows ground speed; the sidebar explicitly shows airspeed (CAS).

This slice implements a bounded approach-control sequence: explicit spoken ILS clearance, heading/level/speed vectoring, stable ILS tracking, then a spoken tower-frequency handoff. Landing, full published procedures, QNH/transition-altitude handling and competency scoring are not implemented. Upstream advanced scenarios remain in source; they are not verified for this demo profile.

## Recognition and guidance

Each recording has one transcription call with live recognition context, followed by one interpretation step for a nonempty transcript. If parsed commands identify an unknown aircraft, contain unsupported actions, or fail local validation, no command is sent. Audio failing the signal-level check is rejected before calling OpenAI; an empty transcript is rejected without interpretation. Concurrent transmissions are refused. Recognition errors remain possible; this is not a validated human speech benchmark.

The command interpreter uses one English capability schema with strict structured output, without the legacy French reference cards, regex hints or sector-graph prompt. Original transcripts, proposals and unresolved wording are retained separately from execution. Trainer feedback explains instruction inconsistencies, exercise restrictions and simulator limitations; it never executes its suggested correction. Existing procedure checks and pilot readbacks remain in place. The last 20 recordings, their recognition context, transcripts and interpretations remain in server memory for investigation, and are cleared on scenario reset/restart. User recordings are not automatically written to disk. See [the boundary design and archive](docs/COMMAND_BOUNDARY.md).

## Verification

Historical capture-only verification (before the explicit clearance/handoff update): the Python suite passed 249 tests, including demo rejection/readback tests. TypeScript checking and the production frontend build pass. A paid synthetic-audio integration test exercised the actual `/api/voice` upload route, OpenAI transcription, interpretation, speech synthesis, and BlueSky target tracking. It progressed through armed, localizer, glideslope and complete, then paused automatically. Final observed errors were 0.001 NM cross-track and 18 ft above the ideal glide path, with 13.2 simulated seconds of stable tracking and no simulation command errors. Observed request times were roughly 5–18 seconds. This does not establish microphone/accent accuracy; try your own speech in Chrome next.

Evidence is in `outputs/verification/VOCB/result.json` and `outputs/verification/VOML/result.json` and accompanying input/readback WAV files. To repeat the paid test with the server running:

```powershell
.\.venv\Scripts\python.exe scripts/verify_openai_demo.py
```

For offline tests: `.\.venv\Scripts\python.exe -m pytest`.

The installed environment and built frontend are ready locally; Node is unnecessary to run. To rebuild, use Node 22.12+ and run `npm ci`, then `npm run build` in `frontend`. On this Windows machine npm omitted an optional native parser binding; installing `@oxc-parser/binding-win32-x64-msvc@0.112.0` with `--no-save` resolved that build issue. Dependencies retain upstream versions; this is not a production hardening or dependency upgrade pass.


## Coimbatore airport model

The demo now uses VOCB instead of the synthetic airport. Source files are in `D:\ATC\Airport Layouts\Coimbatore`:

- `VOCB-ADC.pdf`, aerodrome chart AD 2 VOCB 1-101, 09 July 2026: precise ARP 11°01′36.88″N, 077°02′30.49″E; aerodrome elevation 1,330 ft; runway magnetic directions 048°/228°.
- `AD 2.1VOCB.pdf`, AD 2.12, page 12, 09 July 2026: runway 05/23, 2,990 × 45 m; true bearings 045.72°/225.72°; threshold 05 at 11°01′20.39″N 077°02′05.44″E, 1,330 ft; threshold 23 at 11°02′28.32″N 077°03′15.96″E, 1,277 ft.

The ADC ARP has greater precision than the rounded AD 2.2 position. Coordinates are WGS84; published elevations use EGM08. `data/airports/VOCB.json` holds the chart values and exercise settings; `src/airport_profiles.py` computes geometry for either airport. `src/coimbatore.py` is only a compatibility facade for earlier tests. The runway is drawn from its surveyed threshold coordinates, with a minimum visible stroke width at radar scale. Zoom in with the mouse wheel to inspect it. No invented sector boundary is drawn.

The simulator and radar share the new origin; AFR123 starts 2 NM beyond the outermost available airport-specific published lateral boundary or SMAC coverage along the arrival path, retaining its configured offset from final, heading, altitude and speed. The radar view fits that position independently. For Coimbatore the offset is 3 NM and altitude is 5,000 ft. That placement, heading and level are exercise settings, not a charted arrival. Reset restores this position. The same voice examples still work. Existing simulator heading commands use true north; published magnetic runway bearings are identified separately in the interface. No magnetic-heading conversion has been added.

The radar shows the ICMB localizer and GP/DME, CCB VOR/DME, CB NDB, extended RWY23 final, IF and LOC-only FAF references. Parking stands, taxiways, obstacle inventories, complete approach routes/minima remain outside this exercise. SMAC monitoring and a training tower handoff are implemented as described below. Chart terrain/obstacle and local airspace restrictions are not enforced by this prototype. Airport elevation is reference metadata, not a new terrain or landing model. The supplied chart editions are the source snapshot; no claim of live operational currency is made.


## RWY23 ILS capture objective

Source: `VOCB-ILS-LOC-Z-RWY 23.pdf`, AD 2 VOCB 2-107, 17 April 2025. The chart provides 228 degrees magnetic final course, 3-degree glide path, threshold elevation 1,277 ft, reference datum height 56.7 ft, 3,200-ft intermediate altitude, IF 11.6D ICMB and LOC-only FAF 6.1D ICMB. AD 2.19 provides localizer and GP/DME antenna positions; CCB and CB coordinates come from the ILS Z/Y charts. The FAF symbol is a LOC-only reference, not an outer/middle marker beacon or a separate ILS success gate.

The displayed localizer is runway-aligned at 225.72 degrees true, using the surveyed runway geometry. The chart's magnetic final and its old variation differ slightly from that alignment; no live magnetic-model correction is applied. DME marker positions use horizontal distance projected onto this line, rather than full slant-range radio modeling. The ideal glide path is threshold elevation + reference datum height + distance-to-threshold times tan(3 degrees).

Training settings (not official minima or aircraft operating limits):

- Localizer capture: 7–12 NM out, within 0.15 NM of final, inbound track within 30 degrees, 3,200 ft ±75 ft, vertical rate within 300 ft/min, 160–180 kt CAS, at least 75 ft below the ideal glide path.
- After localizer capture the simulated pilot automatically turns onto and tracks final. It retains the selected level until the descending glide path reaches the aircraft. A new heading or altitude instruction overrides this guidance and requires a fresh ILS clearance.
- Glide-slope capture: prior below-path observation, within -40/+25 ft of the path, cross-track within 0.12 NM, track within 5 degrees and speed in range. Capture from above is rejected.
- Handoff readiness: at least 10 simulated seconds tracking both beams, within 0.12 NM laterally and 75 ft vertically, aligned within 5 degrees, descending, and at 160–180 kt. The simulation pauses before landing. A valid spoken tower handoff then completes the exercise.
- Passing inside 3 NM without completion, going below 3,000 ft before glide-slope capture, or losing localizer tracking pauses the exercise as unsuccessful. Reset clears capture history and restores the aircraft.

This is a simplified guidance controller using BlueSky heading/altitude/vertical-speed commands, not a radio-signal/autopilot certification model. The speed window and capture tolerances are chosen for this learning task, not claimed to be specified by the chart. The objective measures a successful ILS setup, not complete ATC competence or landing clearance. The pilot accepts the named ILS clearance below 5,000 ft AMSL or with an active descent assignment below that level. At localizer capture the pilot requests landing clearance. A runway-specific “cleared to land” lets the aircraft continue to the radar exercise endpoint. At Coimbatore, absent landing clearance or tower handoff, the existing 6 NM reminder and 2 NM go-around apply. During the published missed approach or its hold, a new heading releases the aircraft for vectors and a fresh ILS clearance. Clearance and handoff must each be separate, immediate transmissions.

The updated paid integration test in `scripts/verify_openai_demo.py` uses all five voice examples above, accelerates simulation for verification only, asserts the success pause, and resets to normal speed afterward. Browser use stays at normal speed; expect several minutes from vectoring to capture.


## Airport profiles and Mangaluru

Airport-specific values are now parameterized in `data/airports/VOCB.json` and `data/airports/VOML.json`. Shared training tolerances and guidance gains live in `data/airports/training.json`. Optional `training_overrides` in an airport profile override those defaults. The common `AirportProfile` and `ILSTrainer` classes handle both airports without airport-specific branches. The UI reads the selected profile's runway, navigation aids, intercept level, examples and limits from the backend.

| Setting | Coimbatore | Mangaluru |
|---|---|---|
| ICAO | VOCB | VOML |
| Runway | 05/23 | 06/24 |
| Runway length / width | 2,990 / 45 m | 2,330 / 45 m |
| Aerodrome elevation | 1,330 ft | 318 ft |
| ILS exercise runway | 23 | 24 |
| Final course, published magnetic | 228 degrees | 240 degrees |
| Runway-aligned simulator true course | 225.72 degrees | 238.39 degrees |
| Intercept altitude | 3,200 ft | 2,400 ft |
| Glide path / reference datum height | 3 degrees / 56.7 ft | 3 degrees / 54 ft |
| Localizer | ICMB 109.1 MHz | IMNG 110.1 MHz |
| VOR/DME | CCB 112.9 MHz | MML 114.2 MHz |
| Example true heading | 255 | 268 |

Mangaluru sources are the supplied `Airport Layouts/Mangaluru` files:

- `VOML-ADC.pdf`, 11 June 2026: ARP 12°57′43.42″N 074°53′23.23″E; runway threshold coordinates; 318-ft airport elevation.
- `AD 2.1VOML.pdf`, AD 2.12 p16 (22 January 2026): runway dimensions, true bearings and threshold elevations (06: 309 ft; 24: 310 ft). AD 2.19 p20 (27 November 2025): localizer and GP/DME coordinates and frequencies.
- `VOML-ILS (Z)-RWY-24.pdf`, 15 July 2021: final 240 magnetic, intercept 2,400 ft, 3-degree glide path, RDH 54 ft, MML coordinates, IF 13D from **MML**, LOC-only FAF 6.5D from **IMNG**. This scanned chart was visually inspected; its body is not recoverable through ordinary text extraction. Its 2021 edition is the supplied snapshot, not a claim of current operational validity.

For Mangaluru, speak separately: “Air France one two three, turn right heading two six eight”; “Air France one two three, descend to two thousand four hundred feet”; “Air France one two three, reduce speed to one eight zero knots.” The same capture engine and success objective apply.

Airport switches are executed on BlueSky's simulation thread under the radio processing lock. A switch clears prior aircraft, capture history, wind/zones, and voice evidence, relocates the projection origin, creates the profile's aircraft, and pauses. The frontend reloads navigation geometry and remounts the radar/recorder so prior trails and recordings do not carry over. Invalid profile IDs are rejected before mutation; switching during a processing transmission is rejected. The selected profile lasts for the server session. To choose a startup default set `ATC_AIRPORT=VOML` (default is VOCB).

To add another airport of the same supported single-runway ILS shape, copy a profile JSON and supply its chart-derived values, named distance references, source editions, and exercise starting conditions. Use the ICAO code as the filename and `icao` field. Restart the server to load new/edited files. No new geometry, UI or capture-engine code is needed for that supported shape. Additional runway selection or different procedure types would require further implementation. Source charts are curated manually; this is not an automatic PDF importer.

Verification commands (paid OpenAI calls, server must be running):

```powershell
.\.venv\Scripts\python.exe scripts/verify_openai_demo.py --airport VOCB
.\.venv\Scripts\python.exe scripts/verify_openai_demo.py --airport VOML
```
## Minimum Safe Altitude Warning (SMAC training check)

Mangaluru now includes the supplied **AD 2 VOML 3-301, 16 APR 2026** SMAC.
The five areas have minima of 2,400, 3,500, 5,500, 6,600 and 8,400 ft AMSL.
The 6,600 ft area includes its narrow continuation below the 8,400 ft area.
Source: `../Airport Layouts/Mangaluru/VOML-ATC-SMAC.pdf`; A1-A14 are transcribed
from the chart's boundary table. This is a local chart snapshot, not a live AIP feed.

Coimbatore uses **AD 2 VOCB 3-301, 17 APR 2025**, from
`../Airport Layouts/Coimbatore/VOCB-ATC-SMAC.pdf`. The chart's 19 named vertices
define areas at 3,200, 5,800, 7,400, 9,500 and 11,000 ft AMSL. The three 9,500 ft
labels belong to one connected region. P-W follows the curved northwest rim;
the other edges follow the chart's straight segments. The 30/40 NM dashed range
rings are reference rings, not a circular coverage limit. Restricted-area and
TRA vertical limits on the chart are not SMAC minima and are not imported.
Coimbatore's initial aircraft is at 5,000 ft outside the configured SMAC coverage. Monitoring reports outside coverage until it enters a mapped region.

The radar draws purple boundaries and minimum labels. Each aircraft's current
latitude, longitude and altitude are checked on every simulation snapshot
(normally about 10 updates per wall-clock second). Below the applicable minimum,
the aircraft label turns red and gains `MSAW`; the sidebar reports current
altitude, minimum and deficit. The warning clears at or above the minimum, or
when entering a region with a lower applicable minimum. Shared edges and
overlaps use the highest minimum. Warnings do not block voice commands, move
the aircraft or automatically pause the exercise. There is no audible alarm.

Mangaluru's initial aircraft now starts beyond its outer published approach-area
boundary and outside the configured SMAC coverage. Monitor the applicable minimum
as it enters mapped coverage; do not use the 2,400 ft descent example until inside
the appropriate area. The ILS success condition remains unchanged; MSAW is a
separate advisory, not an added scoring or pass/fail system.

The SMAC says it is for cross-checking assigned altitudes under vectoring
control. This implementation checks **actual** simulated altitude. It suspends
the vectoring-minimum check only for the trainer aircraft with captured glide
slope (or completed capture), inside the configured final approach line length,
and currently within the shared ILS stable cross-track, heading and altitude
tolerances. The UI explicitly shows `SMAC check suspended`. A manual vector,
lost tracking, or excessive deviation restores the check. This is a training
policy, not a chart-published MSAW inhibition area. Localizer capture alone
does not suspend monitoring.

`src/msaw.py` is independent of airport names and operates within the existing
simulation thread in `src/atc_sim.py`; no additional worker or BlueSky fork is
needed. No native SMAC/MSAW facility was found in the installed BlueSky Python
source. The same polygons feed both the monitor and radar display. The current
altitude datum assumes the simulation's feet represent chart AMSL; pressure/QNH
correction, terrain sampling, predictive warning, operational MSAW calibration,
and full approach obstacle clearance are not implemented.

To add another airport's chart, add an optional `msaw` object to its existing
airport JSON:

```json
{
  "msaw": {
    "schema_version": 1,
    "coordinate_reference": "WGS84",
    "altitude_unit": "ft",
    "altitude_reference": "AMSL",
    "source": {"chart": "chart identifier", "effective_date": "YYYY-MM-DD"},
    "suspend_on_tracked_ils": true,
    "points": {"A": [11.0, 77.0], "B": [11.1, 77.0], "C": [11.0, 77.1]},
    "regions": [
      {"id": "region-1", "minimum_ft": 4000,
       "boundary": ["A", "B", "C"], "label": [11.02, 77.02]}
    ]
  }
}
```

Coordinates and label anchors are `[latitude, longitude]`. Boundaries close
automatically. A boundary item `{"to":"B","center":[lat,lon]}` draws a
clockwise arc from the preceding point to B about the supplied center; ordinary
point names draw straight edges. In Mangaluru the outer arcs follow the 30 NM
ARP rim. Arcs are approximated in the existing local NM projection at at most
0.25 degree intervals, interpolating endpoint radii to preserve the tabulated
vertices. This introduces small geometric approximations, not survey precision.
Polygons must be simple and chart coverage should have no unintended gaps;
tests exercise all regions, shared boundaries and the chart interior.

An airport without `msaw` shows "SMAC data has not been
configured". Aircraft outside all regions show "minimum unknown"; invalid
positions/altitudes and simulator disconnection also show unavailable states.
Never interpret these as clearance or an absence of terrain risk.

Validation: 274 Python tests pass after adding Coimbatore, including its region
interiors, shared vertices, coverage, and convention validation. The unchanged
frontend previously passed 8 tests, TypeScript and production build. Live BlueSky snapshots verified low/clear states, simultaneous
aircraft in different regions, reset and airport switching. Browser verification
confirmed the boundaries, red radar tag and warning card. Evidence is in
`outputs/verification/msaw-runtime.json` and `outputs/verification/msaw.png`.

## Data storage and adding other countries

The authored data is ordinary JSON in `data/airports/<ICAO>.json`, one document
per airport. `VOCB.json` and `VOML.json` hold runway geometry, navigation aids,
ILS parameters, the exercise setup and an optional `msaw` object. `country_code`
is an ISO-style two-letter country identifier (`IN` for these two airports),
metadata for cataloguing rather than a switch in the warning logic. ICAO is
the lookup key. `training.json` contains shared exercise tolerances, with optional
per-airport overrides. Chart source paths, identifiers and effective dates are
kept alongside the data; the original PDFs remain the source of record.

The `msaw` object separates:

| Field | Purpose |
| --- | --- |
| `schema_version` | Format version, currently 1 |
| `coordinate_reference` | Canonical coordinates: WGS84 decimal degrees |
| `altitude_unit`, `altitude_reference` | Canonical minimum: feet AMSL |
| `source` | Chart file, identifier, effective date and interpretation notes |
| `points` | Named `[latitude, longitude]` vertices, shared between regions |
| `regions` | Stable IDs, ordered boundaries, minimum altitude, display anchor |
| `suspend_on_tracked_ils` | Explicit trainer policy for the existing ILS exercise |

At load time `airport_profiles.py` reads the selected JSON and caches the
profile in memory. `msaw.py` expands its geometry once into local NM polygons.
Each update compares aircraft coordinates with those polygons and returns the
highest applicable minimum. The browser receives the same geometry from
`/api/nav`; the simulator's per-aircraft state carries the warning result.
No PDF parsing, LLM request or database lookup occurs during a warning check.
Editing JSON requires restarting the server because profiles are cached.

The replication workflow is: obtain the relevant country's authoritative chart;
check its datum, units, coverage and notes; transcribe/convert the boundaries
and minima to the canonical format; retain source provenance; test known points,
edges, gaps and overlaps; inspect the rendered map against the chart; then make
the airport available. Files are automatically discovered by ICAO filename.
Chart types may be called SMAC, MVA or another local term: they must be reviewed
for the same vectoring-minimum meaning rather than assumed equivalent by name.
Values in metres or other datums must be converted and reviewed before import.
Unsupported declared units, datum, coordinate reference or version are rejected
by the loader; coordinate bounds and finite values are checked. Legacy fields
omitted from older data default to version 1/WGS84/feet/AMSL. This is targeted
validation, not a full JSON Schema or automated chart certification.

This approach supports adding many airport datasets without duplicating the
warning engine. Runtime work is proportional to aircraft count and the selected
airport's polygon edges, not the total worldwide airport catalogue. The
airport list reads JSON metadata without constructing each warning polygon.
A large global catalogue could use a lightweight index. Many aircraft or very detailed regions
would also justify a spatial index, and concurrent multi-airport sessions would
need session-scoped state. None is necessary for this single-airport prototype.

International limits remain explicit: the local projection is intended for an
airport-sized area and is not implemented for date-line crossings or polar
geometry; boundaries with holes or special exclusions would require a schema
extension. National altimetry rules, transition levels and approach inhibition
policies are not automatically inferred from the country code. Source revision
history and update ingestion are manual; effective-date selection is not yet
implemented. A future database can store the same normalized records, but the
current portable JSON files are the authoritative application data.

## India airport catalogue import

The selector now contains 124 airports: 73 with ILS (including the existing
Coimbatore and Mangaluru) and 51 in vectoring-only mode. Bengaluru HAL and
Navi Mumbai are included; Bengaluru KIA and Mumbai are deferred by request.
Chennai, Dibrugarh, Hisar, Madurai, Thiruvananthapuram, Tirupati and Vijayawada
are excluded because ILS is mentioned but no ILS chart was supplied.

Each airport uses one selected runway and one aircraft. Other runways and full
instrument procedures are not modeled. Airports with no ILS identified in the
supplied documents have `approach: null`: no fabricated localizer/glide slope,
autopilot capture, or ILS success score. Their altitude examples are synthetic
practice settings. The A320 is an airborne training target, not a statement of
aircraft suitability for every runway. Published runway dimensions may differ
from threshold-to-threshold distance because of displaced thresholds.

Data is still stored in `data/airports/<ICAO>.json`. Published geometry and final
approach parameters are separated from `exercise` and `training_overrides`.
`provenance` records source pages and visual ILS review; chart dates/restrictions
are not automatically enforced. There is no live NOTAM or currency service.

Reproducible stages, run from this directory:

```powershell
.venv/Scripts/python.exe scripts/audit_airport_compatibility.py
.venv/Scripts/python.exe scripts/extract_airport_geometry.py
.venv/Scripts/python.exe scripts/extract_ils_profiles.py
.venv/Scripts/python.exe scripts/import_airport_profiles.py
```

The audit uses cached PDF text under `../tmp/airport-audit`. Geometry extracts,
reviewed ILS overrides, and source evidence are retained in
`outputs/airport-import`. The publisher validates every candidate before writing
runtime profiles and preserves VOCB/VOML. It requires visual review of ILS
values and rejects missing-chart airports instead of treating them as non-ILS.
The import count assertions encode this specific batch; another country requires
a new inventory/policy and source review, not changes to the flight engine.

See [the catalogue](outputs/airport-import/catalogue.md) and
[machine-readable manifest](outputs/airport-import/manifest.json) for every
inclusion, exclusion, selected runway and warning-coverage status.
**New SMAC coverage is not included in this batch.** Coimbatore and Mangaluru
remain configured. Fourteen included new airports have SMAC charts requiring
boundary validation; Agartala and Amritsar include border-clipped coverage,
and Nagpur has conflicting minima between its map and table. The UI reports
unavailable coverage rather than treating missing regions as safe. Reviewed
SMAC JSON can subsequently be placed in `outputs/airport-import/smac/<ICAO>.json`
and incorporated by the same publisher.

Validation: 401 Python tests and 8 frontend tests passed; TypeScript and the
production build passed. Each ILS profile passed a geometry-driven capture,
glide-slope interception and stable-tracking test. Live BlueSky switching checked
all 124 profiles, one aircraft, paused state, correct navigation/mode and no
simulator errors (`outputs/verification/catalogue-runtime.json`). These checks
verify the simplified exercise, not complete procedure or aircraft performance
fidelity. No paid speech-provider call was needed for this data import.


## Explicit clearance, tower handoff and marker visibility

All 73 modeled ILS airports now start in `awaiting_clearance`. A separate voice
instruction, e.g. "Air France one two three, cleared ILS approach runway two three",
arms the selected approach. Capture geometry, speed and level requirements still
apply. Wrong runway numbers/suffixes or callsigns are rejected. Non-ILS airports
remain vectoring exercises and do not accept this ILS/handoff sequence.

Coimbatore accepts handover from glide-slope capture onward and continues descending
until transfer or the configured missed-approach distance. Airports without the
distance rule retain the stable-tracking pause. The UI shows the selected tower
channel. Wrong frequencies, stations and premature handovers are rejected.
Successful transfer produces a pilot readback and ends the normal radar exercise.
Reset or airport switching removes clearance and handoff state. Heading/altitude
instructions after capture cancel automatic tracking and require fresh clearance.

`data/tower_channels.json` stores published TWR rows for 124 airports, including
source PDF path, page, verbatim extracted row, and alternate rows. Only the first
listed channel is selected for this exercise; this is not a claim about the active
operational frequency. Published hours, backup activation and multi-frequency
assignments are not simulated. `scripts/extract_tower_channels.py` regenerates the
file from cached AD 2.18 text without changing airport geometry or SMAC data.

New procedure commands use the same OpenAI endpoint and a single transcription call with live recognition context.
Their semantic results must agree before any action. Interpretation has no selected
runway/frequency context; the existing callsign normalizer is reused. The simulator
thread validates runway, channel, callsign and exercise stage before acknowledgement.
Unsupported, mixed, conditional or ambiguous procedure instructions cause no action.
There is still no typed-command input or transcript confirmation gate.

**Show approach markers**, on by default, controls published fix symbols/labels
where configured and the new 5-NM-spaced threshold-distance markers on all modeled
ILS finals. It does not hide the runway, final line, navigation aids or SMAC areas,
and does not affect capture, guidance or scoring. The choice is stored in the
browser and survives reloads and airport switching. `NM THR` means horizontal
simulator distance from the threshold: it is not a published fix or a DME reading.
Published IF/FAF markers remain those already verified in VOCB/VOML; the other
71 ILS profiles have distance markers, not a newly extracted set of published fixes.

Verification for this update: 421 Python tests, 9 frontend tests, TypeScript and
production build passed. The paid synthetic-audio check used the production voice
endpoint and actual BlueSky for Coimbatore, observing `armed -> localizer ->
glideslope -> handoff_ready -> complete`, with audible readbacks, 10.3 seconds of
stable tracking and no simulator command errors. This verifies integration, not
human microphone/accent recognition. Evidence: `outputs/verification/VOCB/result.json`.
The browser toggle and reload persistence were also checked. Run the optional paid
end-to-end check with `.venv/Scripts/python.exe scripts/verify_openai_demo.py`.


### Grouped map layers and airport-specific entry

The lower-left **Map layers** legend has grouped switches for **ILS approach**
(final line, published fixes and threshold distances), **Airport** (runway and
airport marker/name), **SMAC altitudes** (all areas and minimum labels),
**Navigation aid details** (the cyan antennas, names, frequencies and leader
lines), **Radar references** (rings, bearings and center) and **Approach area**
(the published lateral entry envelope). Other navigation fixes appear as a group
when present. Navigation aid details are hidden by default. **Hide all** and
**Show all** apply to the complete map overlay. Layer choices save per airport
in the browser using a new preference key; previous individual-item settings
are superseded. Hiding SMAC does not disable monitoring or aircraft alerts.

Entry placement no longer uses the radar scope radius. `data/entry_areas.json`
records source-linked lateral geometries from supplied AAI AD 2.17 documents
and AAI ENR 2.1 (July 2026). The importer in `scripts/build_entry_areas.py`
accepts explicit circles and straight/arc polygons and flags unsupported
borders, exclusions and conditional geometry for review. These are **lateral
entry envelopes**, not a simulation of airspace classification, vertical limits,
watch hours, agreements or a published transfer point.

`src/entry_area.py` intersects the arrival path at its configured cross-final
offset with every available published area and SMAC polygon. The aircraft starts
2 NM beyond the last crossing, including disconnected regions. SMAC is used as
an additional training-entry envelope, not as an airspace-jurisdiction boundary.
Coimbatore starts approximately 33.6 NM before RWY23 threshold, beyond SMAC;
Mangaluru starts beyond its 50 NM outer approach-area envelope. The radar view
then expands to include the entry; changing display range never moves it.

Where no usable boundary intersects the arrival path, the saved exercise start
is retained and the sidebar explicitly says that an outside-area start is not
verified. Unsupported details are recorded in the data and indicated in the UI;
a generic radius is never substituted. Run `tests/test_entry_area.py` to check
outside-boundary placement across the catalogue. Source editions are stated in
the dataset; live NOTAM/current operational completeness is not implied.

Startup, reset and airport changes use the same entry setup. Flight dynamics,
voice commands, ILS capture and tower handoff rules are unchanged. Restart the
server and refresh the browser to load the setup and built frontend.
## Missed approach exercise

Select Coimbatore and arm **Go-around on handoff** before transferring the aircraft
to tower. A successful tower handoff starts the missed approach. The console shows
the charted legs and any ATC assignments.
The selected example is **ILS Z RWY 23**, AAI AD 2 VOCB 2-107, 17 April 2025.
Default guidance follows final to the threshold, observes the first climb gate,
tracks the outbound radial, then turns to CCB. The chart speed cap is 185 KIAS.
Arrival within 0.5 NM of CCB and 100 ft of the assigned altitude transfers guidance
to the published hold. Arrival outside the altitude tolerance pauses for review.

Before the trigger, use an explicitly scoped voice instruction, for example
“Air France one two three, on missed approach fly heading two seven zero” or
“Air France one two three, on missed approach climb to seven thousand feet.”
Each instruction replaces that component for this aircraft. Ordinary approach
vectors take effect immediately. During the go-around ordinary heading, level and
speed instructions update active targets. A heading override places the lateral
path under ATC vectoring until reset and the simulator no longer scores arrival
on the published route. A controller who changes the route may also need to assign
a climb. Reset or airport change clears all assignments.

Configuration lives in `data/missed_approaches/<ICAO>.json`. The approach profile
selects a `procedure_id`; the loader requires an exact ICAO, runway end (including
suffix) and approach ID match. The same file can contain multiple runway ends and
procedure variants. Unconfigured combinations show unavailable. Add sourced
`straight`, `radial` and `direct` legs, fixes in WGS84 latitude/longitude, magnetic
radials converted to true course using the chart variation, altitude gates in feet
AMSL, turn direction and a speed cap in KIAS. Other leg types need simulator
support before data import. The Coimbatore record is a working example for SME review.

## Published holding

At Coimbatore a controller can also say “Air France one two three, cleared to
Charlie Charlie Bravo, climb to six thousand three hundred feet, hold as published.”
Start the simulation to fly to the fix. An expected further-clearance time can be
included in the transmission. The aircraft continues holding until vectored.
Level and speed instructions within holding limits preserve the pattern. A heading
releases the aircraft for vectoring and a fresh approach clearance.

The CCB pattern has a 047° magnetic inbound track, left turns, one-minute legs,
a 6,300 ft minimum and a 210 KIAS maximum. Use the **Holding patterns** map layer
to toggle the nominal racetrack. Aircraft speed and wind affect the actual track.
For another airport, add sourced timed patterns to `data/holds/<ICAO>.json`
following the VOCB example. Reference a pattern ID from a missed approach's
`hold_id` to join it automatically. Fix coordinates are WGS84, altitude is
feet AMSL, and magnetic variation is signed east-positive.

## Reviewed control areas (Coimbatore)

Coimbatore now has separate reviewed CTR/CTA volumes in
`data/control_areas/VOCB.json`, including published arcs, vertical limits and
CTR exclusions. Membership is evaluated in the simulation update loop and shown
in the Control area console panel. The Control areas map layer is toggleable.
Other airports explicitly report reviewed data unavailable until their files are
added. Worker instructions and validation commands are in
`docs/CONTROL_AREA_DATA_HANDOFF.md`.

The older `entry_areas.json` remains a lateral entry-placement model (also used
with SMAC coverage); its map layer is now labeled Entry envelope. It is not an
altitude-dependent control-area model. The new monitor does not restrict commands,
grant clearances, trigger tower handoff or change MSAW. FL limits remain uncertain
when pressure altitude is unavailable. Source editions and current limitations
are documented in the handoff guide.

