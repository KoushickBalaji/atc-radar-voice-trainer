import math
import sys
sys.path.insert(0, r'D:\ATC\radar-trainer\src')
from airport_profiles import AirportProfile, get_profile
from msaw import MinimumAltitudeMonitor

p = get_profile('VEPT')
arp = [25 + 35/60 + 37/3600, 85 + 5/60 + 31/3600]

def pt_at(r_nm, brg_deg):
    lat0, lon0 = arp
    dlat = (r_nm * math.cos(math.radians(brg_deg))) / 60
    dlon = (r_nm * math.sin(math.radians(brg_deg))) / (60 * math.cos(math.radians(lat0)))
    return [round(lat0 + dlat, 8), round(lon0 + dlon, 8)]

points = {
    'ARP': arp,
    'N25': pt_at(25.0, 0),
    'S25': pt_at(25.0, 180),
    'N12': pt_at(12.0, 0),
    'S12': pt_at(12.0, 180),
}

east_inner_pts = []
for deg in range(175, 0, -5):
    name = f'IE_{deg}'
    points[name] = pt_at(12.0, deg)
    east_inner_pts.append(name)

west_inner_pts = []
for deg in range(355, 180, -5):
    name = f'IW_{deg}'
    points[name] = pt_at(12.0, deg)
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
        'label': pt_at(18.0, 90),
        'boundary': ['N12', 'N25', {'to': 'S25', 'center': arp}, 'S12'] + east_inner_pts
    },
    {
        'id': 'area-b-west',
        'minimum_ft': 2000,
        'label': pt_at(18.0, 270),
        'boundary': ['S12', 'S25', {'to': 'N25', 'center': arp}, 'N12'] + west_inner_pts
    }
]

msaw_config = {
    'schema_version': 1,
    'coordinate_reference': 'WGS84',
    'altitude_unit': 'ft',
    'altitude_reference': 'AMSL',
    'source': {
        'file': 'Airport Layouts/Patna/VEPT-ATC-SMAC.pdf',
        'chart': 'AD 2 VEPT 3-301',
        'effective_date': '2019-07-01',
        'note': 'Area A (within 12NM of ARP: 1700ft) and Area B (annulus 12-25NM of ARP: 2000ft).'
    },
    'suspend_on_tracked_ils': True,
    'points': points,
    'regions': regions
}

p.data['msaw'] = msaw_config
monitor = MinimumAltitudeMonitor(p)
print('VEPT monitor created successfully, regions:', len(monitor.regions))

# Test points
tests = [
    (5.0, 45, 1700, 'Area A interior NE'),
    (5.0, 225, 1700, 'Area A interior SW'),
    (11.8, 90, 1700, 'Area A just inside 12NM'),
    (12.2, 90, 2000, 'Area B just outside 12NM'),
    (18.0, 90, 2000, 'Area B East interior'),
    (18.0, 270, 2000, 'Area B West interior'),
    (24.8, 180, 2000, 'Area B inside 25NM'),
    (25.5, 180, None, 'Outside 25NM'),
]

for r, b, expected, desc in tests:
    pos = pt_at(r, b)
    res = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': 3000})
    actual = res['minimum_ft']
    status = res['status']
    print(f'{desc:25s}: r={r:4.1f} NM, b={b:3d} deg -> expected={expected}, actual={actual}, status={status}')
    if expected is not None:
        assert actual == expected, f'Mismatch: {actual} != {expected}'
        # Test altitude thresholds
        warn = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': expected - 50})
        clear1 = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': expected})
        clear2 = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': expected + 100})
        assert warn['status'] == 'warning'
        assert clear1['status'] == 'clear'
        assert clear2['status'] == 'clear'
    else:
        assert status == 'outside_coverage'

gaps = []
for r in [0.5, 2, 5, 10, 11.8, 12.2, 15, 20, 24.5]:
    for b in range(0, 360, 2):
        pos = pt_at(r, b)
        res = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': 3000})
        if res['status'] != 'clear':
            gaps.append((r, b, res['status']))

print(f'Gaps in interior: {len(gaps)}')
print('ALL VEPT TESTS PASSED!')
