"""Check vertical limits for circle airports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'scripts'))
import test_classify as tc

ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))

circle_codes = []
for code, d in ad17.items():
    sec1 = d['sec1']
    m = re.search(r'circular area\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+?)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', sec1, re.I)
    if not m:
        m = re.search(r'circular area\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', sec1, re.I)
    if not m:
        m = re.search(r'circle\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', sec1, re.I)
    if not m:
        m = re.search(r'circle\s+of\s+(\d+(?:\.\d+)?)\s*NM\s+radius\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', sec1, re.I)
    if not m:
        m = re.search(r'within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s+radius\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', sec1, re.I)
    if m:
        circle_codes.append(code)

vert_ok = []
vert_fail = []

for code in circle_codes:
    d = ad17[code]
    sec2 = d['sec2']
    v = tc.parse_vert(sec2)
    if v and v['reference'] in ('AMSL', 'FL'):
        vert_ok.append((code, v))
    else:
        vert_fail.append((code, sec2, v))

print(f'Vertical limits OK: {len(vert_ok)} / {len(circle_codes)}')
print(f'Vertical limits Fail: {len(vert_fail)}')
for c, s, v in vert_fail:
    print(f'  {c}: raw="{s}" parsed={v}')
