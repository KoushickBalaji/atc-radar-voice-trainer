import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Bhogapuram\VOVI-ATC-SMAC.pdf')
page = doc[0]

# Print drawings
drawings = page.get_drawings()
print(f'Total drawings in VOVI: {len(drawings)}')

# Check line items with width >= 0.5
thick_lines = []
for d in drawings:
    w = d.get('width', 0)
    for it in d.get('items', []):
        if it[0] == 'l' and w and w >= 0.8:
            thick_lines.append((it[1], it[2], w, d.get('color')))
        elif it[0] == 'c' and w and w >= 0.8:
            thick_lines.append((it[1], it[4], w, 'curve'))

print(f'Thick lines/curves count: {len(thick_lines)}')
for l in thick_lines[:20]:
    print(l)
