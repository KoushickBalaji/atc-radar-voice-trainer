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

pts = {}
for k, v in pts_dms.items():
    pts[k] = [v[0] + v[1]/60 + v[2]/3600, v[3] + v[4]/60 + v[5]/3600]

def to_nm(lat, lon):
    x = (lon - center[1]) * 60 * math.cos(math.radians(center[0]))
    y = (lat - center[0]) * 60
    return x, y

# Plot in NM space
fig, ax = plt.subplots(figsize=(10, 10))

# Draw 10, 20, 30 NM rings
for r in [5, 10, 15, 20, 25, 30]:
    circle = plt.Circle((0, 0), r, fill=False, color='gray', linestyle='--' if r < 30 else '-', alpha=0.5)
    ax.add_patch(circle)

# Plot points
for k, (lat, lon) in pts.items():
    x, y = to_nm(lat, lon)
    ax.plot(x, y, 'ro', markersize=4)
    ax.text(x + 0.5, y + 0.5, k, fontsize=9, fontweight='bold')

ax.plot(0, 0, 'b*', markersize=10, label='TAR/MSSR')

# MVA labels approximate positions in NM
# 2000: West
# 3000: South/Center
# 3800: North (around 10 NM)
# 4000: NW (around 20 NM)
# 6200: North-East (around 20 NM)
# 6900: East (around 25 NM)
# 6200: SE (around 20 NM)
# 5100: SE (around 25 NM)

ax.set_xlim(-35, 35)
ax.set_ylim(-35, 35)
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)
plt.title('VOCI Points in NM Projection from TAR/MSSR')
plt.savefig('D:/ATC/radar-trainer/scratch/VOCI_points_nm.png', dpi=200)
print('Saved VOCI_points_nm.png')
