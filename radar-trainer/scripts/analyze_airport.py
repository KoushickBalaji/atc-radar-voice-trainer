import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

icao = sys.argv[1].upper() if len(sys.argv) > 1 else 'VOBG'

pdf_txt_path = Path(rf'D:\ATC\radar-trainer\scratch\smac_text\{icao}.txt')
ocr_txt_path = Path(rf'D:\ATC\radar-trainer\scratch\smac_ocr\{icao}.txt')

print(f'============================== {icao} DIRECT PDF TEXT ==============================')
if pdf_txt_path.exists():
    print(pdf_txt_path.read_text(encoding='utf-8'))
else:
    print('None')

print(f'============================== {icao} WINRT OCR TEXT ==============================')
if ocr_txt_path.exists():
    print(ocr_txt_path.read_text(encoding='utf-8'))
else:
    print('None')
