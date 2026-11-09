import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Cochin\VOCI-ATC-SMAC.PDF')
page = doc[0]

# Render high-res image if needed or check OCR text
lines = open(r'D:\ATC\radar-trainer\scratch\smac_ocr\VOCI.txt', encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if any(k in l for k in ['Boundary', 'Latitude', 'Longitude', 'Points Coordinates', 'MVA']):
        for j in range(max(0, i-2), min(len(lines), i+35)):
            print(lines[j])
        break
