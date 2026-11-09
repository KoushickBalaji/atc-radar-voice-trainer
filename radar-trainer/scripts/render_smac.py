import sys
from pathlib import Path
import fitz

sys.stdout.reconfigure(encoding='utf-8')

airports = [
    ('VEAT', r'D:\ATC\Airport Layouts\Agartala\VEAT-ATC-SMAC.pdf'),
    ('VIAR', r'D:\ATC\Airport Layouts\Amritsar\VIAR-ATC-SMAC.pdf'),
    ('VOBG', r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf'),
    ('VOVI', r'D:\ATC\Airport Layouts\Bhogapuram\VOVI-ATC-SMAC.pdf'),
    ('VEBS', r'D:\ATC\Airport Layouts\Bhubaneswar\VEBS-ATC-SMAC.pdf'),
    ('VOCL', r'D:\ATC\Airport Layouts\Calicut\VOCL-ATC-SMAC.PDF'),
    ('VOCI', r'D:\ATC\Airport Layouts\Cochin\VOCI-ATC-SMAC.PDF'),
    ('VEGT', r'D:\ATC\Airport Layouts\Guwahati\VEGT-ATC-SMAC.pdf'),
    ('VIJP', r'D:\ATC\Airport Layouts\Jaipur\VIJP-ATC-SMAC.pdf'),
    ('VILK', r'D:\ATC\Airport Layouts\Lucknow\VILK-ATC-SMAC.pdf'),
    ('VANP', r'D:\ATC\Airport Layouts\Nagpur\VANP-ATC-SMAC.pdf'),
    ('VEPT', r'D:\ATC\Airport Layouts\Patna\VEPT-ATC-SMAC.pdf'),
    ('VOTR', r'D:\ATC\Airport Layouts\Tiruchirappalli\VOTR-ATC-SMAC.pdf'),
    ('VEBN', r'D:\ATC\Airport Layouts\Varanasi\VEBN-ATC-SMAC.pdf'),
]

img_dir = Path(r'D:\ATC\radar-trainer\scratch\smac_images')
img_dir.mkdir(parents=True, exist_ok=True)

for icao, p in airports:
    doc = fitz.open(p)
    page = doc[0]
    pix = page.get_pixmap(dpi=200)
    out_path = img_dir / f'{icao}.png'
    pix.save(str(out_path))
    print(f'Rendered {icao}: {pix.width}x{pix.height} -> {out_path.name}')
