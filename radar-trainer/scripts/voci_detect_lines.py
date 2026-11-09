import math
import numpy as np
from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_map.png').convert('L')
arr = np.array(im)
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

def test_line(p1, p2):
    x1, y1 = pts_px[p1]
    x2, y2 = pts_px[p2]
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist < 5:
        return 0
    steps = int(dist)
    dark_count = 0
    for s in range(5, steps - 5): # skip endpoints
        f = s / float(steps)
        x = int(x1 + (x2 - x1) * f)
        y = int(y1 + (y2 - y1) * f)
        if 0 <= x < w and 0 <= y < h:
            # check 3x3 neighborhood
            min_val = np.min(arr[max(0, y-1):min(h, y+2), max(0, x-1):min(w, x+2)])
            if min_val < 150: # dark pixel
                dark_count += 1
    return dark_count / float(steps - 10)

all_pts = sorted(pts_px.keys())
found_lines = []
for i in range(len(all_pts)):
    for j in range(i + 1, len(all_pts)):
        p1, p2 = all_pts[i], all_pts[j]
        score = test_line(p1, p2)
        if score > 0.40:
            found_lines.append((score, p1, p2))

found_lines.sort(reverse=True)
print(f'Total detected lines with score > 0.4: {len(found_lines)}')
for score, p1, p2 in found_lines:
    d = math.hypot(pts_px[p1][0]-pts_px[p2][0], pts_px[p1][1]-pts_px[p2][1]) / scale
    print(f'{p1} -- {p2}: score={score:.2f}, dist={d:.1f} NM')
