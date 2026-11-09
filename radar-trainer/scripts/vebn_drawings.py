from PIL import Image
import math

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEBN.png')
w, h = im.size

# In page coords or image pixels, let's find the exact pixel locations of West point and East point
# Let's search around x=0.25*w, y=0.52*h for West point and x=0.75*w, y=0.53*h for East point
# We can search for the text box '082 31' and '083 09'
import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Varanasi\VEBN-ATC-SMAC.pdf')
page = doc[0]
drawings = page.get_drawings()
print(f'Total drawings in VEBN: {len(drawings)}')

# Check for line items or curves that span across x ~ 150 to x ~ 450
for d in drawings:
    for item in d.get('items', []):
        if item[0] == 'l':
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) < 30 and abs(p1.x - p2.x) > 100:
                print(f'Line: ({p1.x:.1f}, {p1.y:.1f}) -> ({p2.x:.1f}, {p2.y:.1f}), width={d.get("width")}')
        elif item[0] == 'c':
            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
            if p1.y > 300:
                print(f'Curve: ({p1.x:.1f}, {p1.y:.1f}) -> ({p4.x:.1f}, {p4.y:.1f}), width={d.get("width")}')
