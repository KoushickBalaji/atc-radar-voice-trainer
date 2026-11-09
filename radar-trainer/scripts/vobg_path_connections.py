import fitz
import math

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

dots = {
    'A': (96.55, 479.58),
    'B': (272.60, 496.38),
    'C': (162.25, 342.60),
    'D': (418.78, 316.98),
    'E': (414.40, 486.90),
    'F': (499.36, 449.46),
    'G': (537.23, 515.58),
    'H': (539.87, 587.82),
    'I': (474.64, 665.46),
    'J': (444.10, 572.76),
    'K': (372.87, 566.46),
    'L': (318.15, 605.58),
    'M': (294.45, 534.42),
    'N': (214.76, 536.22),
    'O': (112.63, 601.02),
    'P': (353.61, 713.21),
    'Q': (551.51, 311.22),
    'R': (248.60, 210.42),
    'S': (253.52, 319.98),
}

# In PDF vector graphics, a path can have multiple items: lines, curves
# Let's inspect all paths in drawings
connections = []
for d_idx, d in enumerate(page.get_drawings()):
    items = d.get('items', [])
    if not items:
        continue
    # Gather all endpoints in this path
    pts = []
    for it in items:
        if it[0] == 'l':
            pts.append(it[1])
            pts.append(it[2])
        elif it[0] == 'c':
            pts.append(it[1])
            pts.append(it[4])
    
    # Check if this path connects any pair of dots
    for name1, dot1 in dots.items():
        for name2, dot2 in dots.items():
            if name1 >= name2:
                continue
            has1 = any(math.hypot(p.x - dot1[0], p.y - dot1[1]) < 3.0 for p in pts)
            has2 = any(math.hypot(p.x - dot2[0], p.y - dot2[1]) < 3.0 for p in pts)
            if has1 and has2:
                connections.append((name1, name2, d_idx, len(items)))

print('Found connections:')
unique_conn = sorted(list(set((c[0], c[1]) for c in connections)))
for c in unique_conn:
    print(c)
