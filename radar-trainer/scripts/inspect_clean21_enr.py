"""Inspect ENR 2.1 geometry for the 21 clean CTR airports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))

clean_21 = [
    'VAAU', 'VABO', 'VABP', 'VABV', 'VAGD', 'VAHS', 'VAID', 'VANP', 'VASD', 'VASU',
    'VAUD', 'VEBS', 'VEGY', 'VEPT', 'VERC', 'VERW', 'VILK', 'VOCL', 'VOKN', 'VOMY', 'VORY'
]

for code in clean_21:
    areas = enr21[code]
    print(f'=== {code} ({len(areas)} rows) ===')
    for i, a in enumerate(areas):
        cell0 = a['cell0']
        # remove duplicates
        print(f'  Row {i+1}: {cell0[:180]}...')
