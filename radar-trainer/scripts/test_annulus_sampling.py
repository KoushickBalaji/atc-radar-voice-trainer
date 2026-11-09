import math
import sys
sys.path.insert(0, r'D:\ATC\radar-trainer\src')
from airport_profiles import AirportProfile, get_profile
from msaw import MinimumAltitudeMonitor

# Load base VEBS profile
base = get_profile('VEBS')

arp = [20.24666667, 85.81861111]
ptA = [20.07111389, 85.71552222]
ptB = [20.23800000, 85.60840000]

def pt_at(r_nm, brg_deg):
    lat0, lon0 = arp
    dlat = (r_nm * math.cos(math.radians(brg_deg))) / 60
    dlon = (r_nm * math.sin(math.radians(brg_deg))) / (60 * math.cos(math.radians(lat0)))
    return [round(lat0 + dlat, 8), round(lon0 + dlon, 8)]

# Let's test two halves for Area 3: East half (0 to 180) and West half (180 to 360)
# Sample the inner edge from 180 to 0 in steps of 5 degrees
inner_samples_east = []
for deg in range(180, -1, -5):
    inner_samples_east.append(pt_at(12.0, deg))

print(f'Inner samples east count: {len(inner_samples_east)}')
