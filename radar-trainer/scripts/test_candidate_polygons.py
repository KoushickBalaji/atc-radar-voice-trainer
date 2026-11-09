"""Test polygon and arc parsing across candidate airports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from airport_profiles import get_profile
from control_area import boundary
from parse_airspace_geometry import parse_polygon

enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))

test_list = [
    'VILK', 'VABP', 'VOVI', 'VEBS', 'VEPT', 'VOTR', 'VAAU', 'VAGD', 'VAID',
    'VASD', 'VASU', 'VERW', 'VOKN', 'VOMY', 'VORY'
]

for code in test_list:
    prof = get_profile(code)
    print(f'=== Testing {code} ({prof.NAME}) ===')
    
    # Test AD 2.17 polygon if applicable
    ad = ad17[code]
    sec1 = ad['sec1']
    if 'area bounded' in sec1.lower() or 'lines joining' in sec1.lower():
        try:
            edges = parse_polygon(sec1, prof)
            pts = boundary(prof, {'shape': 'polygon', 'edges': edges})
            print(f'  [AD 2.17 CTR] Valid polygon with {len(edges)} edges -> {len(pts)} points')
        except Exception as e:
            print(f'  [AD 2.17 CTR] Failed: {e}')
            
    # Test ENR 2.1 areas
    areas = enr21.get(code, [])
    for i, a in enumerate(areas):
        cell0 = a['cell0']
        title = a['title']
        if 'border' in cell0.lower():
            print(f'  [ENR {title}] Skipped (border)')
            continue
        if 'circular area' in cell0.lower() or 'circle of radius' in cell0.lower():
            continue
        try:
            edges = parse_polygon(cell0, prof)
            pts = boundary(prof, {'shape': 'polygon', 'edges': edges})
            print(f'  [ENR {title}] Valid polygon with {len(edges)} edges -> {len(pts)} points')
        except Exception as e:
            print(f'  [ENR {title}] Failed: {e}')
