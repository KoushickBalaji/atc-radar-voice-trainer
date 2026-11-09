import fitz
import re

doc = fitz.open(r'D:\ATC\Airport Layouts\Bhogapuram\VOVI-ATC-SMAC.pdf')
page = doc[0]

words = page.get_text('words')
labels = ['2200', '2600', '3000', '5200', '5700']
for w in words:
    if w[4] in labels:
        print(f'Alt {w[4]} at bbox: ({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})')

for w in words:
    if re.match(r'^C\d+$', w[4]):
        print(f'Point {w[4]} at bbox: ({w[0]:.1f}, {w[1]:.1f})')
