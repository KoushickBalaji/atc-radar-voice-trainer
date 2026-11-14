# Adjusting Coimbatore traffic timing

Edit `data/traffic/VOCB.json`. Find the scenario by its `id`, then the aircraft by
`callsign`. Its `at_s` is the time in **simulation seconds from exercise start**
when that aircraft becomes active. It is an absolute time, not the delay after
the previous flight. Pausing stops this clock; 2× and 4× speed shorten wall-clock gaps.

Current timings:

| Scenario | Aircraft | Previous `at_s` | Current `at_s` |
| --- | --- | ---: | ---: |
| routine-23 | AFR123 | 0 | 0 |
| routine-23 | BAW452 | 10 | 20 |
| routine-23 | UAE681 | 20 | 40 |
| routine-23 | DLH908 | 40 | 70 |
| level-changeovers-23 | AFR123 | 0 | 0 |
| level-changeovers-23 | BAW452 | 10 | 20 |

This adds ten seconds to each successive gap, including the original twenty-second
gap before DLH908. For example, change UAE681's `"at_s": 40` to `"at_s": 50`
to activate it ten seconds later. Move subsequent flights too if you want to keep
their gaps unchanged. Keep the JSON commas and quotes intact.

Save, then select the scenario again (return through the briefing) to load the
edited file. Existing exercises retain the scenario they started with. Rebuild the
frontend (`npm run build` in `frontend`) as its briefing also imports this file;
for hosting, rebuild/redeploy the container. A server restart alone does not update
the built frontend.

Activation spacing is not an audio-duration guarantee: later pilot calls depend on
aircraft state and radio playback duration. Use 1× speed when evaluating radio workload.

## Transit entry calls and frequency changes

In `data/traffic/VOCB.json`, find `routine-23`, then `UAE681`:

- `initial_station`: the station addressed in the first transit position report.
  Currently `"Coimbatore Approach"`. If omitted, transits address the airport tower.
- `transfer_required`: currently `false`, so the aircraft does not request a
  frequency change and completes its transit when it exits its configured `area`.
  Set it to `true` for a transit that needs a coordinated onward transfer.
- `station` and `frequency`: the receiving unit for an onward transfer, used when
  `transfer_required` is `true`; these do not set the initial call.

The generic behaviour is implemented in `src/traffic_scenario.py` (`Overflight`
and `TrafficRun.update`). Edit the JSON for individual aircraft, and update the
scenario `brief` to match. Reload the scenario and rebuild the frontend as above.

The demo selection screen filters to `routine-23` in `frontend/src/TrainingEntry.tsx`.
The level-changeovers scenario remains in the data for later use.
