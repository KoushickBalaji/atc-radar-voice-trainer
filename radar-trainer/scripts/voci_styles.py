import fitz

doc = fitz.open('D:/ATC/Airport Layouts/Cochin/VOCI-ATC-SMAC.PDF')
page = doc[0]

# Let's inspect drawing properties (colors and widths)
styles = {}
for d in page.get_drawings():
    c = d.get('color')
    w = d.get('width')
    dashes = d.get('dashes')
    key = (c, w, dashes)
    styles[key] = styles.get(key, 0) + len(d.get('items', []))

for k, count in sorted(styles.items(), key=lambda x: -x[1])[:20]:
    print(f'Style: c={k[0]}, w={k[1]}, dashes={k[2]} -> {count} items')
