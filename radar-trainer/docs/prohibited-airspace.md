# VOP 190 monitoring

Coimbatore loads VOP 190 Arvankadu from its airport profile. Source: [AAI ENR 5.1](https://aim-india.aai.aero/eaip/eaip-v2-09-2026/eAIP/IN-ENR%205.1-en-GB.html), checked 16 November 2026. The published center is 112156N 0764548E; clockwise sectors are 060–170 degrees at 1.25 NM and 170–060 degrees at 5 NM. The prohibited volume extends from GND through 17,500 ft.

The radar always draws the red boundary, shaded interior, designation and vertical limits. Aircraft warnings appear in the HUD, Alerts filter and radar label. Amber indicates entry predicted within 60 simulated seconds; red indicates current membership. Alerts clear on leaving the volume or when the projected trajectory no longer enters it. They do not depend on map-layer visibility or approach phase.

Prediction extrapolates current ground track, ground speed and vertical speed, without anticipating commanded turns or altitude capture. It checks exact crossing times for the local-plane sector circles, radial boundaries and altitude limits, including incursions shorter than a sampling interval. The display samples arcs every 0.25 degrees. Both use the simulator's existing local NM projection. Boundaries and the ceiling are included. The simulation uses aircraft altitude in feet for the ceiling; ground is represented by the simulation's nonnegative altitude domain, with no terrain model. The shared safety alarm loops during an actual incursion or SMAC warning while connected and unpaused; predicted entry remains visual. Overlapping violations use a single alarm.

Regression coverage: `tests/test_prohibited_airspace.py` covers sectors, shared boundaries, altitude, predictive crossings, clear conditions and airport scope; the frontend AircraftHud test covers warning, escalation and clearing.

## Sulur (SLR)

The user-defined Sulur training zone is centered 7.5 NM southeast (135 degrees true) of CCB VOR/DME, parallel to VOCB RWY 23 (225.72 degrees true). Its runway is 10,000 ft long, with 4 NM clearance at each end and a total protected width of 4 NM. The resulting rectangle is approximately 9.646 NM by 4 NM. These are user-specified exercise dimensions, not a published airspace transcription.

SLR uses the same red boundary, shading, labels and predictive alerts as VOP, with a solid runway mark at its center. Its restriction is GND to **below FL30**: pressure altitude of 3,000 ft and above is outside the volume. Explicit pressure altitude takes precedence. When the field is absent, the trainer uses its standard-atmosphere simulation altitude as the FL proxy; an explicitly invalid pressure altitude is ignored. Lateral boundaries are included. Prediction checks crossings of all four rectangle edges and the altitude limits.

