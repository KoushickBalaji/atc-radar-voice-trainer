# Coimbatore departures and transfers

## MATS check

Checked the repository's **AAI Manual of Air Traffic Services, Part 1, Edition 7**,
dated 9 May 2025:

- **4.11.7.5.1–3**, printed page 4-10 (PDF page 100): route clearances, runway,
  levels and SSR codes require pilot readback; the controller checks the readback
  and corrects discrepancies.
- **4.11.7.5.4**: frequency changes are transmitted separately from instructions
  requiring readback.
- **7.9.3.1–4**, printed page 7-15 (PDF page 207): the preceding ATC clearance must
  be transmitted and acknowledged before takeoff clearance; runway readiness and
  traffic separation also apply. Reserve “take-off” for takeoff clearance/cancellation.
- **12.9.1–5**, printed page 12-10 (PDF page 330): preferably deliver the route
  clearance before startup, never during lineup/takeoff maneuvers. Route clearance
  does not authorize runway entry or takeoff.

These provisions support the sequence, but do not prescribe the SME's entire
sentence as one universal departure template. The exercise begins with the
departure stationary and omits startup, taxi and lineup. Its CCB radial clearance,
combined tower/approach position and receiving-unit arrangements are simulation
assumptions, not a claim of a published SID or letter of agreement.

## Example exchange

1. Controller: “Speedbird four five two, departure runway two three, turn left,
   establish radial one eight zero, climb to flight level zero nine zero,
   squawk zero four two one.”
2. Pilot reads back the runway, turn, CCB radial, flight level and squawk.
   The aircraft remains stationary. A complete replacement clearance can be issued.
3. Controller checks the readback, then says “Speedbird four five two, runway
   two three, cleared for takeoff.” An optional separate “readback correct” is
   accepted; it alone does not start the roll. The subsequent explicit takeoff
   clearance records verification of the preceding readback.

After rotation, guidance follows the assigned turn direction, intercepts the
CCB outbound radial and climbs to the assigned level. Radials use the chart's
magnetic/true runway bearing offset. This is a simplified local guidance model.
Later heading/direct instructions replace lateral guidance; altitude and speed
instructions preserve it. There is no preset departure route or climb level in
either Coimbatore scenario.

## Radar and radio lifecycle

- UAE681 starts with 40 NM remaining on W43 from DODSI, calls approach at CTA entry
  or no later than 35 NM from the airport, and stays on W43 through CCB, LENBO
  and UGABA. All intermediate fixes on the onward W43 branch are loaded, so
  guidance follows the changing route legs rather than extending the inbound
  radial. Controller vectors override it; level changes preserve it.
- Departures request **Kochi 128.300 MHz** near the outer CTA boundary; UAE681
  requests **HAL 127.700 MHz**. Frequencies are the user-specified scenario values.
  Departure requests use a 120-second lookahead, transit requests 300 seconds.
- The controller may transfer either flight earlier, after it is airborne/on
  frequency. A request alone does not change frequency. A validated contact
  instruction and its pilot readback model establishment on the receiving channel.
- `transferred` means radio contact has ended, not flight completion. The target
  keeps moving under its last clearance and cannot respond to reports, vectors,
  squawk changes or further transfers. It is removed only at lateral CTA B exit.
  Climbing out of a vertical volume does not erase a visible radar target.
- Exiting without transfer also removes the target and records an overdue transfer.
  The existing arrival FL130 transfer remains internal to the combined positions.

## Verification

`tests/test_departure_transit.py` covers interpretation contracts, full readback,
clearance revisions, takeoff gating, turn/radial guidance, early transfer,
post-transfer silence, boundary removal and contact/route setup. Its opt-in BlueSky
test checks actual aircraft motion after transfer and level changes on the transit.
Set `ATC_TEST_LIVE_TRAFFIC=1` to include simulator integration tests.
