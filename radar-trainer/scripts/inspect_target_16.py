"""Detailed inspection of the 16 core airports (14 SMAC + VOCB + VOML)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))

target_16 = [
    'VEAT', 'VIAR', 'VOBG', 'VOVI', 'VEBS', 'VOCL', 'VOCI', 'VEGT',
    'VIJP', 'VILK', 'VANP', 'VEPT', 'VOTR', 'VEBN', 'VOCB', 'VOML'
]

for code in target_16:
    ad = ad17[code]
    enr = enr21.get(code, [])
    print(f'==============================')
    print(f'AIRPORT: {code} ({ad["name"]})')
    print(f'PDF: {ad["pdf_file"]} Page: {ad["page"]}')
    print(f'AD 2.17 Sec 1: {ad["sec1"]}')
    print(f'AD 2.17 Sec 2: {ad["sec2"]}')
    print(f'AD 2.17 Sec 3: {ad["sec3"]}')
    print(f'AD 2.17 Sec 6: {ad["sec6"]}')
    print(f'ENR 2.1 Areas: {len(enr)}')
    for a in enr:
        print(f'  - Title: {a["title"]}')
        print(f'    Cell0: {a["cell0"][:200]}...')
        print(f'    Unit: {a["unit"]} | Hours: {a["callsign_hours"]}')
