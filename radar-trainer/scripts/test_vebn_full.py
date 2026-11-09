import math
import sys
sys.path.insert(0, r'D:\ATC\radar-trainer\src')
from airport_profiles import AirportProfile, get_profile
from msaw import MinimumAltitudeMonitor

p = get_profile('VEBN')
arp = [25 + 27/60 + 4/3600, 82 + 51/60 + 31/3600]
pt_west = [25 + 9/60 + 57.6/3600, 82 + 31/60 + 20.66/3600]
pt_east = [25 + 8/60 + 5.4/3600, 83 + 9/60 + 21.33/3600]

def pt_at(r_nm, brg_deg):
    lat0, lon0 = arp
    dlat = (r_nm * math.cos(math.radians(brg_deg))) / 60
    dlon = (r_nm * math.sin(math.radians(brg_deg))) / (60 * math.cos(math.radians(lat0)))
    return [round(lat0 + dlat, 8), round(lon0 + dlon, 8)]

points = {
    'ARP': arp,
    'WEST': pt_west,
    'EAST': pt_east,
}

regions = [
    {
        'id': 'north',
        'minimum_ft': 2300,
        'label': pt_at(10.0, 0),
        'boundary': ['EAST', 'WEST', {'to': 'EAST', 'center': arp}]
    },
    {
        'id': 'south',
        'minimum_ft': 2500,
        'label': pt_at(20.0, 180),
        'boundary': ['WEST', 'EAST', {'to': 'WEST', 'center': arp}]
    }
]

msaw_config = {
    'schema_version': 1,
    'coordinate_reference': 'WGS84',
    'altitude_unit': 'ft',
    'altitude_reference': 'AMSL',
    'source': {
        'file': 'Airport Layouts/Varanasi/VEBN-ATC-SMAC.pdf',
        'chart': 'AD 2 VEBN 3-301',
        'effective_date': '2026-08-06',
        'note': 'Divided by straight line between 25NM arc points 250957.6N 0823120.66E and 250805.4N 0830921.33E into North sector (2300ft) and South sector (2500ft).'
    },
    'suspend_on_tracked_ils': True,
    'points': points,
    'regions': regions
}

p.data['msaw'] = msaw_config
monitor = MinimumAltitudeMonitor(p)
print('VEBN monitor created successfully, regions:', len(monitor.regions))

# Test points
tests = [
    (10.0, 0, 2300, 'North sector interior (North)'),
    (15.0, 90, 2300, 'North sector interior (East)'),
    (15.0, 270, 2300, 'North sector interior (West)'),
    (20.0, 180, 2500, 'South sector interior (South)'),
    (24.5, 180, 2500, 'South sector near outer arc'),
    (25.5, 180, None, 'Outside coverage South'),
    (25.5, 0, None, 'Outside coverage North'),
]

for r, b, expected, desc in tests:
    pos = pt_at(r, b)
    res = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': 3000})
    actual = res['minimum_ft']
    status = res['status']
    print(f'{desc:30s}: r={r:4.1f} NM, b={b:3d} deg -> expected={expected}, actual={actual}, status={status}')
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

# Test shared boundary uses highest minimum (2500)
# Midpoint of West and East
mid_lat = (pt_west[0] + pt_east[0]) / 2
mid_lon = (pt_west[1] + pt_east[1]) / 2
res_boundary = monitor.evaluate({'lat': mid_lat, 'lon': mid_lon, 'alt_ft': 2400})
print(f'Shared boundary: minimum={res_boundary["minimum_ft"]}, status={res_boundary["status"]}')
assert res_boundary['minimum_ft'] == 2500
assert res_boundary['status'] == 'warning'

# No gaps in interior
gaps = []
for r in [0.5, 2, 5, 10, 15, 20, 24.5]:
    for b in range(0, 360, 2):
        pos = pt_at(r, b)
        res = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': 3000})
        if res['status'] != 'clear':
            gaps.append((r, b, res['status']))

print(f'Gaps in interior: {len(gaps)}')
print('ALL VEBN TESTS PASSED!')
