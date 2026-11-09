import fitz
import re
from PIL import Image, ImageDraw, ImageFont

# Let's inspect the VOBG PDF to find where the sector labels and boundaries are.
doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

# Let's search for words and their positions
words = page.get_text('words')
# words is list of (x0, y0, x1, y1, word, block_no, line_no, word_no)
# Look for numbers like 4600, 5200, 6000, 5500, 5000, 5700
labels = ['4600', '5200', '6000', '5500', '5000', '5700']
for w in words:
    if w[4] in labels:
        print(f'Altitude label {w[4]} at bbox: ({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})')

# Also let's find the point letter labels A-S
point_names = [chr(c) for c in range(ord('A'), ord('T'))]
for w in words:
    if w[4] in point_names and len(w[4]) == 1:
        print(f'Point label {w[4]} at bbox: ({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})')
