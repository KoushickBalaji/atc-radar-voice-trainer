import fitz
from PIL import Image

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=200)
im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

words = page.get_text('words')
sx = pix.width / page.rect.width
sy = pix.height / page.rect.height

# Let's find point labels A-S and crop around them
for w in words:
    if len(w[4]) == 1 and 'A' <= w[4] <= 'S':
        letter = w[4]
        cx = int((w[0] + w[2])/2 * sx)
        cy = int((w[1] + w[3])/2 * sy)
        # crop 160x160 box
        box = (max(0, cx-80), max(0, cy-80), min(pix.width, cx+80), min(pix.height, cy+80))
        crop = im.crop(box)
        crop.save(rf'D:\ATC\radar-trainer\scratch\vobg_pt_{letter}.png')

print('All 19 point crops saved.')
