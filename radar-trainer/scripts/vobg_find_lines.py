import math
from PIL import Image, ImageDraw

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOBG.png')
w, h = im.size
sx = w / 595.32
sy = h / 807.84

dots = {
    'A': (96.55 * sx, 479.58 * sy),
    'B': (272.60 * sx, 496.38 * sy),
    'C': (162.25 * sx, 342.60 * sy),
    'D': (418.78 * sx, 316.98 * sy),
    'E': (414.40 * sx, 486.90 * sy),
    'F': (499.36 * sx, 449.46 * sy),
    'G': (537.23 * sx, 515.58 * sy),
    'H': (539.87 * sx, 587.82 * sy),
    'I': (474.64 * sx, 665.46 * sy),
    'J': (444.10 * sx, 572.76 * sy),
    'K': (372.87 * sx, 566.46 * sy),
    'L': (318.15 * sx, 605.58 * sy),
    'M': (294.45 * sx, 534.42 * sy),
    'N': (214.76 * sx, 536.22 * sy),
    'O': (112.63 * sx, 601.02 * sy),
    'P': (353.61 * sx, 713.21 * sy),
    'Q': (551.51 * sx, 311.22 * sy),
    'R': (248.60 * sx, 210.42 * sy),
    'S': (253.52 * sx, 319.98 * sy),
}

# Function to check how dark the pixels along segment p1->p2 are
def segment_darkness(p1, p2):
    n_samples = int(math.hypot(p2[0]-p1[0], p2[1]-p1[1]))
    if n_samples == 0:
        return 255
    dark_count = 0
    for i in range(5, n_samples - 5): # skip endpoints
        f = i / n_samples
        x = int(p1[0] + f * (p2[0] - p1[0]))
        y = int(p1[1] + f * (p2[1] - p1[1]))
        if 0 <= x < w and 0 <= y < h:
            pix_val = im.getpixel((x, y))
            # check if dark (black line)
            if max(pix_val[:3]) < 70:
                dark_count += 1
    return dark_count / max(1, n_samples - 10)

# Check all pairs
tested = []
names = sorted(dots.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        n1, n2 = names[i], names[j]
        frac = segment_darkness(dots[n1], dots[n2])
        if frac > 0.4:
            tested.append((frac, n1, n2))

tested.sort(reverse=True)
print('Strong straight line segments between dots:')
for frac, n1, n2 in tested:
    print(f'  {n1} <-> {n2}: {frac*100:.1f}% dark pixels')
