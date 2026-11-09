import math
import json

arp = [12.952222222222222, 77.66444444444446]

pts = {
    'A': [12.80952222, 76.99754722],
    'B': [12.81838056, 77.43491111],
    'C': [13.23545556, 77.32495556],
    'D': [13.24606389, 77.89386111],
    'E': [12.88005, 77.94270833],
    'F': [12.88345, 78.14308611],
    'G': [12.71668611, 78.14595833],
    'H': [12.62533056, 78.25991111],
    'I': [12.41669167, 78.073925],
    'J': [12.54909167, 77.97364444],
    'K': [12.56739167, 77.76018611],
    'L': [12.57659167, 77.65211389],
    'M': [12.65587222, 77.5712],
    'N': [12.65265556, 77.40407778],
    'O': [12.60346111, 77.08196944],
    'P': [12.28617222, 77.73534444],
    'Q': [13.25246111, 78.27501667],
    'R': [13.61443333, 77.56345],
    'S': [13.24019444, 77.57079167]
}

def dist_brg(p1, p2):
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    brg = (math.degrees(math.atan2(y, x)) + 360) % 360
    # distance in NM
    mid_lat = (lat1 + lat2) / 2
    d = math.hypot(dlat * 60, dlon * 60 * math.cos(mid_lat))
    return d, brg

for k, p in sorted(pts.items()):
    d, b = dist_brg(arp, p)
    print(f'{k}: dist={d:5.2f} NM, brg={b:5.1f} deg | lat={p[0]:.6f}, lon={p[1]:.6f}')
