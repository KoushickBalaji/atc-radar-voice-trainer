import re

text = open(r'D:\ATC\radar-trainer\scratch\smac_text\VOBG.txt', encoding='utf-8').read()
pt_pattern = re.compile(r'([A-Z])\s+(\d{2})[°\ufffd](\d{2})\'([\d.]+)\"N\s+(\d{3})[°\ufffd](\d{2})\'([\d.]+)\"E')
pts = {}
for m in pt_pattern.finditer(text):
    letter = m.group(1)
    lat = int(m.group(2)) + int(m.group(3))/60 + float(m.group(4))/3600
    lon = int(m.group(5)) + int(m.group(6))/60 + float(m.group(7))/3600
    pts[letter] = [round(lat, 8), round(lon, 8)]

print(f'Total points found: {len(pts)}')
for k in sorted(pts):
    print(f'{k}: {pts[k]}')
