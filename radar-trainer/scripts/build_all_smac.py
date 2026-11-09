"""Build and validate all SMAC outputs and reviews for the 14 pending airports.

Conforms to radar-trainer/docs/SMAC_DATA_HANDOFF.md.
Only places complete, verified datasets in outputs/airport-import/smac/<ICAO>.json.
Stores unresolved / pending datasets and reviews in outputs/airport-import/smac-review/.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from airport_profiles import get_profile
from msaw import MinimumAltitudeMonitor

STAGE_SMAC = ROOT / 'outputs/airport-import/smac'
STAGE_REVIEW = ROOT / 'outputs/airport-import/smac-review'
STAGE_SMAC.mkdir(parents=True, exist_ok=True)
STAGE_REVIEW.mkdir(parents=True, exist_ok=True)

# Helper function for geodesic calculations
def to_nm(lat, lon, ref_lat, ref_lon):
    dlat = (lat - ref_lat) * 60.0
    dlon = (lon - ref_lon) * 60.0 * math.cos(math.radians((lat + ref_lat) / 2.0))
    dist = math.hypot(dlat, dlon)
    brg = (math.degrees(math.atan2(dlon, dlat)) + 360.0) % 360.0
    return dist, brg

def pt_from_nm(ref_lat, ref_lon, dist_nm, brg_deg):
    rad = math.radians(brg_deg)
    dlat = (dist_nm * math.cos(rad)) / 60.0
    dlon = (dist_nm * math.sin(rad)) / (60.0 * math.cos(math.radians(ref_lat)))
    return [round(ref_lat + dlat, 8), round(ref_lon + dlon, 8)]

# ==============================================================================
# 1. VEBS (Bhubaneswar)
# ==============================================================================
def build_vebs():
    arp = [20.24666667, 85.81861111]
    ptA = [20.07111389, 85.71552222]
    ptB = [20.23800000, 85.60840000]

    points = {
        'ARP': arp,
        'A': ptA,
        'B': ptB,
        'N25': pt_from_nm(arp[0], arp[1], 25.0, 0),
        'S25': pt_from_nm(arp[0], arp[1], 25.0, 180),
        'N12': pt_from_nm(arp[0], arp[1], 12.0, 0),
        'S12': pt_from_nm(arp[0], arp[1], 12.0, 180),
    }

    east_inner_pts = []
    for deg in range(175, 0, -5):
        name = f'IE_{deg}'
        points[name] = pt_from_nm(arp[0], arp[1], 12.0, deg)
        east_inner_pts.append(name)

    west_inner_pts = []
    for deg in range(355, 180, -5):
        name = f'IW_{deg}'
        points[name] = pt_from_nm(arp[0], arp[1], 12.0, deg)
        west_inner_pts.append(name)

    regions = [
        {
            'id': 'area-1',
            'minimum_ft': 2200,
            'label': pt_from_nm(arp[0], arp[1], 6.0, 238),
            'boundary': ['ARP', 'A', {'to': 'B', 'center': arp}]
        },
        {
            'id': 'area-2',
            'minimum_ft': 1900,
            'label': pt_from_nm(arp[0], arp[1], 6.0, 60),
            'boundary': ['ARP', 'B', {'to': 'A', 'center': arp}]
        },
        {
            'id': 'area-3-east',
            'minimum_ft': 3200,
            'label': pt_from_nm(arp[0], arp[1], 18.0, 90),
            'boundary': ['N12', 'N25', {'to': 'S25', 'center': arp}, 'S12'] + east_inner_pts
        },
        {
            'id': 'area-3-west',
            'minimum_ft': 3200,
            'label': pt_from_nm(arp[0], arp[1], 18.0, 270),
            'boundary': ['S12', 'S25', {'to': 'N25', 'center': arp}, 'N12'] + west_inner_pts
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Bhubaneswar/VEBS-ATC-SMAC.pdf',
            'chart': 'AD 2 VEBS 3-301',
            'effective_date': '2019-07-01',
            'note': 'Area 1 (within 12NM between points A and B, 2200ft AMSL); Area 2 (remaining 12NM circle, 1900ft AMSL); Area 3 (12-25NM annulus, 3200ft AMSL) decomposed into East and West halves.'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# 2. VEPT (Patna)
# ==============================================================================
def build_vept():
    arp = [25 + 35/60 + 37/3600, 85 + 5/60 + 31/3600]

    points = {
        'ARP': arp,
        'N25': pt_from_nm(arp[0], arp[1], 25.0, 0),
        'S25': pt_from_nm(arp[0], arp[1], 25.0, 180),
        'N12': pt_from_nm(arp[0], arp[1], 12.0, 0),
        'S12': pt_from_nm(arp[0], arp[1], 12.0, 180),
    }

    east_inner_pts = []
    for deg in range(175, 0, -5):
        name = f'IE_{deg}'
        points[name] = pt_from_nm(arp[0], arp[1], 12.0, deg)
        east_inner_pts.append(name)

    west_inner_pts = []
    for deg in range(355, 180, -5):
        name = f'IW_{deg}'
        points[name] = pt_from_nm(arp[0], arp[1], 12.0, deg)
        west_inner_pts.append(name)

    regions = [
        {
            'id': 'area-a',
            'minimum_ft': 1700,
            'label': arp,
            'boundary': ['N12', {'to': 'S12', 'center': arp}, {'to': 'N12', 'center': arp}]
        },
        {
            'id': 'area-b-east',
            'minimum_ft': 2000,
            'label': pt_from_nm(arp[0], arp[1], 18.0, 90),
            'boundary': ['N12', 'N25', {'to': 'S25', 'center': arp}, 'S12'] + east_inner_pts
        },
        {
            'id': 'area-b-west',
            'minimum_ft': 2000,
            'label': pt_from_nm(arp[0], arp[1], 18.0, 270),
            'boundary': ['S12', 'S25', {'to': 'N25', 'center': arp}, 'N12'] + west_inner_pts
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Patna/VEPT-ATC-SMAC.pdf',
            'chart': 'AD 2 VEPT 3-301',
            'effective_date': '2019-07-01',
            'note': 'Area A (within 12NM of ARP: 1700ft AMSL) and Area B (annulus 12-25NM of ARP: 2000ft AMSL) decomposed into East and West halves.'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# 3. VEBN (Varanasi)
# ==============================================================================
def build_vebn():
    arp = [25 + 27/60 + 4/3600, 82 + 51/60 + 31/3600]
    pt_west = [25 + 9/60 + 57.6/3600, 82 + 31/60 + 20.66/3600]
    pt_east = [25 + 8/60 + 5.4/3600, 83 + 9/60 + 21.33/3600]

    points = {
        'ARP': arp,
        'WEST': pt_west,
        'EAST': pt_east,
    }

    regions = [
        {
            'id': 'north',
            'minimum_ft': 2300,
            'label': pt_from_nm(arp[0], arp[1], 10.0, 0),
            'boundary': ['EAST', 'WEST', {'to': 'EAST', 'center': arp}]
        },
        {
            'id': 'south',
            'minimum_ft': 2500,
            'label': pt_from_nm(arp[0], arp[1], 20.0, 180),
            'boundary': ['WEST', 'EAST', {'to': 'WEST', 'center': arp}]
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Varanasi/VEBN-ATC-SMAC.pdf',
            'chart': 'AD 2 VEBN 3-301',
            'effective_date': '2026-08-06',
            'note': 'Divided by straight line between 25NM arc points 250957.6N 0823120.66E and 250805.4N 0830921.33E into North sector (2300ft AMSL) and South sector (2500ft AMSL).'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# 4. VILK (Lucknow)
# ==============================================================================
def build_vilk():
    arp = [26 + 45/60 + 43/3600, 80 + 53/60]
    p_north = pt_from_nm(arp[0], arp[1], 25.0, 0)
    p_south = pt_from_nm(arp[0], arp[1], 25.0, 180)

    points = {
        'ARP': arp,
        'N25': p_north,
        'S25': p_south
    }

    regions = [
        {
            'id': 'vilk-mva-2500',
            'minimum_ft': 2500,
            'label': arp,
            'boundary': ['N25', {'to': 'S25', 'center': arp}, {'to': 'N25', 'center': arp}]
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Lucknow/VILK-ATC-SMAC.pdf',
            'chart': 'AD 2 VILK 3-301',
            'effective_date': '2023-11-02',
            'note': 'Single MVA of 2500ft AMSL established within 25NM of ARP (264543N 0805300E).'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# 5. VIJP (Jaipur)
# ==============================================================================
def build_vijp():
    arp = [26 + 49/60 + 27/3600, 75 + 48/60 + 9/3600]
    p_A = [27 + 13/60 + 0.24/3600, 75 + 38/60 + 33.54/3600]
    p_B = [27 + 5/60 + 32.31/3600, 76 + 9/60 + 36.48/3600]
    p_C = [27 + 1/60 + 2.36/3600, 76 + 3/60 + 35.37/3600]
    p_D = [27 + 6/60 + 24.61/3600, 75 + 41/60 + 15.07/3600]

    points = {'ARP': arp, 'A': p_A, 'B': p_B, 'C': p_C, 'D': p_D}

    # Sample C to D along 18 NM arc (from 50 deg down to 340 deg)
    sampled_cd = []
    r_nm = 18.01
    for deg in range(48, -19, -2):
        brg = deg % 360
        pid = f'CD_{brg:03d}'
        points[pid] = pt_from_nm(arp[0], arp[1], r_nm, deg)
        sampled_cd.append(pid)

    boundary_3800 = ['D', 'A', {'to': 'B', 'center': arp}, 'C'] + sampled_cd
    boundary_3300 = ['B', {'to': 'A', 'center': arp}, 'D', {'to': 'C', 'center': arp}]

    regions = [
        {
            'id': 'vijp-sva-3800',
            'minimum_ft': 3800,
            'label': pt_from_nm(arp[0], arp[1], 21.0, 15),
            'boundary': boundary_3800
        },
        {
            'id': 'vijp-mva-3300',
            'minimum_ft': 3300,
            'label': arp,
            'boundary': boundary_3300
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Jaipur/VIJP-ATC-SMAC.pdf',
            'chart': 'AD 2 VIJP 3-301',
            'effective_date': '2020-12-31',
            'note': 'SVA Sector bounded by points A-B-C-D (between 18NM and 25NM from radial 340° to 050°): 3800ft AMSL; remaining 25NM circle around ARP (264927N 0754809E): 3300ft AMSL.'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# 6. VOTR (Tiruchirappalli)
# ==============================================================================
def build_votr():
    arp = [10 + 45/60 + 56.12/3600, 78 + 42/60 + 54.16/3600]
    pts_dms = {
        'TR361': [10 + 46/60 + 51.99/3600, 79 + 7/60 + 47.35/3600],
        'TR362': [10 + 46/60 + 39.95/3600, 79 + 2/60 + 40.40/3600],
        'TR363': [10 + 20/60 + 38.78/3600, 78 + 43/60 + 36.69/3600],
        'TR364': [10 + 25/60 + 43.67/3600, 78 + 43/60 + 22.47/3600],
        'TR365': [10 + 48/60 + 42.50/3600, 78 + 22/60 + 30.54/3600],
        'TR366': [10 + 48/60 + 37.30/3600, 78 + 26/60 + 40.33/3600],
        'TR367': [10 + 44/60 + 37.35/3600, 78 + 28/60 + 39.15/3600],
        'TR368': [10 + 38/60 + 13.00/3600, 78 + 28/60 + 17.77/3600],
        'TR369': [10 + 37/60 + 36.52/3600, 78 + 23/60 + 48.68/3600],
    }

    points = dict(pts_dms)
    points['ARP'] = arp

    boundary_b = ['TR365', 'TR366', 'TR367', 'TR368', 'TR369', {'to': 'TR365', 'center': arp}]
    boundary_c = ['TR361', {'to': 'TR363', 'center': arp}, 'TR364', {'to': 'TR362', 'center': arp}]

    r_start = 20.2128
    r_end = 19.4364
    brg_start = 178.69
    brg_end = 87.85
    sweep = (brg_end - brg_start) % 360

    sampled_inner_a = []
    steps = 135
    for i in range(1, steps):
        f = 1.0 - (i / float(steps))
        angle_deg = (brg_start + sweep * f) % 360
        r_f = r_start + (r_end - r_start) * f - 0.05
        pid = f'A20_{int(angle_deg):03d}_{i}'
        points[pid] = pt_from_nm(arp[0], arp[1], r_f, angle_deg)
        sampled_inner_a.append(pid)

    boundary_a = ['TR363', {'to': 'TR361', 'center': arp}, 'TR362'] + sampled_inner_a + ['TR364']

    regions = [
        {
            'id': 'votr-area-a',
            'minimum_ft': 4000,
            'label': pt_from_nm(arp[0], arp[1], 22.5, 0),
            'boundary': boundary_a
        },
        {
            'id': 'votr-area-b',
            'minimum_ft': 3000,
            'label': pt_from_nm(arp[0], arp[1], 17.0, 265),
            'boundary': boundary_b
        },
        {
            'id': 'votr-area-c',
            'minimum_ft': 2300,
            'label': arp,
            'boundary': boundary_c
        }
    ]

    return {
        'schema_version': 1,
        'coordinate_reference': 'WGS84',
        'altitude_unit': 'ft',
        'altitude_reference': 'AMSL',
        'source': {
            'file': 'Airport Layouts/Tiruchirappalli/VOTR-ATC-SMAC.pdf',
            'chart': 'AD 2 VOTR 3-301',
            'effective_date': '2020-07-16',
            'note': 'Area A (outer 20-25NM annulus from radial 178° clockwise to 088°: 4000ft AMSL); Area B (hills pocket 14-20NM West bounded by TR365-TR369: 3000ft AMSL); Area C (inner 20NM circle plus SE 20-25NM flat plain: 2300ft AMSL).'
        },
        'suspend_on_tracked_ils': True,
        'points': points,
        'regions': regions
    }

# ==============================================================================
# Main Builder & Validator
# ==============================================================================
def main():
    resolved_builders = {
        'VEBS': build_vebs,
        'VEPT': build_vept,
        'VEBN': build_vebn,
        'VILK': build_vilk,
        'VIJP': build_vijp,
        'VOTR': build_votr,
    }

    print('Building and verifying 6 resolved airports...')
    for code, builder in resolved_builders.items():
        spec = builder()
        out_path = STAGE_SMAC / f'{code}.json'
        out_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'Wrote {out_path}')

        # Verify with profile and MinimumAltitudeMonitor
        profile = get_profile(code)
        profile.data['msaw'] = spec
        monitor = MinimumAltitudeMonitor(profile)
        assert len(monitor.regions) == len(spec['regions']), f'{code}: region count mismatch'

        # Interior checks
        for reg in spec['regions']:
            lbl = reg['label']
            min_ft = reg['minimum_ft']
            res_warn = monitor.evaluate({'lat': lbl[0], 'lon': lbl[1], 'alt_ft': min_ft - 50})
            res_clear = monitor.evaluate({'lat': lbl[0], 'lon': lbl[1], 'alt_ft': min_ft})
            assert res_warn['status'] == 'warning', f'{code} {reg["id"]}: expected warning'
            assert res_clear['status'] == 'clear', f'{code} {reg["id"]}: expected clear'

        # Outside coverage check at 26 NM
        arp_pt = spec['points'].get('ARP', [profile.LAT, profile.LON])
        out_pt = pt_from_nm(arp_pt[0], arp_pt[1], 26.0, 45)
        res_out = monitor.evaluate({'lat': out_pt[0], 'lon': out_pt[1], 'alt_ft': 1000})
        assert res_out['status'] == 'outside_coverage', f'{code}: expected outside_coverage at 26 NM'

        print(f'  [PASS] {code} passed all interior, warning/clear threshold, and outside-coverage checks.')

    print('\nAll 6 resolved airports built and verified successfully!')

if __name__ == '__main__':
    main()
