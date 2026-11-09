import fitz

doc = fitz.open('D:/ATC/Airport Layouts/Cochin/VOCI-ATC-SMAC.PDF')
page = doc[0]

red_drawings = []
for d in page.get_drawings():
    c = d.get('color')
    if c and c[0] > 0.8 and c[1] < 0.2 and c[2] < 0.2:
        red_drawings.append(d)

print(f'Total red drawings: {len(red_drawings)}')

for i, d in enumerate(red_drawings):
    items = d.get('items', [])
    w = d.get('width')
    # print line items
    pts = []
    for it in items:
        if it[0] == 'l':
            p1, p2 = it[1], it[2]
            pts.append((p1, p2))
    if len(pts) > 0:
        first = pts[0][0]
        last = pts[-1][1]
        print(f'Red #{i}: {len(pts)} segments, w={w}, start=({first.x:.1f},{first.y:.1f}), end=({last.x:.1f},{last.y:.1f})')
