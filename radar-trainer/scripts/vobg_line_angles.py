import math
from PIL import Image

for letter in [chr(c) for c in range(ord('A'), ord('T'))]:
    im = Image.open(rf'D:\ATC\radar-trainer\scratch\vobg_pt_{letter}.png')
    w, h = im.size
    cx, cy = w // 2, h // 2
    # Find angles with dark pixels at radius r=30
    dark_angles = []
    r = 35
    for deg in range(360):
        rad = math.radians(deg)
        px = int(cx + r * math.cos(rad))
        py = int(cy + r * math.sin(rad))
        if 0 <= px < w and 0 <= py < h:
            val = im.getpixel((px, py))
            if max(val[:3]) < 50: # dark pixel
                dark_angles.append(deg)
    
    # cluster consecutive angles
    clusters = []
    if dark_angles:
        curr = [dark_angles[0]]
        for a in dark_angles[1:]:
            if a == curr[-1] + 1:
                curr.append(a)
            else:
                clusters.append(int(sum(curr)/len(curr)))
                curr = [a]
        clusters.append(int(sum(curr)/len(curr)))
    print(f'Point {letter}: line directions at angles: {clusters}')
