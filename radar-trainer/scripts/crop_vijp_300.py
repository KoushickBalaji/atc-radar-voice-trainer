import fitz
from PIL import Image
import io

doc = fitz.open(r'D:\ATC\Airport Layouts\Jaipur\VIJP-ATC-SMAC.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=300)
im = Image.open(io.BytesIO(pix.tobytes("png")))
w, h = im.size

# In VIJP, the table is at y ~ 0.65 to 0.9, x ~ 0.05 to 0.6
crop = im.crop((int(w * 0.05), int(h * 0.65), int(w * 0.55), int(h * 0.9)))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_table_300dpi.png')
print('VIJP table 300 DPI saved.')
