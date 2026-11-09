import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Amritsar\VIAR-ATC-SMAC.pdf')
page = doc[0]

# Render cropped areas
# Image is 1654 x 2339
# Let's crop the table in the lower right / center
pix = page.get_pixmap(dpi=200)
print('VIAR dimensions:', pix.width, pix.height)

# WinRT OCR text gave lines for VIAR. Let's see the full table from OCR:
ocr_text = open(r'D:\ATC\radar-trainer\scratch\smac_ocr\VIAR.txt', encoding='utf-8').read()
for line in ocr_text.split('\n'):
    if any(k in line for k in ['Point', 'Area', 'MVA', 'Latitude', 'Longitude', 'ARP', 'Boundary', 'FIR', 'Border']):
        print(line)
