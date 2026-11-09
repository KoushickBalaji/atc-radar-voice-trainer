"""Generate all 14 SMAC review documents and 8 draft JSONs.

Conforms to radar-trainer/docs/SMAC_DATA_HANDOFF.md.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE_REVIEW = ROOT / 'outputs/airport-import/smac-review'
STAGE_REVIEW.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Draft JSONs for 8 Unresolved / Pending Airports
# ------------------------------------------------------------------------------

drafts = {
    'VEAT': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "UNRESOLVED_BORDER_CLIPPED",
        "source": {
            "file": "Airport Layouts/Agartala/VEAT-ATC-SMAC.pdf",
            "chart": "AD 2 VEAT 3-301",
            "effective_date": "2024-05-16",
            "note": "Coverage within 25NM is clipped on West, South, and East by the Bangladesh international border (Kolkata FIR boundary). Numerical border coordinates are not published on the chart."
        },
        "suspend_on_tracked_ils": True,
        "points": {
            "ARP": [23.88694444, 91.24055556]
        },
        "regions": [
            {
                "id": "veat-area-a-draft",
                "minimum_ft": 1600,
                "label": [23.88694444, 91.24055556],
                "boundary": ["ARP"],
                "note": "Unresolved: 12NM circle clipped by international border."
            },
            {
                "id": "veat-area-b-draft",
                "minimum_ft": 2700,
                "label": [24.0, 91.24],
                "boundary": ["ARP"],
                "note": "Unresolved: 12-25NM annulus clipped by international border."
            }
        ]
    },
    'VIAR': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "UNRESOLVED_BORDER_CLIPPED",
        "source": {
            "file": "Airport Layouts/Amritsar/VIAR-ATC-SMAC.pdf",
            "chart": "AD 2 VIAR 3-301",
            "effective_date": "2020-12-31",
            "note": "Coverage within 25NM of ARP (314227N 0744757E) is clipped on the West by the Pakistan international border (Lahore FIR boundary). Numerical border coordinates are not published on the chart."
        },
        "suspend_on_tracked_ils": True,
        "points": {
            "ARP": [31.7075, 74.79916667]
        },
        "regions": [
            {
                "id": "viar-area-1-draft",
                "minimum_ft": 2300,
                "label": [31.7075, 74.79916667],
                "boundary": ["ARP"],
                "note": "Unresolved: 12NM circle clipped by international border."
            },
            {
                "id": "viar-area-2-draft",
                "minimum_ft": 2800,
                "label": [31.85, 74.9],
                "boundary": ["ARP"],
                "note": "Unresolved: 12-25NM annulus clipped by international border."
            }
        ]
    },
    'VANP': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "UNRESOLVED_MAP_TABLE_CONFLICT",
        "source": {
            "file": "Airport Layouts/Nagpur/VANP-ATC-SMAC.pdf",
            "chart": "AD 2 VANP 3-301",
            "effective_date": "2025-11-27",
            "note": "Direct conflict: Chart map only displays MVA 2700 and MVA 3100, whereas the printed table defines 5 areas (Area A: 2700, Area B: 2800, Area C: 2400, Area D: 2600, Area E: 3100) with duplicate description text for Area D and Area E."
        },
        "suspend_on_tracked_ils": True,
        "points": {
            "ARP": [21.09222222, 79.0475]
        },
        "regions": []
    },
    'VOCL': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "UNRESOLVED_MISSING_COORDINATES",
        "source": {
            "file": "Airport Layouts/Calicut/VOCL-ATC-SMAC.pdf",
            "chart": "AD 2 VOCL 3-301",
            "effective_date": "2019-07-01",
            "note": "The printed coordinate table contains only 16 rows (points A through Q), but the chart map displays boundary vertices A1, B1, C1, D1, E1, F1, F, H, J without published coordinates."
        },
        "suspend_on_tracked_ils": True,
        "points": {
            "ARP": [11.13666667, 75.95527778]
        },
        "regions": []
    },
    'VEGT': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "UNRESOLVED_MISSING_COORDINATE_TABLE",
        "source": {
            "file": "Airport Layouts/Guwahati/VEGT-ATC-SMAC.pdf",
            "chart": "AD 2 VEGT 3-301",
            "effective_date": "2024-05-16",
            "note": "No coordinate table is provided on the chart. Boundaries follow unquantified topographic contour bounds and radials without vertex coordinates."
        },
        "suspend_on_tracked_ils": True,
        "points": {
            "ARP": [26.10611111, 91.58583333]
        },
        "regions": []
    },
    'VOCI': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "PENDING_SECTOR_CONNECTIVITY_RESOLUTION",
        "source": {
            "file": "Airport Layouts/Cochin/VOCI-ATC-SMAC.PDF",
            "chart": "AD 2 VOCI 3-301",
            "effective_date": "2019-07-01",
            "note": "Points A through X are published in a 24-row coordinate table, but no sector connectivity table is published. Boundary edges follow complex military airspace and terrain paths with multiple ambiguous interpretations."
        },
        "suspend_on_tracked_ils": True,
        "points": {},
        "regions": []
    },
    'VOVI': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "PENDING_SECTOR_CONNECTIVITY_RESOLUTION",
        "source": {
            "file": "Airport Layouts/Bhogapuram/VOVI-ATC-SMAC.pdf",
            "chart": "AD 2 VOVI 3-301",
            "effective_date": "2026-10-29",
            "note": "Points C20 through C52 (19 points) are published in a table, but no sector connectivity table is published. Boundaries follow complex terrain and radial intersections with multiple ambiguous polygon interpretations."
        },
        "suspend_on_tracked_ils": True,
        "points": {},
        "regions": []
    },
    'VOBG': {
        "schema_version": 1,
        "coordinate_reference": "WGS84",
        "altitude_unit": "ft",
        "altitude_reference": "AMSL",
        "status": "PENDING_SECTOR_CONNECTIVITY_RESOLUTION",
        "source": {
            "file": "Airport Layouts/Bengaluru (HAL)/VOBG-ATC-SMAC.pdf",
            "chart": "AD 2 VOBG 3-301",
            "effective_date": "2026-10-01",
            "note": "Points A through S (19 points) are published in a coordinate list, but no sector connectivity table is published. Boundaries follow complex terrain contours and military airspace corridors with multiple ambiguous polygon interpretations."
        },
        "suspend_on_tracked_ils": True,
        "points": {},
        "regions": []
    }
}

for code, spec in drafts.items():
    p = STAGE_REVIEW / f'{code}.draft.json'
    p.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote draft JSON: {p}')

print('Draft JSON generation complete.')
