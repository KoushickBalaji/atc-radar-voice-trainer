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

out_dir = Path(r'D:\ATC\radar-trainer\scratch\smac_text')
out_dir.mkdir(parents=True, exist_ok=True)

for icao, p in airports:
    doc = fitz.open(p)
    text = doc[0].get_text()
    out_file = out_dir / f'{icao}.txt'
    out_file.write_text(text, encoding='utf-8')
    print(f'=== {icao}: {len(text)} chars saved to {out_file.name} ===')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    kw_lines = [l for l in lines if any(k in l.upper() for k in ['SECTOR', 'AREA', 'ALTITUDE', 'MINIMUM', 'NM', 'WGS', 'MVA', 'SMA', 'CONTOUR', 'TABLE'])]
    print(f'  Total lines: {len(lines)}, Keyword lines: {len(kw_lines)}')
    for l in kw_lines[:10]:
        print('   ', l)
