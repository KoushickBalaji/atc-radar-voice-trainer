import math
from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_map.png')
w, h = im.size

# We know the map coordinates:
# Center TAR/MSSR: 10°08'54.62"N, 076°24'33.32"E
# Let's find where the outer circle is:
# In VOCI_map.png, the 30 NM circle touches near the borders:
# Let's find the circle center (cx, cy) and radius R in pixels!
# We can find pixels with dark color on the outer circle
import numpy as np
arr = np.array(im.convert('L'))

# Search for the circle center and radius
# The circle has radius approx 0.45 * min(w, h)
# Let's test centers around (w/2, h/2)
best_score = 0
best_cx, best_cy, best_r = 0, 0, 0

for cx in range(int(w*0.48), int(w*0.52), 2):
    for cy in range(int(h*0.48), int(h*0.52), 2):
        for r in range(int(w*0.40), int(w*0.46), 2):
            # sample 36 points on circle
            score = 0
            for a in range(0, 360, 10):
                rad = math.radians(a)
                px = int(cx + r * math.sin(rad))
                py = int(cy - r * math.cos(rad))
                if 0 <= px < w and 0 <= py < h:
                    if arr[py, px] < 100:
                        score += 1
            if score > best_score:
                best_score = score
                best_cx, best_cy, best_r = cx, cy, r

print(f'Circle fit: center=({best_cx}, {best_cy}), R={best_r} px (score={best_score}/36)')
# R is 30 NM!
px_per_nm = best_r / 30.0
print(f'Pixels per NM: {px_per_nm:.2f}')
