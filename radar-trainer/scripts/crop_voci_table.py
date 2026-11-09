import fitz
from PIL import Image
import io

doc = fitz.open(r'D:\ATC\Airport Layouts\Cochin\VOCI-ATC-SMAC.PDF')
page = doc[0]
pix = page.get_pixmap(dpi=300)
im = Image.open(io.BytesIO(pix.tobytes("png")))
w, h = im.size

# In 300 DPI, page is approx 2480 x 3508
# Table was at X ~ 200..700 in 200 DPI (approx X=300..1050 in 300 DPI, Y=2400..3300 in 300 DPI)
crop = im.crop((int(w * 0.1), int(h * 0.65), int(w * 0.55), int(h * 0.95)))
crop.save(r'D:\ATC\radar-trainer\scratch\VOCI_table_clean.png')
print('VOCI table cropped.')
