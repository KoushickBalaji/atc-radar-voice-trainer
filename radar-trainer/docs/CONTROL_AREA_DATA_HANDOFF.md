# Airport control-area data handoff

The runtime reads one reviewed file per airport from `data/control_areas/<ICAO>.json`.
Use `data/control_areas/VOCB.json` as the complete working example. Only Coimbatore
is configured in this implementation. Missing files mean **unavailable**, never
outside or uncontrolled airspace. Restart the server after adding or editing files.

## What to extract

Use AD 2.17 for CTR/ATZ and ENR 2.1 for CTA/TMA. SMAC charts describe minimum
vectoring altitudes, not airspace jurisdiction. Do not derive control boundaries
from SMAC coverage, radar range, ILS range, or an arbitrary airport-centred circle.
Check the publication edition, units, coordinates, arc direction and radius,
vertical references, exclusions, classification, and hours. Retain exact source
text and source page (one-based PDF page), edition/date, file or URL.

Top-level fields: `schema_version: 1`, `icao`, `reviewed: true`, `notes` (strings),
`areas` (nonempty list). Never set reviewed true for unresolved geometry. Keep
drafts outside `data/control_areas`, for example `outputs/control-area-review/`.

Each area requires:

- `id`: unique stable identifier within this airport; `name`: published name.
- `kind`: CTR, CTA, TMA or ATZ; `classification`: published class as a string.
- `hours`: `H24` only when published as such; otherwise retain the published text.
  Non-H24 membership is uncertain because watch-hour calendars are not modeled.
- `lower`, `upper`: objects with `reference` SFC, AMSL, FL or UNL. AMSL values
  are feet, FL values are flight levels (e.g. 145, not 14500). SFC/UNL have no value.
  Convert explicitly published metres to feet and retain original units in evidence.
  Unknown or AGL limits must remain drafts; do not convert AGL using airport elevation.
- `excludes`: IDs of other volumes in this file. Subtraction is three-dimensional:
  CTA B excludes the CTR only where its lateral AND vertical extent applies.
  Nested exclusions are unsupported. Split/restructure with documented evidence
  or leave unresolved; do not discard holes or border restrictions.
- `source`: `file` or `url`, plus `section`, page/date/edition where applicable,
  and `evidence` containing the transcribed source description. Include derivations.
- `shape`: `circle` or `polygon`, as described below.

Coordinates are WGS84 decimal `[latitude, longitude]`; south/west are negative.
These are not pixel coordinates or local nautical-mile coordinates.

Circle: `center: [lat, lon]`, `radius_nm: number`.

Polygon: `edges: [{"point": [lat,lon]}, ...]`. First edge is a starting point.
Subsequent `point` values end straight segments unless the edge also contains
`center: [lat,lon]`, `radius_nm`, and `clockwise: true|false`, in which case it
ends a circular arc from the previous point. To close with an arc, repeat the
starting point on the final arc edge. Otherwise the final segment closes straight.
Do not replace curved boundaries with straight chords. The renderer samples arcs
at at most 0.25 degrees using the stated radius and the existing local NM projection.
Arc endpoint discrepancies over 0.2 NM reject the file; this tolerance accommodates
coordinate rounding/projection, and is not operational positional accuracy.

## Validation and review

Run from `radar-trainer`:

```powershell
.venv/Scripts/python.exe scripts/validate_control_areas.py
.venv/Scripts/python.exe -m pytest tests/test_control_area.py -q
```

The loader rejects malformed identifiers, references, geometry, radii and reversed
same-reference limits. This does not establish chart accuracy: inspect the drawn
outline against the source and check representative inside/outside points, vertical
edges and exclusions. Add airport-specific tests for new reviewed data. Borders,
conditional activation, stacked classes and complex exclusions need explicit review.
Do not run the old `build_entry_areas.py` to populate these files; that parser builds
lateral entry envelopes and deliberately omits vertical limits and exclusions.

## Runtime semantics and limits

Membership updates in the existing simulation loop; no extra thread is needed.
Horizontal and vertical boundaries are included. Shared vertical limits can match
two areas. SFC assumes the simulation's airborne aircraft; this is not a terrain check.
FL bounds require a separate `pressure_alt_ft`. The adapter currently has none, so
relevant FL decisions are uncertain, rather than treating altitude AMSL as pressure
altitude. A definitive exclusion or failure of another bound can still rule an area
out. Known matches and uncertain matches are returned separately.

For each callsign, confirmed presence inside any configured volume starts exit
monitoring. The monitor projects the measured ground track, ground speed and
vertical rate for 60 simulation seconds, respecting a selected altitude ahead
on the climb or descent. A predicted interval outside all configured volumes
sets the target’s exit countdown. The radar marks that callsign and the console
lists all affected aircraft by time to exit. Starting outside, uncertain membership
and completed tower handoff are ineligible. No extra worker data is required.

The console displays membership and published limits; the Control areas map layer
shows lateral outlines (all levels together). The separate Entry envelope layer
retains older aircraft-start geometry. Neither display visibility nor membership
changes voice clearance, entry positioning, scoring, MSAW, pause, or tower handoff.
This is an airspace-awareness training feature, not an operational access decision.

## Coimbatore audit

The old model had three lateral shapes but discarded vertical limits and CTR
exclusions. Its entry placement also uses SMAC coverage. That behaviour remains
explicitly labeled as an entry envelope, not control jurisdiction.

The reviewed model uses AD 2.17, supplied PDF page 14 dated 22 January 2026:
CTR with 13 NM and 10 NM clockwise arcs, SFC–7500 ft AMSL, class D, H24.
The SFC floor follows its CTR designation; the table prints only the upper limit.
CTA A: 2000–5500 ft AMSL. CTA B: 5500 ft AMSL–FL145. Both are class D/H24
and exclude the CTR volume, from the locally cached July 2026 ENR 2.1 edition.
The ENR source text is preserved in the JSON evidence. Online revalidation was
unavailable during this audit; no claim is made that these are current operational
limits. The supplied AD PDF was extracted and visually checked.
