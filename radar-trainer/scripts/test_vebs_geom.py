import math
import sys
sys.path.insert(0, r'D:\ATC\radar-trainer\src')
from airport_profiles import AirportProfile, get_profile
from msaw import MinimumAltitudeMonitor

# Let's test Bhubaneswar geometry
arp = [20.24666667, 85.81861111]
ptA = [20.07111389, 85.71552222]
ptB = [20.23800000, 85.60840000]

# Function to compute point at radius and bearing from ARP
def pt_at(r_nm, brg_deg):
    lat0, lon0 = arp
    dlat = (r_nm * math.cos(math.radians(brg_deg))) / 60
    dlon = (r_nm * math.sin(math.radians(brg_deg))) / (60 * math.cos(math.radians(lat0)))
    return [lat0 + dlat, lon0 + dlon]

print('Testing VEBS geometry construction...')
