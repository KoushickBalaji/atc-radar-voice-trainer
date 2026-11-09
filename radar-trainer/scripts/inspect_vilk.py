import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open(r'D:\ATC\Airport Layouts\Lucknow\VILK-ATC-SMAC.pdf')
page = doc[0]

text = page.get_text()
print('Direct text in VILK:\n', text)

# OCR text
ocr = open(r'D:\ATC\radar-trainer\scratch\smac_ocr\VILK.txt', encoding='utf-8').read()
print('OCR text in VILK:\n', ocr)
