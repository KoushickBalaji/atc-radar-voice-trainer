import fitz
import math

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

# Point text locations (x, y)
words = page.get_text('words')
pts_pos = {}
for w in words:
    if len(w[4]) == 1 and 'A' <= w[4] <= 'S':
        pts_pos[w[4]] = ((w[0] + w[2])/2, (w[1] + w[3])/2)

# Collect all line segments in the PDF
lines = []
for d in page.get_drawings():
    for item in d.get('items', []):
        if item[0] == 'l':
            p1, p2 = item[1], item[2]
            lines.append((p1, p2))

# Find lines whose endpoints are near any two points in pts_pos
print('Checking direct lines between points...')
connections = set()
for p1, p2 in lines:
    n1, n2 = None, None
    for name, pos in pts_pos.items():
        if math.hypot(p1.x - pos[0], p1.y - pos[1]) < 30:
            n1 = name
        if math.hypot(p2.x - pos[0], p2.y - pos[1]) < 30:
            n2 = name
    if n1 and n2 and n1 != n2:
        connections.add(tuple(sorted([n1, n2])))

for c in sorted(connections):
    print('Connected:', c)
