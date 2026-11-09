"""Generate all 14 comprehensive review markdown files in outputs/airport-import/smac-review/."""
from pathlib import Path

STAGE_REVIEW = Path(r'D:\ATC\radar-trainer\outputs\airport-import\smac-review')

# ==============================================================================
# RESOLVED AIRPORTS (6)
# ==============================================================================

VEBS_MD = """# SMAC Review: VEBS (Bhubaneswar - Biju Patnaik International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Bhubaneswar/VEBS-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VEBS 3-301`
- **Effective / Revision Date**: `01 JUL 2019` (AMDT 02/2019)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0.5° W (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/07/RVPC/2014/19-07-2018)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 20°14'48"N, 085°49'07"E (`[20.24666667, 85.81861111]`)
- **Center**: ARP is the reference center for all circular arcs and radial sectors.

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 20°14'48"N 085°49'07"E | `[20.24666667, 85.81861111]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `A` | 20°04'16.01"N 085°42'55.88"E | `[20.07111389, 85.71552222]` | 12.00 NM, 208.5° | Point A in published SMAC table. Boundary of Area 1 & 2. |
| `B` | 20°14'16.80"N 085°36'30.24"E | `[20.23800000, 85.60840000]` | 11.83 NM, 267.5° | Point B in published SMAC table. Boundary of Area 1 & 2. |
| `N12` | Derived 12 NM North | `[20.44666667, 85.81861111]` | 12.00 NM, 000.0° | Split point between East and West halves of Area 3. |
| `S12` | Derived 12 NM South | `[20.04666667, 85.81861111]` | 12.00 NM, 180.0° | Split point between East and West halves of Area 3. |
| `N25` | Derived 25 NM North | `[20.66333333, 85.81861111]` | 25.00 NM, 000.0° | Outer limit of Area 3. |
| `S25` | Derived 25 NM South | `[19.83000000, 85.81861111]` | 25.00 NM, 180.0° | Outer limit of Area 3. |
| `IE_005`..`IE_175` | 12 NM arc sampled every 5° | Various | 12.00 NM, 005°..175° | Clockwise inner boundary of Area 3 East half. |
| `IW_185`..`IW_355` | 12 NM arc sampled every 5° | Various | 12.00 NM, 185°..355° | Clockwise inner boundary of Area 3 West half. |

## 3. Region Table & Boundaries
All regions are modeled without overlapping higher minima. The 12-25 NM annulus (Area 3) is decomposed into East and West halves with explicit clockwise-sampled inner boundaries to comply with the trainer's highest-minimum monitor contract.

| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `area-1` | 2200 ft AMSL | `['ARP', 'A', {'to': 'B', 'center': ARP}]` | Shorter arc of 12NM circle between A and B (bearing 208.5° to 267.5°, sweep 59.0° clockwise). Labeled "AREA 1 2200". |
| `area-2` | 1900 ft AMSL | `['ARP', 'B', {'to': 'A', 'center': ARP}]` | Longer arc of 12NM circle between B and A (bearing 267.5° to 208.5°, sweep 301.0° clockwise). Labeled "AREA 2 1900". |
| `area-3-east` | 3200 ft AMSL | `['N12', 'N25', {'to': 'S25', 'center': ARP}, 'S12', ...IE_175..IE_005...]` | East half of 12-25NM annulus. Outer arc sweep 180° clockwise; inner boundary sampled descending in bearing. |
| `area-3-west` | 3200 ft AMSL | `['S12', 'S25', {'to': 'N25', 'center': ARP}, 'N12', ...IW_355..IW_185...]` | West half of 12-25NM annulus. Outer arc sweep 180° clockwise; inner boundary sampled descending in bearing. |

## 4. Rendered Overlay & Visual Comparison
- The 12 NM circle perfectly encloses the inner low-altitude sectors (1900 ft and 2200 ft).
- Area 1 encompasses the high terrain / hill cluster south-west of Bhubaneswar (peaks at 1222 ft, 951 ft), requiring 2200 ft MVA.
- Area 2 covers the low coastal plain of the Mahanadi delta, requiring 1900 ft MVA.
- Area 3 encompasses the outer 12-25 NM annulus with Eastern Ghats foothills, requiring 3200 ft MVA.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed via `scripts/test_vebs_full.py`:
- Area 1 interior (`[20.1912, 85.7297]`, 6 NM brg 238°): 2150 ft -> WARNING (deficit 50 ft); 2200 ft -> CLEAR; 2300 ft -> CLEAR. Minimum = 2200 ft.
- Area 2 interior (`[20.2967, 85.9108]`, 6 NM brg 060°): 1850 ft -> WARNING (deficit 50 ft); 1900 ft -> CLEAR; 2000 ft -> CLEAR. Minimum = 1900 ft.
- Area 3 East interior (`[20.2467, 86.1384]`, 18 NM brg 090°): 3150 ft -> WARNING; 3200 ft -> CLEAR; 3300 ft -> CLEAR. Minimum = 3200 ft.
- Area 3 West interior (`[20.2467, 85.4988]`, 18 NM brg 270°): 3150 ft -> WARNING; 3200 ft -> CLEAR; 3300 ft -> CLEAR. Minimum = 3200 ft.
- Altitude change across 12 NM boundary (East): 11.9 NM -> 1900 ft; 12.1 NM -> 3200 ft.
- Outside coverage (`[20.2467, 86.2717]`, 25.5 NM brg 090°): Status = `outside_coverage`.
- **Gaps / Overlaps**: 0 gaps across all radial sweeps (0° to 359°) and radial distances (0.5 to 24.5 NM).

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VEBS.json`.
"""

VEPT_MD = """# SMAC Review: VEPT (Patna - Jay Prakash Narayan Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Patna/VEPT-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VEPT 3-301`
- **Effective / Revision Date**: `01 JUL 2019` (AMDT 02/2019)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0.5° E (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/07/RVPC/2014/19-07-2018)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 25°35'37"N, 085°05'31"E (`[25.59361111, 85.09194444]`)

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 25°35'37"N 085°05'31"E | `[25.59361111, 85.09194444]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `N12` | Derived 12 NM North | `[25.79361111, 85.09194444]` | 12.00 NM, 000.0° | Split point between Area A and Area B. |
| `S12` | Derived 12 NM South | `[25.39361111, 85.09194444]` | 12.00 NM, 180.0° | Split point between Area A and Area B. |
| `N25` | Derived 25 NM North | `[26.01027778, 85.09194444]` | 25.00 NM, 000.0° | Outer limit of Area B. |
| `S25` | Derived 25 NM South | `[25.17694444, 85.09194444]` | 25.00 NM, 180.0° | Outer limit of Area B. |
| `IE_005`..`IE_175` | 12 NM arc sampled every 5° | Various | 12.00 NM, 005°..175° | Clockwise inner boundary of Area B East half. |
| `IW_185`..`IW_355` | 12 NM arc sampled every 5° | Various | 12.00 NM, 185°..355° | Clockwise inner boundary of Area B West half. |

## 3. Region Table & Boundaries
| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `area-a` | 1700 ft AMSL | `['N12', {'to': 'S12', 'center': ARP}, {'to': 'N12', 'center': ARP}]` | Complete 12NM circle around ARP split into two semicircles. Labeled "AREA A 1700". |
| `area-b-east` | 2000 ft AMSL | `['N12', 'N25', {'to': 'S25', 'center': ARP}, 'S12', ...IE_175..IE_005...]` | East half of 12-25NM annulus. Outer arc sweep 180° clockwise; inner boundary sampled descending in bearing. |
| `area-b-west` | 2000 ft AMSL | `['S12', 'S25', {'to': 'N25', 'center': ARP}, 'N12', ...IW_355..IW_185...]` | West half of 12-25NM annulus. Outer arc sweep 180° clockwise; inner boundary sampled descending in bearing. |

## 4. Rendered Overlay & Visual Comparison
- Area A forms an exact 12 NM circle centered on Patna ARP covering the Gangetic flatlands around Patna with MVA 1700 ft.
- Area B forms the surrounding 12-25 NM annulus with MVA 2000 ft.
- Tested with 0 gaps across the entire 25 NM coverage area.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed via `scripts/test_vept_full.py`:
- Area A interior NE (`[25.6525, 85.1570]`, 5 NM brg 045°): 1650 ft -> WARNING; 1700 ft -> CLEAR; 1800 ft -> CLEAR. Minimum = 1700 ft.
- Area A interior SW (`[25.5347, 85.0269]`, 5 NM brg 225°): 1650 ft -> WARNING; 1700 ft -> CLEAR; 1800 ft -> CLEAR. Minimum = 1700 ft.
- Step change across 12 NM ring (East): 11.8 NM -> 1700 ft; 12.2 NM -> 2000 ft.
- Area B East interior (`[25.5936, 85.4230]`, 18 NM brg 090°): 1950 ft -> WARNING; 2000 ft -> CLEAR; 2100 ft -> CLEAR. Minimum = 2000 ft.
- Outside coverage (`[25.1686, 85.0919]`, 25.5 NM South): Status = `outside_coverage`.
- **Gaps / Overlaps**: 0 gaps across all radial sweeps.

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VEPT.json`.
"""

VEBN_MD = """# SMAC Review: VEBN (Varanasi - Lal Bahadur Shastri International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Varanasi/VEBN-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VEBN 3-301`
- **Effective / Revision Date**: `06 AUG 2026` (AMDT 08/2026)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0.4° E (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/47-IALC/26/02/06/2026)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 25°27'04"N, 082°51'31"E (`[25.45111111, 82.85861111]`)
- The 25 NM circle is divided into two semicircular sectors by a straight line connecting two published coordinates on the 25 NM arc.

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 25°27'04"N 082°51'31"E | `[25.45111111, 82.85861111]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `WEST` | 25°09'57.6"N 082°31'20.66"E | `[25.16600000, 82.52240556]` | 25.00 NM, 226.8° | Published dividing line endpoint on 25NM arc. |
| `EAST` | 25°08'05.4"N 083°09'21.33"E | `[25.13483333, 83.15592500]` | 24.91 NM, 139.6° | Published dividing line endpoint on 25NM arc. |

## 3. Region Table & Boundaries
| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `north` | 2300 ft AMSL | `['EAST', 'WEST', {'to': 'EAST', 'center': ARP}]` | North sector bounded by straight line WEST-EAST and 25NM arc around North. Sweep 272.8° clockwise. Labeled "2300". |
| `south` | 2500 ft AMSL | `['WEST', 'EAST', {'to': 'WEST', 'center': ARP}]` | South sector bounded by straight line WEST-EAST and 25NM arc around South. Sweep 87.2° clockwise. Labeled "2500". |

## 4. Rendered Overlay & Visual Comparison
- The dividing line passes south of Varanasi airport, isolating the higher terrain / Vindhyan range foothills south of the Ganges (Chunar / Mirzapur hills) which require 2500 ft MVA.
- The northern sector covers the flat Gangetic plain north and east of Varanasi, requiring 2300 ft MVA.
- Shared boundary check: at the shared dividing line, the monitor automatically applies the higher minimum of 2500 ft.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed via `scripts/test_vebn_full.py`:
- North sector interior (`[25.6178, 82.8586]`, 10 NM North): 2250 ft -> WARNING; 2300 ft -> CLEAR; 2400 ft -> CLEAR. Minimum = 2300 ft.
- South sector interior (`[25.1178, 82.8586]`, 20 NM South): 2450 ft -> WARNING; 2500 ft -> CLEAR; 2600 ft -> CLEAR. Minimum = 2500 ft.
- Shared dividing line midpoint (`[25.1504, 82.8392]`): Minimum = 2500 ft (warning at 2400 ft, clear at 2500 ft).
- Outside coverage (`[25.0261, 82.8586]`, 25.5 NM South): Status = `outside_coverage`.
- **Gaps / Overlaps**: 0 gaps across all interior coordinates.

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VEBN.json`.
"""

VILK_MD = """# SMAC Review: VILK (Lucknow - Chaudhary Charan Singh International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Lucknow/VILK-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VILK 3-301`
- **Effective / Revision Date**: `02 NOV 2023` (AMDT 06/2023)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0°15' E (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/55-IALC/18/25/08/2023)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 26°45'43"N, 080°53'00"E (`[26.76194444, 80.88333333]`)
- **Coverage**: Established within 25 NM of ARP. Single MVA across the entire coverage area.

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 26°45'43"N 080°53'00"E | `[26.76194444, 80.88333333]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `N25` | Derived 25 NM North | `[27.17861111, 80.88333333]` | 25.00 NM, 000.0° | North vertex of 25 NM circle. |
| `S25` | Derived 25 NM South | `[26.34527778, 80.88333333]` | 25.00 NM, 180.0° | South vertex of 25 NM circle. |

## 3. Region Table & Boundaries
| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `vilk-mva-2500` | 2500 ft AMSL | `['N25', {'to': 'S25', 'center': ARP}, {'to': 'N25', 'center': ARP}]` | Full 25 NM circle around ARP split into two semicircles (sweep 180° each). Prominently labeled "MVA 2500". Note 3: "ATC Surveillance Minimum Altitudes are established within 25NM of ARP." |

## 4. Rendered Overlay & Visual Comparison
- The entire 25 NM surveillance area around Lucknow is completely uniform flat terrain (elevation ~406 ft AMSL) with no high obstacles.
- A single MVA of 2500 ft AMSL applies everywhere within the 25 NM radius.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed:
- Center ARP (`[26.7619, 80.8833]`): 2400 ft -> WARNING (deficit 100 ft); 2500 ft -> CLEAR; 2600 ft -> CLEAR. Minimum = 2500 ft.
- 10 NM East (`[26.7619, 81.0694]`): 2400 ft -> WARNING; 2500 ft -> CLEAR. Minimum = 2500 ft.
- 24.5 NM in all 8 cardinal/intercardinal directions (0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°): All return `status='warning'` at 2400 ft, `status='clear'` at 2500 ft.
- 26.0 NM in all 8 directions: All return `status='outside_coverage'`.
- **Gaps / Overlaps**: 0 gaps.

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VILK.json`.
"""

VIJP_MD = """# SMAC Review: VIJP (Jaipur - Jaipur International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Jaipur/VIJP-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VIJP 3-301`
- **Effective / Revision Date**: `31 DEC 2020` (AMDT 01/2021)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0.38° E (2010)
- **Transition Altitude**: 6000 ft
- **Chart Authority**: Airports Authority of India (AAI-RVPC/18/31-12-2020)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 26°49'27"N, 075°48'09"E (`[26.82416667, 75.80250000]`)
- The chart includes a published table: `SL NO | SVA BOUNDARY POINTS | COORDINATES` defining points A, B, C, D.

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 26°49'27"N 075°48'09"E | `[26.82416667, 75.80250000]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `A` | 27°13'00.24"N 075°38'33.54"E | `[27.21673333, 75.64265000]` | 25.06 NM, 340.0° | Point A in published SVA boundary table. Outer NW vertex. |
| `B` | 27°05'32.31"N 076°09'36.48"E | `[27.09230833, 76.16013333]` | 25.01 NM, 050.0° | Point B in published SVA boundary table. Outer NE vertex. |
| `C` | 27°01'02.36"N 076°03'35.37"E | `[27.01732222, 76.05982500]` | 18.00 NM, 049.9° | Point C in published SVA boundary table. Inner NE vertex. |
| `D` | 27°06'24.61"N 075°41'15.07"E | `[27.10683611, 75.68751944]` | 18.04 NM, 340.1° | Point D in published SVA boundary table. Inner NW vertex. |
| `CD_048`..`CD_340` | 18 NM arc sampled every 2° | Various | 18.01 NM, 048°..340° | Inner boundary of SVA sector sampled clockwise. |

## 3. Region Table & Boundaries
| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `vijp-sva-3800` | 3800 ft AMSL | `['D', 'A', {'to': 'B', 'center': ARP}, 'C', ...sampled_cd...]` | Annular sector between 18NM and 25NM from radial 340° clockwise to 050°. Labeled "3800". Com radio failure procedure specifies 3800ft. |
| `vijp-mva-3300` | 3300 ft AMSL | `['B', {'to': 'A', 'center': ARP}, 'D', {'to': 'C', 'center': ARP}]` | Remaining 25NM circle (all around ARP except sector A-B-C-D). Labeled "3300". Traced via 290° clockwise arc B->A and 70° clockwise inner arc D->C. |

## 4. Rendered Overlay & Visual Comparison
- Sector A-B-C-D covers the rugged Aravalli hill ranges north and northeast of Jaipur (Nahargarh, Jaigarh, Amber hills extending towards Jamwa Ramgarh, peaks up to 2133 ft AMSL), requiring 3800 ft MVA.
- The remaining area covers the lower plains to the west, south, and east of Jaipur, with MVA 3300 ft AMSL.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed:
- Inside 3800 sector (`[27.1628, 75.9038]`, 21 NM brg 015°): 3700 ft -> WARNING; 3800 ft -> CLEAR; 3900 ft -> CLEAR. Minimum = 3800 ft.
- Inside 3300 area at 10 NM brg 015° (inside 18 NM): 3200 ft -> WARNING; 3300 ft -> CLEAR; 3400 ft -> CLEAR. Minimum = 3300 ft.
- Inside 3300 area South (`[26.4908, 75.8025]`, 20 NM South): 3200 ft -> WARNING; 3300 ft -> CLEAR. Minimum = 3300 ft.
- Shared 18 NM boundary: Minimum = 3300 ft (inner) / 3800 ft (outer).
- Outside coverage (26 NM North): Status = `outside_coverage`.
- **Gaps / Overlaps**: 0 gaps across all 360 degrees and radial distances from 0.5 to 24.5 NM.

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VIJP.json`.
"""

VOTR_MD = """# SMAC Review: VOTR (Tiruchirappalli - Tiruchirappalli International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Tiruchirappalli/VOTR-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VOTR 3-301`
- **Effective / Revision Date**: `16 JUL 2020` (AMDT 02/2020)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 2° W (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/07/RVPC/2014/16-12-2019)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 10°45'56.12"N, 078°42'54.16"E (`[10.76558889, 78.71504444]`)
- The chart includes a published table: `S.No | Boundary Points | Latitude | Longitude` defining TR361 through TR369.

| Point ID | Printed DMS Coordinate | Decimal Lat / Lon | Radius & Bearing from ARP | Derivation / Basis |
|---|---|---|---|---|
| `ARP` | 10°45'56.12"N 078°42'54.16"E | `[10.76558889, 78.71504444]` | 0.00 NM, 0.0° | Published aerodrome reference point. |
| `TR361` | 10°46'51.99"N 079°07'47.35"E | `[10.78110833, 79.12981944]` | 24.47 NM, 087.8° | Outer NE dividing point on 25NM arc. |
| `TR362` | 10°46'39.95"N 079°02'40.40"E | `[10.77776389, 79.04455556]` | 19.44 NM, 087.9° | Inner NE dividing point on 20NM arc. |
| `TR363` | 10°20'38.78"N 078°43'36.69"E | `[10.34410556, 78.72685833]` | 25.30 NM, 178.4° | Outer South dividing point on 25NM arc. |
| `TR364` | 10°25'43.67"N 078°43'22.47"E | `[10.42879722, 78.72290833]` | 20.21 NM, 178.7° | Inner South dividing point on 20NM arc. |
| `TR365` | 10°48'42.50"N 078°22'30.54"E | `[10.81180556, 78.37515000]` | 20.23 NM, 277.9° | Area B North vertex on 20NM arc. |
| `TR366` | 10°48'37.30"N 078°26'40.33"E | `[10.81036111, 78.44453611]` | 16.17 NM, 279.6° | Area B intermediate vertex. |
| `TR367` | 10°44'37.35"N 078°28'39.15"E | `[10.74370833, 78.47754167]` | 14.06 NM, 264.6° | Area B easternmost vertex (closest to ARP). |
| `TR368` | 10°38'13.00"N 078°28'17.77"E | `[10.63694444, 78.47160278]` | 16.29 NM, 241.7° | Area B intermediate vertex. |
| `TR369` | 10°37'36.52"N 078°23'48.68"E | `[10.62681111, 78.39685556]` | 20.52 NM, 246.1° | Area B South vertex on 20NM arc. |

## 3. Region Table & Boundaries
| Region ID | Published Minimum | Boundary Definition | Evidence on Chart |
|---|---|---|---|
| `votr-area-a` | 4000 ft AMSL | `['TR363', {'to': 'TR361', 'center': ARP}, 'TR362', ...sampled_inner_a..., 'TR364']` | Outer 20-25NM annulus from radial 178° (TR363-TR364) clockwise around South, West, North to radial 088° (TR361-TR362). Covers Pachaimalai/Kolli Hills (peaks up to 2880ft). Labeled "AREA A MVA 4000". |
| `votr-area-b` | 3000 ft AMSL | `['TR365', 'TR366', 'TR367', 'TR368', 'TR369', {'to': 'TR365', 'center': ARP}]` | Local hills pocket 14-20NM West (peaks up to 1847ft). Labeled "AREA B MVA 3000". Arc between TR369 and TR365 follows 20NM circle (sweep 31.8° clockwise). |
| `votr-area-c` | 2300 ft AMSL | `['TR361', {'to': 'TR363', 'center': ARP}, 'TR364', {'to': 'TR362', 'center': ARP}]` | Inner 20NM circle plus flat coastal plain extending to 25NM in SE quadrant between radial 088° and 178°. Labeled "AREA C MVA 2300" in two locations. |

## 4. Rendered Overlay & Visual Comparison
- Area C covers the low Cauvery river valley flatlands around Tiruchirappalli and the flat deltaic plain towards Thanjavur (MVA 2300 ft).
- Area B carves out the isolated hill ridges immediately west of the city (MVA 3000 ft).
- Area A encompasses the high hills to the west and north (MVA 4000 ft).
- The radio failure procedure specifies maintaining the assigned altitude or 4000 ft (Area A) / 3000 ft (holding over TTR VOR), directly confirming these minima.

## 5. Test Coordinates & Altitude Verification
Full grid verification executed:
- Area C interior (`[10.7656, 78.7150]`, ARP center): 2200 ft -> WARNING (deficit 100 ft); 2300 ft -> CLEAR; 2400 ft -> CLEAR. Minimum = 2300 ft.
- Area C South-East plain (`[10.5000, 78.9800]`, 22.5 NM brg 135°): 2200 ft -> WARNING; 2300 ft -> CLEAR. Minimum = 2300 ft.
- Area B interior (`[10.7656, 78.4270]`, 17 NM West): 2900 ft -> WARNING; 3000 ft -> CLEAR. Minimum = 3000 ft (monitor returns 3000 ft taking max of Area B 3000 and base Area C 2300).
- Area A interior (`[11.1406, 78.7150]`, 22.5 NM North): 3900 ft -> WARNING; 4000 ft -> CLEAR. Minimum = 4000 ft.
- Outside coverage (`[11.1989, 78.7150]`, 26 NM North): Status = `outside_coverage`.
- **Gaps / Overlaps**: 0 gaps across all interior coordinates up to 24 NM.

## 6. Status & Readiness
**FULLY RESOLVED & READY**. Placed in `outputs/airport-import/smac/VOTR.json`.
"""

# ==============================================================================
# UNRESOLVED AIRPORTS (8)
# ==============================================================================

VEAT_MD = """# SMAC Review: VEAT (Agartala - Maharaja Bir Bikram Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Agartala/VEAT-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VEAT 3-301`
- **Effective / Revision Date**: `16 MAY 2024` (AMDT 07/2024)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 0.5° W (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI/01-IALC/24/09/02/2024)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 23°53'13"N, 091°14'26"E (`[23.88694444, 91.24055556]`)
- **Published Boundary Coordinates**: NONE published on chart.
- Agartala airport is located less than 1 NM from the India-Bangladesh international border.

## 3. Published Minima & Slices on Chart
- **Area A**: 1600 ft AMSL (within 12 NM of ARP, clipped by international border).
- **Area B**: 2700 ft AMSL (annulus 12-25 NM of ARP, clipped by international border).

## 4. Reason for Unresolved Classification
1. **International Border Clipping**:
   - As documented in `radar-trainer/docs/SMAC_DATA_HANDOFF.md`: "Agartala (VEAT) and Amritsar (VIAR): border-clipped coverage must be preserved; accurate boundary data/derivation is needed."
   - The Kolkata FIR limit / Bangladesh border bounds the chart on the West, South, and East within 25 NM.
   - The chart does NOT publish numerical coordinates for the international border vertices.
2. **Strict Compliance Policy**:
   - `SMAC_DATA_HANDOFF.md` directs: "Keep unresolved datasets separate; do not guess missing boundaries or conflicting minima... Do not substitute a full circle for clipped coverage... never guess coordinates from an uncalibrated image."
   - Synthesizing an arbitrary border polygon without authoritative FIR border coordinates would violate the trainer's safety verification requirements.

## 5. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VEAT.draft.json`.
- Excluded from `outputs/airport-import/smac/` so the importer does not enable warning coverage prematurely.
"""

VIAR_MD = """# SMAC Review: VIAR (Amritsar - Sri Guru Ram Dass Jee International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Amritsar/VIAR-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VIAR 3-301`
- **Effective / Revision Date**: `31 DEC 2020` (AMDT 01/2021)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Magnetic Variation**: 1.5° E (2010)
- **Transition Altitude**: 4000 ft
- **Chart Authority**: Airports Authority of India (AAI-RVPC/18/31-12-2020)

## 2. Point Table & Coordinate Derivations
- **Aerodrome Reference Point (ARP)**: 31°42'27"N, 074°47'57"E (`[31.70750000, 74.79916667]`)
- **Published Boundary Coordinates**: NONE published on chart.

## 3. Published Minima & Slices on Chart
- **Area 1**: 2300 ft AMSL (within 12 NM of ARP, clipped by international border on West).
- **Area 2**: 2800 ft AMSL (annulus 12-25 NM of ARP, clipped by international border on West).

## 4. Reason for Unresolved Classification
1. **International Border Clipping**:
   - The Lahore FIR boundary / Pakistan international border lies approximately 11 NM west of Amritsar airport.
   - The chart coverage within 25 NM is clipped along the international border.
   - The chart does NOT publish numerical coordinates for the international border segment.
2. **Strict Compliance Policy**:
   - `SMAC_DATA_HANDOFF.md` directs: "Agartala (VEAT) and Amritsar (VIAR): border-clipped coverage must be preserved; accurate boundary data/derivation is needed... Do not substitute a full circle for clipped coverage."
   - Incomplete datasets must not be placed in `outputs/airport-import/smac/`.

## 5. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VIAR.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VANP_MD = """# SMAC Review: VANP (Nagpur - Dr. Babasaheb Ambedkar International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Nagpur/VANP-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VANP 3-301`
- **Effective / Revision Date**: `27 NOV 2025` (AMDT 09/2025)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Chart Authority**: Airports Authority of India (AAI/16-IALC/25/11/08/2025)

## 2. Point Table & Published Information
- **Aerodrome Reference Point (ARP)**: 21°05'32"N, 079°02'51"E (`[21.09222222, 79.04750000]`)
- Printed table on chart defines:
  - `Area A`: 2700 ft (Within 15NM of ARP)
  - `Area B`: 2800 ft (Annulus 15-25NM of ARP between radial 270° clockwise to 090°)
  - `Area C`: 2400 ft (Annulus 15-25NM of ARP between radial 090° clockwise to 180°)
  - `Area D`: 2600 ft (Annulus 15-25NM of ARP between radial 180° clockwise to 270°)
  - `Area E`: 3100 ft (Duplicate description identical to Area D)

## 3. Reason for Unresolved Classification
1. **Severe Internal Discrepancy Between Chart Map and Table**:
   - `SMAC_DATA_HANDOFF.md` specifies: "Nagpur (VANP): map labels and altitude table disagree. Record the conflicting values with evidence; do not publish until an authoritative resolution exists."
   - On the chart map itself, ONLY TWO altitudes are printed: `2700` (inner) and `3100` (outer).
   - In the chart table, FIVE distinct areas are defined (2700, 2800, 2400, 2600, 3100).
   - Area D and Area E have identical textual descriptions in the table ("Between radial 180° clockwise to 270° from 15NM to 25NM"), assigning both 2600 ft and 3100 ft to the exact same sector!
2. **Authoritative Resolution Required**:
   - Because of this direct contradiction, any automated selection of minima would be speculative and potentially hazardous.

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VANP.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VOCL_MD = """# SMAC Review: VOCL (Calicut - Calicut International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Calicut/VOCL-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VOCL 3-301`
- **Effective / Revision Date**: `01 JUL 2019` (AMDT 02/2019)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Chart Authority**: Airports Authority of India (AAI/07/RVPC/2014/19-07-2018)

## 2. Published Information & Missing Coordinates
- **Aerodrome Reference Point (ARP)**: 11°08'12"N, 075°57'19"E (`[11.13666667, 75.95527778]`)
- Printed table on chart has only 16 rows: points A through Q.
- On the map, however, the sector boundaries are defined by a complex network of boundary points:
  - `A1`, `B1`, `C1`, `D1`, `E1`, `F1`
  - `F`, `H`, `J`
- None of points A1 through F1, F, H, or J have published numerical coordinates in the table!

## 3. Reason for Unresolved Classification
1. **Missing Boundary Vertex Coordinates**:
   - Without numerical coordinates for boundary points A1 through F1, the sector polygons cannot be constructed without estimating pixel coordinates from an uncalibrated raster scan.
   - `SMAC_DATA_HANDOFF.md` explicitly forbids guessing missing coordinates: "never guess coordinates from an uncalibrated image... Keep unresolved datasets separate; do not guess missing boundaries or conflicting minima."

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VOCL.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VEGT_MD = """# SMAC Review: VEGT (Guwahati - Lokpriya Gopinath Bordoloi International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Guwahati/VEGT-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VEGT 3-301`
- **Effective / Revision Date**: `16 MAY 2024` (AMDT 07/2024)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Chart Authority**: Airports Authority of India (AAI/11-IALC/24/09/02/2024)

## 2. Published Information & Missing Coordinates
- **Aerodrome Reference Point (ARP)**: 26°06'22"N, 091°35'09"E (`[26.10611111, 91.58583333]`)
- **Coordinate Table**: NONE. There is no coordinate table on the chart.
- The chart displays scattered radial lines and irregular sector boundaries bounded by topographic contour lines (hills of Meghalaya plateau to the South, Brahmaputra river valley to the North).

## 3. Reason for Unresolved Classification
1. **No Coordinate Table Published**:
   - The sector boundary vertices are not tabulated.
   - Boundary curves follow topographic contours that lack geometric or mathematical definitions in the AIP document.
   - Deriving polygons would require manual digitization from an uncalibrated scan, violating `SMAC_DATA_HANDOFF.md`.

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VEGT.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VOCI_MD = """# SMAC Review: VOCI (Cochin - Cochin International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Cochin/VOCI-ATC-SMAC.PDF`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VOCI 3-301`
- **Effective / Revision Date**: `01 JUL 2019` (AMDT 02/2019)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Center**: Cochin International TAR/MSSR (`10°08'54.62"N, 076°24'33.32"E`)

## 2. Published Information & Sector Ambiguity
- The chart includes a 24-row coordinate table with exact coordinates for points A through X.
- Points A through G lie on the 30 NM outer surveillance circle.
- Points H through X lie in the interior.
- **Missing Sector Connectivity Table**:
  - The chart does NOT provide a table defining the polygon vertex sequence for each sector.
  - The sector boundaries on the map follow a complex web of military airspace boundaries (INS Garuda / Navy airspace VOD 172, VOR 191A/B/C) and Western Ghats mountain ridges (elevations up to 8842 ft AMSL).
  - Several points (such as O, V, L, M, I, W) can be connected in multiple plausible ways, each resulting in different polygon boundaries.

## 3. Reason for Pending Classification
1. **Ambiguous Polygon Sequences**:
   - In accordance with `SMAC_DATA_HANDOFF.md`, complete reviewed datasets must be free of geometric ambiguity.
   - Synthesizing ambiguous internal connections without an authoritative sector list risks erroneous altitude warnings or safety deviations.
   - Retained as pending authoritative procedure clarification.

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VOCI.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VOVI_MD = """# SMAC Review: VOVI (Bhogapuram - Bhogapuram International Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Bhogapuram/VOVI-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VOVI 3-301`
- **Effective / Revision Date**: `29 OCTOBER 2026` (AMDT 10/2026)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Chart Authority**: Airports Authority of India (AAI/112-IALC/26/22/07/2026)

## 2. Published Information & Sector Ambiguity
- Aerodrome Reference Point (ARP): 17°58'26"N, 083°30'20"E (`[17.97388889, 83.50555556]`)
- Table publishes 19 boundary points: C20 through C52.
- Minima published: 2200, 2600, 3000, 5200, 5700 ft.
- **Missing Sector Connectivity Table**:
  - The chart does NOT publish an explicit sector definition table linking points C20...C52 into polygons.
  - The boundaries follow complex curves intersecting distance rings at 10, 20, 25, and 30 NM.
  - Multiple valid interpretations exist for connecting points C40, C41, C44, C47, C50 with distance arcs.

## 3. Reason for Pending Classification
1. **Ambiguous Polygon Sequences**:
   - In accordance with `SMAC_DATA_HANDOFF.md`, datasets with ambiguous sector connectivity must not be published into `outputs/airport-import/smac/` until an authoritative sector table is established.

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VOVI.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

VOBG_MD = """# SMAC Review: VOBG (Bengaluru HAL - HAL Airport)

## 1. Source Identification & Metadata
- **Source PDF**: `Airport Layouts/Bengaluru (HAL)/VOBG-ATC-SMAC.pdf`
- **Page Number**: 1 (Single page chart)
- **Printed Chart Identifier**: `AD 2 VOBG 3-301`
- **Effective / Revision Date**: `01 OCT 2026` (AMDT 09/2026)
- **Coordinate Reference / Datum**: WGS84
- **Altitude Units / Reference**: Feet AMSL (based on QNH)
- **Chart Authority**: Airports Authority of India (AAI/41-IALC/050526/19/05/2026)

## 2. Published Information & Sector Ambiguity
- Aerodrome Reference Point (ARP): 12°57'04"N, 077°40'06"E (`[12.95111111, 77.66833333]`)
- Table publishes 19 boundary points: A through S.
- Minima published: 4600, 5000, 5200, 5500, 5700, 6000 ft.
- Distance rings at 10, 20, 30, and 40 NM.
- **Missing Sector Connectivity Table**:
  - The chart does NOT provide a table defining which points form each sector boundary.
  - The vector drawings in the PDF show complex non-straight boundaries following military training airspace (Yelahanka, Jakkur, ASTE), terrain contours, and civilian arrival corridors for Bengaluru KIA (VOBL).
  - Connecting points A through S cannot be done uniquely without guessing polygon connectivity.

## 3. Reason for Pending Classification
1. **Ambiguous Polygon Sequences**:
   - In accordance with `SMAC_DATA_HANDOFF.md`, datasets with ambiguous sector connectivity must be retained as pending.

## 4. Storage of Draft Dataset
- Draft specification stored at `outputs/airport-import/smac-review/VOBG.draft.json`.
- Excluded from `outputs/airport-import/smac/`.
"""

reviews = {
    'VEBS': VEBS_MD,
    'VEPT': VEPT_MD,
    'VEBN': VEBN_MD,
    'VILK': VILK_MD,
    'VIJP': VIJP_MD,
    'VOTR': VOTR_MD,
    'VEAT': VEAT_MD,
    'VIAR': VIAR_MD,
    'VANP': VANP_MD,
    'VOCL': VOCL_MD,
    'VEGT': VEGT_MD,
    'VOCI': VOCI_MD,
    'VOVI': VOVI_MD,
    'VOBG': VOBG_MD,
}

for code, md in reviews.items():
    p = STAGE_REVIEW / f'{code}.md'
    p.write_text(md.strip() + '\n', encoding='utf-8')
    print(f'Wrote review markdown: {p}')

print('\nAll 14 review markdown files generated successfully.')
