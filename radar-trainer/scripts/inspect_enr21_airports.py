"""Inspect ENR 2.1 entries for the 34 airports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))

for code, areas in enr21.items():
    if not areas: continue
    print(f'=== {code} ({len(areas)} areas) ===')
    for a in areas:
        cell0 = a['cell0']
        title = a['title']
        unit = a['unit']
        # Extract vertical limit from cell0
        # Usually format: • upper / lower or FL xxx / yyy FT AMSL
        vert = re.findall(r'(?:FL\s*\d+|\d+\s*FT\s*(?:AMSL)?)\s*/\s*(?:FL\s*\d+|\d+\s*FT\s*(?:AMSL)?|SFC)', cell0, re.I)
        print(f'  - {title}: Unit={unit} | Verticals={vert}')
        # check for border / river
        if re.search(r'border|river|line of control', cell0, re.I):
            print(f'    * CONTAINS BORDER/RIVER')
