"""Test classification and geometry validation for all 124 airports."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUTS = Path('d:/ATC/Airport Layouts')
CACHE = Path('d:/ATC/tmp/airport-audit')

import sys
sys.path.insert(0, str(ROOT / 'src'))
from airport_profiles import get_profile
from control_area import validate, boundary

def parse_dms(coord_str):
    m = re.search(r'(\d{6}(?:\.\d+)?)\s*([NS])\s*(\d{7}(?:\.\d+)?)\s*([EW])', coord_str, re.I)
    if not m:
        m2 = re.search(r'(\d{6}(?:\.\d+)?)[NS]\s*(\d{7}(?:\.\d+)?)[EW]', coord_str, re.I)
        if m2:
            raw = coord_str[m2.start():m2.end()]
            ns = 'N' if 'N' in raw.upper() else 'S'
            ew = 'E' if 'E' in raw.upper() else 'W'
            return [convert_dms(m2[1], ns), convert_dms(m2[2], ew)]
        return None
    return [convert_dms(m[1], m[2]), convert_dms(m[3], m[4])]

def convert_dms(val, hemisphere):
    deglen = 2 if hemisphere in 'NS' else 3
    deg = int(val[:deglen])
    minutes = int(val[deglen:deglen+2])
    sec = float(val[deglen+2:])
    res = deg + minutes / 60.0 + sec / 3600.0
    return -res if hemisphere in 'SW' else res

def parse_vert(text):
    text = text.strip()
    if not text: return None
    # Check AGL
    if re.search(r'AGL', text, re.I):
        m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)?\s*AGL', text, re.I)
        return {'reference': 'AGL', 'value': float(m[1].replace(',', '')) if m else 0}
    # Check FL
    m = re.search(r'\bFL\s*(\d+)\b', text, re.I)
    if m:
        return {'reference': 'FL', 'value': int(m[1])}
    # Check AMSL
    m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)?\s*AMSL', text, re.I)
    if m:
        return {'reference': 'AMSL', 'value': float(m[1].replace(',', ''))}
    m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)\b', text, re.I)
    if m:
        return {'reference': 'AMSL', 'value': float(m[1].replace(',', ''))}
    return None

def test_airports():
    ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
    enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
    airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])
    profiles = {code: json.loads((ROOT / f'data/airports/{code}.json').read_text(encoding='utf-8')) for code in airports}
    
    results = {}
    
    for code in airports:
        ad = ad17[code]
        enr = enr21.get(code, [])
        name = profiles[code]['name']
        
        issues = []
        areas = []
        
        # 1. Inspect AD 2.17
        sec1 = ad['sec1']
        sec2 = ad['sec2']
        sec3 = ad['sec3']
        sec6 = ad['sec6']
        
        if not sec1 or 'not established' in sec1.lower() or 'not established' in sec2.lower():
            issues.append('CTR Not Established in AD 2.17')
        elif 'nil' in sec1.lower() or len(sec1) < 10:
            issues.append('No ATS airspace in AD 2.17 (NIL)')
        elif re.search(r'border|river|line of control|international boundary', sec1, re.I) and not re.search(r'circular area of radius \d+ NM centered', sec1, re.I):
            issues.append('CTR boundary clipped by international border or river without numerical coordinates')
        elif 'vicinity of ad' in sec1.lower():
            issues.append('CTR boundary unquantified: within vicinity of AD')
        else:
            # Try parsing CTR circle
            # Formats:
            # "Circular area centered on 230416N 0723735E within a 15NM radius"
            # "Circle of radius 10 NM centered on 264936N 0805306E"
            # "Circular area of radius 15 NM centered at 100913N 0762419E"
            # "Circle of 12 NM radius centered on 125743N 0745323E"
            circ_m = re.search(r'circular area\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+?)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', sec1, re.I)
            if not circ_m:
                circ_m = re.search(r'circle\s+(?:of\s+radius\s+)?(\d+(?:\.\d+)?)\s*NM(?:\s+radius)?\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', sec1, re.I)
                if circ_m:
                    rad = float(circ_m[1])
                    c_pt = parse_dms(circ_m[2])
                else:
                    rad = None
                    c_pt = None
            else:
                rad = float(circ_m[2])
                c_pt = parse_dms(circ_m[1])
                
            if rad and c_pt:
                v_up = parse_vert(sec2)
                if not v_up:
                    issues.append(f'CTR vertical limit not parsed: "{sec2}"')
                elif v_up['reference'] == 'AGL':
                    issues.append(f'CTR vertical limit has unsupported AGL reference: "{sec2}"')
                else:
                    cls = sec3.strip().split()[0].replace("'", "").replace("’", "") if sec3 else 'D'
                    hrs = 'H24' if 'H24' in sec6.upper() else (sec6.strip() if sec6 else 'HO')
                    areas.append({
                        'id': 'ctr',
                        'name': f'{name} CTR',
                        'kind': 'CTR',
                        'classification': cls,
                        'hours': hrs,
                        'lower': {'reference': 'SFC'},
                        'upper': v_up,
                        'excludes': [],
                        'source': {
                            'file': ad['pdf_file'],
                            'page': ad['page'],
                            'section': 'AD 2.17',
                            'evidence': f'AD 2.17: {sec1} | Vertical: {sec2} | Class: {sec3} | Hours: {sec6}'
                        },
                        'shape': 'circle',
                        'center': c_pt,
                        'radius_nm': rad
                    })
            else:
                issues.append(f'CTR geometry is complex polygon/arc or unparsed: "{sec1[:80]}"')
                
        # 2. Inspect ENR 2.1
        if enr:
            for i, ea in enumerate(enr):
                cell0 = ea['cell0']
                title = ea['title']
                if re.search(r'border|river|line of control', cell0, re.I):
                    issues.append(f'ENR 2.1 {title} clipped by border/river')
                elif re.search(r'portions of|excluding airspace of|excluding.*CTR', cell0, re.I) and not re.search(r'excluding (?:the )?airspace contained within\s+' + re.escape(name) + r'\s+CTR', cell0, re.I):
                    # Complex exclusions like restricted areas, multiple CTAs, etc.
                    issues.append(f'ENR 2.1 {title} has complex exclusions: {cell0[:100]}')
                    
        results[code] = {
            'icao': code,
            'name': name,
            'areas': areas,
            'issues': issues,
            'enr_count': len(enr)
        }
        
    return results

if __name__ == '__main__':
    res = test_airports()
    clean = [k for k, v in res.items() if not v['issues'] and v['enr_count'] == 0]
    clean_with_enr = [k for k, v in res.items() if not v['issues'] and v['enr_count'] > 0]
    with_issues = [k for k, v in res.items() if v['issues']]
    
    print(f'Total airports: {len(res)}')
    print(f'Clean CTR only (no ENR CTA): {len(clean)}')
    print(f'Clean CTR + potential ENR: {len(clean_with_enr)}')
    print(f'With issues: {len(with_issues)}')
