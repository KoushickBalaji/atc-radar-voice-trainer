import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

# Let's inspect vector paths
drawings = page.get_drawings()
# Find line segments that have width > 1 or certain color (boundary lines)
boundary_segments = []
for d in drawings:
    width = d.get('width', 0)
    color = d.get('color')
    fill = d.get('fill')
    # sector boundary lines are typically dark / black / solid
    for item in d.get('items', []):
        if item[0] == 'l':
            p1, p2 = item[1], item[2]
            boundary_segments.append((p1, p2, width, color))

print(f'Total line segments: {len(boundary_segments)}')

# Let's also look at the words around the point labels to see if any lines connect them
