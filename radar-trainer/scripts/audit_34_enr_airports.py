"""Detailed audit of the 34 airports with ENR 2.1 entries."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from airport_profiles import get_profile
from control_area import validate, boundary
from parse_airspace_geometry import parse_polygon, parse_first_coord
import test_classify as tc

enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))

airports_with_enr = [k for k, v in enr21.items() if v]

print(f'Total airports with ENR 2.1 entries: {len(airports_with_enr)}')

def audit_airport_enr(code):
    prof = get_profile(code)
    ad = ad17[code]
    enr_rows = enr21[code]
    
    # deduplicate enr rows by cell0 text
    seen_cells = set()
    unique_enr = []
    for r in enr_rows:
        c0 = ' '.join(r['cell0'].split())
        if c0 not in seen_cells:
            seen_cells.add(c0)
            unique_enr.append(r)
            
    # Check CTR
    ad_sec1 = ad['sec1']
    ad_sec2 = ad['sec2']
    ad_sec3 = ad['sec3']
    ad_sec6 = ad['sec6']
    
    ctr_area = None
    ctr_error = None
    
    # Try circle CTR
    circ_m = re.search(r'circular area\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+?)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', ad_sec1, re.I)
    if not circ_m:
        circ_m = re.search(r'circular area\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
    if not circ_m:
        circ_m = re.search(r'circle\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
    if not circ_m:
        circ_m = re.search(r'circle\s+of\s+(\d+(?:\.\d+)?)\s*NM\s+radius\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
        
    if circ_m:
        # circle
        if len(circ_m.groups()) == 2:
            try:
                rad = float(circ_m[1])
                c_pt = parse_first_coord(circ_m[2])
            except:
                rad = float(circ_m[2])
                c_pt = parse_first_coord(circ_m[1])
        v_up = tc.parse_vert(ad_sec2)
        if v_up and v_up['reference'] in ('AMSL', 'FL'):
            cls = ad_sec3.strip().split()[0].replace("'", "").replace("’", "") if ad_sec3 else 'D'
            hrs = 'H24' if 'H24' in ad_sec6.upper() else (ad_sec6.strip() if ad_sec6 else 'HO')
            ctr_area = {
                'id': 'ctr',
                'name': f'{prof.NAME} CTR',
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
                    'evidence': f'AD 2.17: {ad_sec1} | Vertical: {ad_sec2}'
                },
                'shape': 'circle',
                'center': c_pt,
                'radius_nm': rad
            }
        else:
            ctr_error = f'Invalid CTR vertical: {ad_sec2}'
    else:
        # try polygon CTR (like VOCB)
        if 'point of origin' in ad_sec1.lower() and not re.search(r'border|river', ad_sec1, re.I):
            try:
                edges = parse_polygon(ad_sec1, prof)
                v_up = tc.parse_vert(ad_sec2)
                if v_up and v_up['reference'] in ('AMSL', 'FL'):
                    cls = ad_sec3.strip().split()[0].replace("'", "").replace("’", "") if ad_sec3 else 'D'
                    hrs = 'H24' if 'H24' in ad_sec6.upper() else (ad_sec6.strip() if ad_sec6 else 'HO')
                    ctr_area = {
                        'id': 'ctr',
                        'name': f'{prof.NAME} CTR',
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
                            'evidence': f'AD 2.17: {ad_sec1} | Vertical: {ad_sec2}'
                        },
                        'shape': 'polygon',
                        'edges': edges
                    }
                    # test boundary
                    boundary(prof, ctr_area)
                else:
                    ctr_error = f'Invalid CTR vertical: {ad_sec2}'
            except Exception as e:
                ctr_error = f'CTR polygon failed: {e}'
        else:
            ctr_error = f'CTR not parsed / border-cut'
            
    # Now check ENR areas
    enr_areas = []
    enr_errors = []
    for idx, row in enumerate(unique_enr):
        c0 = row['cell0']
        title = row['title']
        
        # Check border
        if re.search(r'border|river|line of control', c0, re.I):
            enr_errors.append(f'{title}: Clipped by border or river without coordinates')
            continue
            
        # Check if circle
        circ_m2 = re.search(r'(?:circular area|circle)\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', c0, re.I)
        if not circ_m2:
            circ_m2 = re.search(r'(?:circular area|circle)\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+?)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', c0, re.I)
            if circ_m2:
                rad2 = float(circ_m2[2])
                c_pt2 = parse_first_coord(circ_m2[1])
            else:
                rad2 = None
                c_pt2 = None
        else:
            rad2 = float(circ_m2[1])
            c_pt2 = parse_first_coord(circ_m2[2])
            
        # Extract vertical limits: e.g. "FL 65 / 1000 FT AMSL" or "5500 FT AMSL / 2000 FT AMSL"
        # Look for pattern: <upper> / <lower>
        v_m = re.search(r'(FL\s*\d+|\d+\s*FT(?:\s*AMSL)?)\s*/\s*(FL\s*\d+|\d+\s*FT(?:\s*AMSL)?|SFC)', c0, re.I)
        if not v_m:
            enr_errors.append(f'{title}: Vertical limits not extractable')
            continue
        v_upper = tc.parse_vert(v_m[1])
        v_lower = {'reference': 'SFC'} if 'SFC' in v_m[2].upper() else tc.parse_vert(v_m[2])
        if not v_upper or not v_lower:
            enr_errors.append(f'{title}: Failed parsing vertical limits {v_m.group(0)}')
            continue
            
        # Excludes
        excludes = []
        if 'excluding' in c0.lower() and 'ctr' in c0.lower():
            if ctr_area:
                excludes.append('ctr')
                
        # Check complex exclusions like restricted areas
        if re.search(r'restricted area|flying zone|vor\s*\d+|except', c0, re.I):
            enr_errors.append(f'{title}: Unsupported complex exclusion (military/restricted area)')
            continue
            
        hrs = 'H24' if 'H24' in row['callsign_hours'].upper() else 'HO'
        
        area_id = f'cta-{idx+1}'
        if rad2 and c_pt2:
            area_obj = {
                'id': area_id,
                'name': f'{prof.NAME} {title}'.strip(),
                'kind': 'CTA',
                'classification': 'D',
                'hours': hrs,
                'lower': v_lower,
                'upper': v_upper,
                'excludes': excludes,
                'source': {
                    'url': 'https://aim-india.aai.aero/eaip/eaip-v2-07-2026/eAIP/IN-ENR%202.1-en-GB.html',
                    'section': 'ENR 2.1',
                    'edition': 'July 2026',
                    'evidence': c0
                },
                'shape': 'circle',
                'center': c_pt2,
                'radius_nm': rad2
            }
            try:
                boundary(prof, area_obj)
                enr_areas.append(area_obj)
            except Exception as e:
                enr_errors.append(f'{title}: Circle boundary failed: {e}')
        else:
            # Try polygon
            try:
                edges = parse_polygon(c0, prof)
                area_obj = {
                    'id': area_id,
                    'name': f'{prof.NAME} {title}'.strip(),
                    'kind': 'CTA',
                    'classification': 'D',
                    'hours': hrs,
                    'lower': v_lower,
                    'upper': v_upper,
                    'excludes': excludes,
                    'source': {
                        'url': 'https://aim-india.aai.aero/eaip/eaip-v2-07-2026/eAIP/IN-ENR%202.1-en-GB.html',
                        'section': 'ENR 2.1',
                        'edition': 'July 2026',
                        'evidence': c0
                    },
                    'shape': 'polygon',
                    'edges': edges
                }
                boundary(prof, area_obj)
                enr_areas.append(area_obj)
            except Exception as e:
                enr_errors.append(f'{title}: Polygon failed: {e}')
                
    return {
        'code': code,
        'name': prof.NAME,
        'ctr_ok': ctr_area is not None,
        'ctr_error': ctr_error,
        'ctr_area': ctr_area,
        'enr_count_published': len(unique_enr),
        'enr_areas_parsed': enr_areas,
        'enr_errors': enr_errors
    }

for c in airports_with_enr:
    res = audit_airport_enr(c)
    print(f'=== {c} ({res["name"]}) ===')
    print(f'  CTR: {"OK" if res["ctr_ok"] else "FAIL - " + str(res["ctr_error"])}')
    print(f'  ENR: {len(res["enr_areas_parsed"])} / {res["enr_count_published"]} valid')
    if res['enr_errors']:
        for err in res['enr_errors']:
            print(f'    * {err}')
