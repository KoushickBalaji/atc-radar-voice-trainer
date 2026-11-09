import fitz
import re

doc = fitz.open(r'D:\ATC\Airport Layouts\Guwahati\VEGT-ATC-SMAC.pdf')
page = doc[0]

# Search text
text = page.get_text()
# Find patterns like Ndddddd or Edddddd or Ndd dd dd
print('=== Direct text matches ===')
for line in text.split('\n'):
    if any(k in line for k in ['N2', 'E09', 'MVA', '2500', '3500', '5000', '6000', '7000', 'ARP']):
        print(line)

# Let's also check OCR text of VEGT
print('=== OCR text matches ===')
ocr = open(r'D:\ATC\radar-trainer\scratch\smac_ocr\VEGT.txt', encoding='utf-8').read()
for line in ocr.split('\n'):
    if any(k in line for k in ['N2', 'E0', 'MVA', '2500', '3500', '5000', '6000', '7000', 'VER', 'VED']):
        print(line)
