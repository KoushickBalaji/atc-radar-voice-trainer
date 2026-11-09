import math
import sys
sys.path.insert(0, r'D:\ATC\radar-trainer\src')
from airport_profiles import AirportProfile, get_profile
from msaw import MinimumAltitudeMonitor

p = get_profile('VEBS')
arp = [20.24666667, 85.81861111]
ptA = [20.07111389, 85.71552222]
ptB = [20.23800000, 85.60840000]

def pt_at(r_nm, brg_deg):
    lat0, lon0 = arp
    dlat = (r_nm * math.cos(math.radians(brg_deg))) / 60
    dlon = (r_nm * math.sin(math.radians(brg_deg))) / (60 * math.cos(math.radians(lat0)))
    return [round(lat0 + dlat, 8), round(lon0 + dlon, 8)]

points = {
    'ARP': arp,
    'A': ptA,
    'B': ptB,
    'N25': pt_at(25.0, 0),
    'S25': pt_at(25.0, 180),
    'N12': pt_at(12.0, 0),
    'S12': pt_at(12.0, 180),
}

# Add intermediate points along 12 NM inner boundary
# For East half (inner goes from S12 (180) to N12 (0)):
east_inner_pts = []
for deg in range(175, 0, -5):
    name = f'IE_{deg}'
    points[name] = pt_at(12.0, deg)
    east_inner_pts.append(name)

# For West half (inner goes from N12 (360) to S12 (180)):
west_inner_pts = []
for deg in range(355, 180, -5):
    name = f'IW_{deg}'
    points[name] = pt_at(12.0, deg)
    west_inner_pts.append(name)

regions = [
    {
        'id': 'area-1',
        'minimum_ft': 2200,
        'label': pt_at(6.0, 238),
        'boundary': ['ARP', 'A', {'to': 'B', 'center': arp}]
    },
    {
        'id': 'area-2',
        'minimum_ft': 1900,
        'label': pt_at(6.0, 60),
        'boundary': ['ARP', 'B', {'to': 'A', 'center': arp}]
    },
    {
        'id': 'area-3-east',
        'minimum_ft': 3200,
        'label': pt_at(18.0, 90),
        'boundary': ['N12', 'N25', {'to': 'S25', 'center': arp}, 'S12'] + east_inner_pts
    },
    {
        'id': 'area-3-west',
        'minimum_ft': 3200,
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
        'file': 'Airport Layouts/Bhubaneswar/VEBS-ATC-SMAC.pdf',
        'chart': 'AD 2 VEBS 3-301',
        'effective_date': '2019-07-01',
        'note': 'Radial sectors within 12NM (Area 1: 2200ft, Area 2: 1900ft) and outer annulus 12-25NM (Area 3: 3200ft).'
    },
    'suspend_on_tracked_ils': True,
    'points': points,
    'regions': regions
}

p.data['msaw'] = msaw_config
monitor = MinimumAltitudeMonitor(p)
print('Monitor created successfully, regions:', len(monitor.regions))

# Test points
tests = [
    (6.0, 238, 2200, 'Area 1 interior'),
    (6.0, 60, 1900, 'Area 2 interior'),
    (18.0, 90, 3200, 'Area 3 East interior'),
    (18.0, 270, 3200, 'Area 3 West interior'),
    (11.9, 90, 1900, 'Just inside 12NM in Area 2'),
    (12.1, 90, 3200, 'Just outside 12NM in Area 3'),
    (24.9, 90, 3200, 'Inside 25NM in Area 3'),
    (25.5, 90, None, 'Outside 25NM'),
]

for r, b, expected, desc in tests:
    pos = pt_at(r, b)
    res = monitor.evaluate({'lat': pos[0], 'lon': pos[1], 'alt_ft': 4000})
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

print('ALL VEBS TESTS PASSED!')
