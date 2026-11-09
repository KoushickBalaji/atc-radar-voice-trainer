import re

text = open(r'D:\ATC\radar-trainer\scratch\smac_ocr\VOTR.txt', encoding='utf-8').read()
for line in text.split('\n'):
    if any(k in line for k in ['AREA', 'MVA', 'TR36', 'Boundary', 'Latitude', 'Longitude', 'ARP', '25NM', '20NM', '15NM', '10NM']):
        print(line)
