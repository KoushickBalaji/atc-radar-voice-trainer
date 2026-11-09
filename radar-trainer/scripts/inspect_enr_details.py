"""Inspect full text of ENR 2.1 for the target airports."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))

for code in ['VEBS', 'VEPT', 'VEBN', 'VILK', 'VIJP', 'VANP', 'VIAR', 'VOCL', 'VOCI', 'VOTR', 'VOVI', 'VOML']:
    areas = enr21.get(code, [])
    print(f'================ {code} ({len(areas)} areas) ================')
    for i, a in enumerate(areas):
        print(f'Area {i+1}: {a["title"]}')
        print(f'Cell0: {a["cell0"]}')
        print(f'Unit: {a["unit"]}')
        print(f'Callsign/Hours: {a["callsign_hours"]}')
        print('-'*40)
