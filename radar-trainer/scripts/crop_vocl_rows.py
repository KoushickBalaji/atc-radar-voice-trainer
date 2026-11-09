import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Calicut\VOCL-ATC-SMAC.PDF')
page = doc[0]
# render at 400 DPI
pix = page.get_pixmap(dpi=400)
# crop around table: in 400 DPI, page is approx 3300 x 4678
# table x ~ 400 to 1400, y ~ 3200 to 4300
crop = pix.tobytes("png")
from PIL import Image
import io
im = Image.open(io.BytesIO(crop))
w, h = im.size
# crop rows 10-16: y from 0.8 to 0.92, x from 0.12 to 0.42
sub = im.crop((int(w * 0.12), int(h * 0.8), int(w * 0.42), int(h * 0.92)))
sub.save(r'D:\ATC\radar-trainer\scratch\VOCL_table_rows_10_16.png')
print('Rows 10-16 saved at 400 DPI.')
