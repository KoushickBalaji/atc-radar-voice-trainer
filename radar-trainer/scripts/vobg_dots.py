import fitz
import math

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

words = page.get_text('words')
pts_pos = {}
for w in words:
    if len(w[4]) == 1 and 'A' <= w[4] <= 'S':
        pts_pos[w[4]] = ((w[0] + w[2])/2, (w[1] + w[3])/2)

# Check all drawing items for circles or small rects near each point
dots = {}
for d in page.get_drawings():
    rect = d.get('rect')
    if rect and rect.width < 15 and rect.height < 15:
        cx, cy = (rect.x0 + rect.x1)/2, (rect.y0 + rect.y1)/2
        for name, pos in pts_pos.items():
            if math.hypot(cx - pos[0], cy - pos[1]) < 40:
                if name not in dots or math.hypot(cx - pos[0], cy - pos[1]) < math.hypot(dots[name][0] - pos[0], dots[name][1] - pos[1]):
                    dots[name] = (cx, cy)

for name in sorted(pts_pos):
    print(f'Point {name}: label at {pts_pos[name]}, dot at {dots.get(name)}')
