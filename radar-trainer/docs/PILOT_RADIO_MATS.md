# Pilot radio behaviour and MATS references

Checked 11 November 2026 against the supplied AAI MATS Part 1, Edition 7.0,
9 May 2025. AAI web search also identifies Edition 7; no later edition was
located. The current public-documents site is JavaScript-only and the PDF
redirect could not be fetched by the web reader, so currency of every amendment
is not certified.

Official source: https://aim-india.aai.aero/sites/default/files/ais_docs/Manual%20of%20Air%20Traffic%20Services%2C%20Part-1%20Edition%207.pdf

- 12.8.1: full aircraft and ground-station callsigns when establishing contact.
- 4.17.3.1: position-report contents include identification, position, time,
  current/passing and cleared level, next position/time and ensuing point.
- 4.17.3.2: include assigned speed in position reports and initial calls after
  a frequency change. The simulator uses abbreviated surveillance check-ins,
  not a full procedural position report with invented ETAs.
- 12.9.4 and 4.11.7.5.1: read back route clearances, runway clearances,
  runway in use, altimeter settings, SSR codes, levels, headings, speeds and
  transition levels. Existing ILS, landing, takeoff and hold readbacks remain.
- 4.11.7.5.2: other instructions must be acknowledged in a way that indicates
  understanding/compliance. Roger acknowledges information; it is not a blanket
  substitute for required readbacks. Unsupported directives remain rejected.
- 4.11.7.5.4: transmit frequency changes separately from readback instructions.
- 10.1.2.4: coordinated transfer timing and local agreements apply. No general
  FL180 entry / FL130 arrival / FL140 departure rule was found.

Implementation reuses approach_radio interpretation/validation/readback,
SimManager procedure execution and snapshots, TrafficRun announcements, and
existing pilot-audio/TTS delivery. pilot_report is the shared state-to-speech
formatter for requests and check-ins. No new service or UI is required.

Supported current-data requests: level, cleared level, heading, indicated speed,
ground speed, vertical speed, position relative to the airport/sector centre,
remaining route, squawk, QNH and aircraft type. Unknown or absent data is reported
unavailable. Requests do not move aircraft. Future/conditional reporting
instructions remain unsupported and are rejected, not falsely acknowledged.

Squawk and QNH assignments are retained in per-aircraft radio state and read back.
QNH does not introduce a new pressure/altimetry physics model. Flight-level
training uses the existing standard-atmosphere BlueSky altitude representation;
this is not validation of real pressure-altitude airspace membership. No SSR code
is invented on initial contact. Direct routing uses verified airport route fixes
and the existing BlueSky LNAV route. Full arbitrary multi-fix route clearances,
ground taxi/runway-entry operations and transition-level assignment are not
newly simulated by this change; unsupported instructions cannot receive wilco.

Choose Coimbatore scenario "Level changeovers · FL180 / FL130 / FL140" for the
requested level sequence. Arrival enters at FL180, waits for an explicit descent,
requests changeover at/below FL130, and calls Coimbatore Approach only after a
separate accepted contact instruction. It remains available for vectoring.
Departure requests changeover at/above FL140 and stays until transferred.
Training Control 128.000 is explicitly fictional. These are exercise settings,
not published Coimbatore SOPs/LOAs. The existing mixed scenario keeps its
separated arrival stack and early tower-to-approach transfer.

Single-aircraft airport exercises now check in once when spawned at their
configured entry point. Mixed arrivals check in on scheduled entry; overflights
retain the existing control-volume entry trigger. No RF propagation/radio-range
model is added. Calls use stable event IDs and existing sequential audio delivery.

Runway heading (follow-up): accepts standalone "fly runway heading", "maintain
runway heading", "continue runway heading", "runway heading", and the alias
"heading runway". The existing callsign validation still applies. Interpretation
keeps this as a relative instruction; the simulation thread resolves the assigned
departure runway (including the reciprocal end) or the active exercise runway.
It uses the stored true bearing for BlueSky's true-heading command, not runway
number times ten, a bearing toward the airport, or a wind-corrected ground track.
The readback is "fly runway heading" plus callsign. A ready/rolling departure
retains this heading for liftoff without receiving takeoff clearance. Conditional,
combined, or explicit numbered-runway variants are rejected rather than partly
executed. MATS Edition 7 Appendix A, Table A-3 lists runway heading (RH).
Validation: 95 focused radio, procedure, validation and simulator tests passed;
one pre-existing opt-in flight-engine test was skipped in this focused run.
