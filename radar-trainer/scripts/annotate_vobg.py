import fitz
from PIL import Image, ImageDraw, ImageFont

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

# Render high-res pixmap
pix = page.get_pixmap(dpi=200)
im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
draw = ImageDraw.Draw(im)

# Let's find the point labels and their coordinates in PDF page units
words = page.get_text('words')
# scale factor from page units to pixmap pixels
sx = pix.width / page.rect.width
sy = pix.height / page.rect.height

pts_text = {}
for w in words:
    # point letters
    if len(w[4]) == 1 and 'A' <= w[4] <= 'S':
        # check if near coordinate
        pts_text[w[4]] = ((w[0] + w[2])/2 * sx, (w[1] + w[3])/2 * sy)

for name, (px, py) in pts_text.items():
    draw.ellipse([px-10, py-10, px+10, py+10], outline='red', width=3)
    draw.text((px+12, py-12), name, fill='red')

im.save(r'D:\ATC\radar-trainer\scratch\VOBG_annotated.png')
print('Annotated VOBG saved.')
