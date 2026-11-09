# SMAC extraction handoff for another agent

## Deliverables

Read the supplied official SMAC PDFs in `D:/ATC/Airport Layouts/` and produce
one UTF-8 JSON file per airport at:

`D:/ATC/radar-trainer/outputs/airport-import/smac/<ICAO>.json`

Each file contains ONLY the `msaw` object described below, not a complete airport
profile and not an object wrapped in an `msaw` key. Use actual ICAO codes as filenames.
Do not modify runway, ILS, aircraft, voice, or simulator code. Preserve the existing
Coimbatore and Mangaluru datasets. Do not add Bengaluru KIA or Mumbai.

Only place complete, reviewed datasets in this directory: the importer treats file
presence as readiness to enable monitoring. Store incomplete drafts and unresolved
issues separately under `outputs/airport-import/smac-review/`.

## Required JSON shape

This is a **fictional format example**, not airport data. Replace every value.

```json
{
  "schema_version": 1,
  "coordinate_reference": "WGS84",
  "altitude_unit": "ft",
  "altitude_reference": "AMSL",
  "source": {
    "file": "Airport Layouts/Airport name/XXXX-ATC-SMAC.pdf",
    "chart": "Exact printed chart identifier",
    "effective_date": "2025-04-17",
    "note": "Coverage, source datum, conversions and relevant chart notes."
  },
  "suspend_on_tracked_ils": true,
  "points": {
    "A": [12.0, 75.0],
    "B": [12.1, 75.0],
    "C": [12.1, 75.1],
    "D": [12.0, 75.1]
  },
  "regions": [
    {
      "id": "area-a",
      "minimum_ft": 3000,
      "label": [12.05, 75.05],
      "boundary": ["A", "B", "C", "D"]
    }
  ]
}
```

## Field rules

- Coordinates are numeric **[latitude, longitude]**, WGS84 decimal degrees. North
  and east positive; south and west negative. Preserve source precision and record
  the original DMS values in the review notes. Do not swap latitude and longitude.
- `minimum_ft` is the chart's vectoring minimum in feet AMSL, not obstacle elevation,
  height above the runway, an ILS intercept level, MSA-circle value, or flight level.
  Verify units/datum before conversion. Do not infer an uncertain datum.
- `points` holds named boundary vertices. Reuse identical point IDs on shared edges.
  Chart point names are preferred; otherwise use stable names and document their basis.
- Each `regions` entry is one simple, non-self-intersecting polygon with a unique
  `id`, positive minimum, and `label` coordinate inside it. `label` is only a display
  anchor and may be chosen manually; it does not affect the minimum calculation.
- `boundary` lists vertices in perimeter order. Straight edges join consecutive
  points; the last point is automatically joined to the first by a straight edge.
  Do not repeat the first point merely to close an ordinary polygon.
- `source.file` is relative to `D:/ATC`, using forward slashes. `source.chart` is
  the printed chart identifier. `effective_date` is the chart effective date in
  YYYY-MM-DD form, not download date. If not established, use null and explain why.
- `source.note` should record coverage limitations and interpretation/conversion
  details. Retain restrictive chart notes in the accompanying review document.
- `suspend_on_tracked_ils: true` matches the current trainer policy: suspend the
  vectoring-minimum check only on a captured glide slope with current geometry
  within tracking tolerances. It is an application policy, not an extracted chart
  fact. Preserve it for this batch; do not invent airport-specific inhibition logic.

## Curved boundaries

The loader supports a **clockwise** arc from the preceding point to a named endpoint:

```json
"boundary": [
  "A",
  {"to": "B", "center": [12.05, 75.05]},
  "C"
]
```

`A` and `B` must exist in `points`; `center` is [latitude, longitude]. An arc cannot
be the first boundary entry. There is no `radius_nm`, `direction`, `start`, or
`end` field in the runtime arc format. The loader derives radius from the endpoints
and interpolates between their radii in its local NM projection. For a circular arc,
both endpoints must lie on the charted radius within source/projection tolerances.
Record the published radius, centre, and derivation separately in review notes.

An arc closing the polygon must be explicit, e.g. `["A", "B", {"to":"A",
"center":[12.05,75.05]}]`. Do not encode a full circle as an arc from a point back
to itself: its sweep becomes zero. Use multiple distinct points and arcs. Check
the clockwise sweep visually: reversing endpoints can select the long arc.

For counterclockwise edges, holes, border exclusions, or disconnected coverage,
produce a faithful decomposition into supported simple regions, or mark the
dataset unresolved. Do not substitute a full circle for clipped coverage. Explicit
polygon approximations are acceptable only with a documented derivation, sampling
tolerance, and visual validation; never guess coordinates from an uncalibrated image.

## Evidence and validation supplied with each airport

Write `outputs/airport-import/smac-review/<ICAO>.md` with:

1. Source PDF, page numbers, chart ID, revision/effective date and units/datum.
2. Point table: point ID, printed coordinate or geometric definition, converted
   decimal coordinate, and how it was derived. Include arc centres/radii/bearings;
   distinguish true from magnetic bearings and document any conversion.
3. Region table: ID, published minimum, boundary order, and source evidence.
4. A rendered chart/overlay comparison showing correct boundaries and minima.
5. Test coordinates for each region interior, shared boundaries, each side of
   altitude changes, and outside coverage, with expected minima. At shared edges
   and overlaps the current monitor uses the **highest** applicable minimum.
6. Check altitude just below, exactly at, and above each minimum: warning, clear,
   clear respectively. Check no unintended gaps, overlaps or self-intersections.
7. Uncertainties, conflicts and omitted coverage. Do not choose a conflicting
   source value silently or mark an incomplete dataset ready.

Existing examples: the `msaw` objects in `data/airports/VOML.json` and
`data/airports/VOCB.json`. The implementation contract is `src/msaw.py`;
`tests/test_msaw.py` demonstrates coverage and boundary checks. JSON parsing or
successful construction alone does not establish that the geometry matches the PDF.

## Integration after review

The existing `scripts/import_airport_profiles.py` reads these standalone JSON files
and inserts them as `msaw` in the corresponding airport profile. Run from
`D:/ATC/radar-trainer` after review:

```powershell
.venv/Scripts/python.exe scripts/import_airport_profiles.py
.venv/Scripts/python.exe -m pytest -q
```

Update the catalogue/documentation to reflect the resulting coverage. Restart the
trainer because profiles are cached; inspect each new airport's purple SMAC regions
and verify runtime warning/clear/outside-coverage behavior. These final integration
checks can be performed by the main agent after extraction is delivered.

## Known unresolved cases

Pending airports: VEAT Agartala; VIAR Amritsar; VOBG Bengaluru HAL; VOVI
Bhogapuram; VEBS Bhubaneswar; VOCL Calicut; VOCI Cochin; VEGT Guwahati;
VIJP Jaipur; VILK Lucknow; VANP Nagpur; VEPT Patna; VOTR Tiruchirappalli;
VEBN Varanasi.

- Agartala (VEAT) and Amritsar (VIAR): border-clipped coverage must be preserved;
  accurate boundary data/derivation is needed.
- Nagpur (VANP): map labels and altitude table disagree. Record the conflicting
  values with evidence; do not publish until an authoritative resolution exists.

The remaining supplied SMAC charts still require extraction and validation; their
presence in the pending list is not a guarantee that no further ambiguities exist.
