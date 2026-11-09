import re
import math

text = open(r'D:\ATC\radar-trainer\scratch\smac_text\VOVI.txt', encoding='utf-8').read()
pattern = re.compile(r'(\d+)\s+(C\d+)\s+(\d{3})\s+(\d{2})\s+([\d.]+)\s+E\s+(\d{2})\s+(\d{2})\s+([\d.]+)\s+N')

pts = {}
for m in pattern.finditer(text):
    sno, name = m.group(1), m.group(2)
    lon = int(m.group(3)) + int(m.group(4))/60 + float(m.group(5))/3600
    lat = int(m.group(6)) + int(m.group(7))/60 + float(m.group(8))/3600
    pts[name] = [round(lat, 8), round(lon, 8)]

arp = [17.97388889, 83.50555556]

def dist_brg(p1, p2):
    dlat = (p2[0] - p1[0]) * 60
    dlon = (p2[1] - p1[1]) * 60 * math.cos(math.radians((p1[0] + p2[0])/2))
    d = math.hypot(dlat, dlon)
    b = (math.degrees(math.atan2(dlon, dlat)) + 360) % 360
    return d, b

print(f'Total VOVI points found: {len(pts)}')
for k, p in sorted(pts.items()):
    d, b = dist_brg(arp, p)
    print(f'{k:5s}: dist={d:5.2f} NM, brg={b:5.1f} deg | lat={p[0]:.6f}, lon={p[1]:.6f}')
