import math
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_map.png')
w, h = im.size

center = [10 + 8/60 + 54.62/3600, 76 + 24/60 + 33.32/3600]

pts_dms = {
    'A': [10, 34, 11.7, 76, 8, 9.9],
    'B': [10, 38, 50.8, 76, 20, 47.8],
    'C': [10, 36, 39.5, 76, 36, 27.1],
    'D': [10, 14, 14.3, 76, 54, 29.4],
    'E': [9, 57, 54.3, 76, 52, 50.0],
    'F': [9, 44, 20.8, 76, 42, 1.3],
    'G': [9, 38, 57.0, 76, 23, 49.2],
    'H': [10, 15, 49.4, 76, 15, 29.7],
    'I': [9, 59, 16.3, 76, 49, 19.6],
    'J': [10, 15, 19.5, 76, 21, 7.0],
    'K': [10, 9, 20.5, 76, 32, 45.7],
    'L': [10, 3, 1.1, 76, 38, 32.6],
    'M': [10, 0, 11.3, 76, 38, 32.9],
    'N': [9, 59, 25.6, 76, 22, 49.7],
    'O': [10, 6, 30.4, 76, 42, 25.5],
    'P': [10, 15, 25.0, 76, 33, 59.6],
    'Q': [10, 20, 23.5, 76, 26, 7.1],
    'R': [10, 31, 32.8, 76, 21, 8.7],
    'S': [10, 22, 41.9, 76, 25, 5.6],
    'T': [10, 22, 7.8, 76, 12, 58.9],
    'U': [10, 21, 47.8, 76, 35, 30.8],
    'V': [10, 14, 27.7, 76, 52, 31.3],
    'W': [9, 52, 19.2, 76, 42, 24.9],
    'X': [9, 49, 16.8, 76, 39, 23.0],
}

cx, cy = 732, 683
scale = 20.50

pts_px = {}
for k, v in pts_dms.items():
    lat = v[0] + v[1]/60 + v[2]/3600
    lon = v[3] + v[4]/60 + v[5]/3600
    dx = (lon - center[1]) * 60 * math.cos(math.radians(center[0]))
    dy = (lat - center[0]) * 60
    pts_px[k] = (cx + dx * scale, cy - dy * scale)

fig, ax = plt.subplots(figsize=(14, 14))
ax.imshow(im)

for k, (px, py) in pts_px.items():
    ax.plot(px, py, 'ro', markersize=5)
    ax.text(px + 6, py - 6, k, fontsize=12, fontweight='bold', color='red',
            bbox=dict(boxstyle='square,pad=0.1', facecolor='white', alpha=0.7))

# Candidate line segments to test
candidate_lines = [
    ('A', 'T'), ('T', 'H'), ('H', 'J'),
    ('B', 'R'), ('R', 'S'), ('S', 'Q'),
    ('C', 'U'), ('U', 'P'), ('P', 'K'),
    ('D', 'V'), ('V', 'O'), ('O', 'L'), ('L', 'M'), ('M', 'W'), ('W', 'X'), ('X', 'F'),
    ('E', 'I'),
    ('G', 'N'),
    ('J', 'Q'), ('Q', 'P'), ('K', 'L'), ('M', 'I'),
    ('H', 'T'), ('S', 'T'), ('R', 'T')
]

for p1, p2 in candidate_lines:
    x1, y1 = pts_px[p1]
    x2, y2 = pts_px[p2]
    ax.plot([x1, x2], [y1, y2], 'b--', linewidth=1.5, alpha=0.7)

plt.tight_layout()
plt.savefig('D:/ATC/radar-trainer/scratch/VOCI_overlay_test.png', dpi=200)
print('Saved VOCI_overlay_test.png')
