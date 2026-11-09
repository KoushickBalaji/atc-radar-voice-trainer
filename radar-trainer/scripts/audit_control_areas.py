"""Comprehensive audit of AD 2.17 and ENR 2.1 for all 124 airports."""
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUTS = Path('d:/ATC/Airport Layouts')
CACHE = Path('d:/ATC/tmp/airport-audit')

COORD_RE = re.compile(r'(\d{6}(?:\.\d+)?)\s*([NS])\s*(\d{7}(?:\.\d+)?)\s*([EW])', re.I)
DMS_RE = re.compile(r'(\d{6}(?:\.\d+)?)[NS]\s*(\d{7}(?:\.\d+)?)[EW]', re.I)

def dms(deg_min_sec, hemisphere):
    deglen = 2 if hemisphere in 'NS' else 3
    degrees = int(deg_min_sec[:deglen])
    minutes = int(deg_min_sec[deglen:deglen+2])
    seconds = float(deg_min_sec[deglen+2:])
    val = degrees + minutes / 60.0 + seconds / 3600.0
    return -val if hemisphere in 'SW' else val

def parse_coord(coord_str):
    m = COORD_RE.search(coord_str)
    if not m:
        m2 = re.search(r'(\d{6}(?:\.\d+)?)[NS]\s*(\d{7}(?:\.\d+)?)[EW]', coord_str, re.I)
        if m2:
            # extract hemisphere
            raw = coord_str[m2.start():m2.end()]
            ns = 'N' if 'N' in raw.upper() else 'S'
            ew = 'E' if 'E' in raw.upper() else 'W'
            return [dms(m2[1], ns), dms(m2[2], ew)]
        return None
    return [dms(m[1], m[2]), dms(m[3], m[4])]

def parse_vertical_limit(text):
    text = text.strip()
    if not text:
        return None
    # Check for FL
    fl_m = re.search(r'\bFL\s*(\d+)\b', text, re.I)
    # Check for AMSL
    amsl_m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)?\s*AMSL', text, re.I)
    # Check for AGL
    agl_m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)?\s*AGL', text, re.I)
    
    if agl_m:
        return {'reference': 'AGL', 'value': float(agl_m[1].replace(',', ''))}
    if fl_m:
        return {'reference': 'FL', 'value': int(fl_m[1])}
    if amsl_m:
        return {'reference': 'AMSL', 'value': float(amsl_m[1].replace(',', ''))}
    # Plain feet
    ft_m = re.search(r'(\d+(?:,\d+)?)\s*(?:FT|FEET)\b', text, re.I)
    if ft_m:
        return {'reference': 'AMSL', 'value': float(ft_m[1].replace(',', ''))}
    return None

def main():
    ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
    enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
    airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])
    profiles = {code: json.loads((ROOT / f'data/airports/{code}.json').read_text(encoding='utf-8')) for code in airports}
    
    summary = {}
    
    for code in airports:
        ad = ad17.get(code, {})
        enr = enr21.get(code, [])
        name = profiles[code]['name']
        
        ad_sec1 = ad.get('sec1', '')
        ad_sec2 = ad.get('sec2', '')
        ad_sec3 = ad.get('sec3', '')
        ad_sec6 = ad.get('sec6', '')
        
        # Analyze AD 2.17
        ad_status = 'ok'
        ad_issues = []
        ad_areas = []
        
        if not ad_sec1 or 'not established' in ad_sec1.lower() or 'not established' in ad_sec2.lower():
            ad_status = 'not_established'
            ad_issues.append('CTR Not Established')
        elif 'nil' in ad_sec1.lower() or len(ad_sec1) < 10:
            ad_status = 'nil'
            ad_issues.append('No ATS airspace in AD 2.17')
        elif re.search(r'border|river|line of control|international boundary', ad_sec1, re.I) and not re.search(r'circular area of radius \d+ NM centered', ad_sec1, re.I):
            ad_status = 'border_clipped'
            ad_issues.append('Boundary clipped by international border or river without numerical coordinates')
        elif 'vicinity of ad' in ad_sec1.lower():
            ad_status = 'unquantified'
            ad_issues.append('Boundary unquantified: within vicinity of AD')
        else:
            # Check for circle
            circ_m = re.search(r'circular area\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', ad_sec1, re.I)
            if not circ_m:
                circ_m = re.search(r'circle of radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
                if circ_m:
                    rad = float(circ_m[1])
                    c_pt = parse_coord(circ_m[2])
                else:
                    rad = None
                    c_pt = None
            else:
                rad = float(circ_m[2])
                c_pt = parse_coord(circ_m[1])
                
            if circ_m and rad and c_pt:
                # Vertical limit
                v_upper = parse_vertical_limit(ad_sec2)
                if not v_upper:
                    ad_status = 'unclear_vertical'
                    ad_issues.append(f'Vertical limit not parsed: "{ad_sec2}"')
                elif v_upper['reference'] == 'AGL':
                    ad_status = 'agl_limit'
                    ad_issues.append(f'Vertical limit has AGL reference: "{ad_sec2}"')
                else:
                    cls = ad_sec3.strip().split()[0].replace("'", "").replace("’", "") if ad_sec3 else 'D'
                    hrs = 'H24' if 'H24' in ad_sec6.upper() else (ad_sec6.strip() if ad_sec6 else 'HO')
                    ad_areas.append({
                        'id': 'ctr',
                        'name': f'{name} CTR',
                        'kind': 'CTR',
                        'classification': cls,
                        'hours': hrs,
                        'lower': {'reference': 'SFC'},
                        'upper': v_upper,
                        'excludes': [],
                        'source': {
                            'file': ad['pdf_file'],
                            'page': ad['page'],
                            'section': 'AD 2.17',
                            'evidence': f'AD 2.17: {ad_sec1} Vertical: {ad_sec2} Class: {ad_sec3} Hours: {ad_sec6}'
                        },
                        'shape': 'circle',
                        'center': c_pt,
                        'radius_nm': rad
                    })
            else:
                # Check if complex polygon/arc
                ad_status = 'complex_or_unparsed'
                ad_issues.append(f'AD 2.17 geometry not simple circle: "{ad_sec1[:100]}"')
                
        # Analyze ENR 2.1
        enr_status = 'none' if not enr else 'present'
        enr_issues = []
        for row in enr:
            cell0 = row['cell0']
            if re.search(r'border|river|line of control', cell0, re.I):
                enr_issues.append(f'Border reference in {row["title"]}')
                
        summary[code] = {
            'icao': code,
            'name': name,
            'ad_status': ad_status,
            'ad_issues': ad_issues,
            'ad_areas': ad_areas,
            'enr_count': len(enr),
            'enr_issues': enr_issues
        }
        
    return summary

if __name__ == '__main__':
    res = main()
    ad_ok = [k for k, v in res.items() if v['ad_status'] == 'ok']
    ad_border = [k for k, v in res.items() if v['ad_status'] == 'border_clipped']
    ad_not_est = [k for k, v in res.items() if v['ad_status'] == 'not_established']
    ad_nil = [k for k, v in res.items() if v['ad_status'] == 'nil']
    ad_complex = [k for k, v in res.items() if v['ad_status'] == 'complex_or_unparsed']
    ad_other = [k for k, v in res.items() if v['ad_status'] not in ('ok', 'border_clipped', 'not_established', 'nil', 'complex_or_unparsed')]
    
    print(f'Total airports: {len(res)}')
    print(f'AD 2.17 OK (clean circle): {len(ad_ok)}')
    print(f'AD 2.17 Border clipped: {len(ad_border)} -> {ad_border}')
    print(f'AD 2.17 Not Established: {len(ad_not_est)} -> {ad_not_est}')
    print(f'AD 2.17 NIL/missing: {len(ad_nil)} -> {ad_nil}')
    print(f'AD 2.17 Complex/unparsed: {len(ad_complex)} -> {ad_complex}')
    print(f'AD 2.17 Other: {len(ad_other)} -> {ad_other}')
