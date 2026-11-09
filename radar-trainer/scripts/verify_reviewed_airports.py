"""Verify all 77 reviewed control areas."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from airport_profiles import get_profile
from control_area import validate, boundary, ControlAreas
import test_classify as tc
from parse_airspace_geometry import parse_polygon, parse_first_coord

ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])

# Airports with multi-sector/unresolved CTA that must remain drafts
draft_overrides = {'VABO', 'VAID', 'VANP', 'VASU', 'VIJP', 'VERW'}

reviewed = {}
drafts = {}

for code in airports:
    prof = get_profile(code)
    ad = ad17[code]
    enr_rows = enr21.get(code, [])
    name = prof.NAME
    
    if code in draft_overrides:
        drafts[code] = f'CTA has complex concentric/nested/external exclusions or multiple combined areas in single cell'
        continue
        
    # VOCB existing
    if code == 'VOCB':
        path = ROOT / 'data/control_areas/VOCB.json'
        reviewed[code] = json.loads(path.read_text(encoding='utf-8'))
        continue
        
    ad_sec1 = ad['sec1']
    ad_sec2 = ad['sec2']
    ad_sec3 = ad['sec3']
    ad_sec6 = ad['sec6']
    
    issues = []
    areas = []
    
    # 1. Parse CTR
    if not ad_sec1 or 'not established' in ad_sec1.lower() or 'not established' in ad_sec2.lower():
        issues.append('CTR Not Established in AD 2.17')
    elif 'nil' in ad_sec1.lower() or len(ad_sec1) < 10:
        issues.append('No ATS airspace in AD 2.17 (NIL)')
    elif re.search(r'border|river|line of control|international boundary', ad_sec1, re.I) and not re.search(r'circular area of radius \d+ NM centered', ad_sec1, re.I):
        issues.append('CTR boundary clipped by international border or river without numerical coordinates')
    elif 'vicinity of ad' in ad_sec1.lower():
        issues.append('CTR boundary unquantified: within vicinity of AD')
    else:
        circ_m = re.search(r'circular area\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+?)\s+within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s*radius', ad_sec1, re.I)
        if not circ_m:
            circ_m = re.search(r'circular area\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
        if not circ_m:
            circ_m = re.search(r'circle\s+of\s+radius\s+(\d+(?:\.\d+)?)\s*NM\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
        if not circ_m:
            circ_m = re.search(r'circle\s+of\s+(\d+(?:\.\d+)?)\s*NM\s+radius\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
        if not circ_m:
            circ_m = re.search(r'within\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*NM\s+radius\s+(?:centered|centred)\s+(?:at|on)\s+([0-9NSEW\s\.]+)', ad_sec1, re.I)
            
        if circ_m:
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
                        'evidence': f'AD 2.17: {ad_sec1} | Vertical: {ad_sec2} | Class: {ad_sec3} | Hours: {ad_sec6}'
                    },
                    'shape': 'circle',
                    'center': c_pt,
                    'radius_nm': rad
                })
            else:
                issues.append(f'Invalid or missing CTR vertical limits: "{ad_sec2}"')
        else:
            if 'point of origin' in ad_sec1.lower() and not re.search(r'border|river', ad_sec1, re.I):
                try:
                    edges = parse_polygon(ad_sec1, prof)
                    v_up = tc.parse_vert(ad_sec2)
                    if v_up and v_up['reference'] in ('AMSL', 'FL'):
                        cls = ad_sec3.strip().split()[0].replace("'", "").replace("’", "") if ad_sec3 else 'D'
                        hrs = 'H24' if 'H24' in ad_sec6.upper() else (ad_sec6.strip() if ad_sec6 else 'HO')
                        ctr_obj = {
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
                                'evidence': f'AD 2.17: {ad_sec1} | Vertical: {ad_sec2} | Class: {ad_sec3} | Hours: {ad_sec6}'
                            },
                            'shape': 'polygon',
                            'edges': edges
                        }
                        boundary(prof, ctr_obj)
                        areas.append(ctr_obj)
                    else:
                        issues.append(f'Invalid or missing CTR vertical limits: "{ad_sec2}"')
                except Exception as e:
                    issues.append(f'CTR polygon parsing failed: {e}')
            else:
                issues.append('CTR geometry is complex or unparsed')
                
    # 2. Parse ENR 2.1
    if enr_rows:
        seen = set()
        unique_enr = []
        for r in enr_rows:
            c0 = ' '.join(r['cell0'].split())
            if c0 not in seen:
                seen.add(c0)
                unique_enr.append(r)
                
        enr_areas = []
        for idx, row in enumerate(unique_enr):
            c0 = row['cell0']
            title = row['title']
            
            if re.search(r'border|river|line of control', c0, re.I):
                issues.append(f'ENR 2.1 {title}: Clipped by border or river without coordinates')
                continue
            if re.search(r'restricted area|flying zone|vor\s*\d+|except', c0, re.I):
                issues.append(f'ENR 2.1 {title}: Unsupported complex exclusion (military/restricted area)')
                continue
                
            v_m = re.search(r'(FL\s*\d+|\d+\s*FT(?:\s*AMSL)?)\s*/\s*(FL\s*\d+|\d+\s*FT(?:\s*AMSL)?|SFC)', c0, re.I)
            if not v_m:
                issues.append(f'ENR 2.1 {title}: Vertical limits not extractable')
                continue
            v_upper = tc.parse_vert(v_m[1])
            v_lower = {'reference': 'SFC'} if 'SFC' in v_m[2].upper() else tc.parse_vert(v_m[2])
            if not v_upper or not v_lower:
                issues.append(f'ENR 2.1 {title}: Failed parsing vertical limits {v_m.group(0)}')
                continue
                
            excludes = []
            if 'excluding' in c0.lower() and 'ctr' in c0.lower():
                if any(a['id'] == 'ctr' for a in areas):
                    excludes.append('ctr')
                    
            hrs = 'H24' if 'H24' in row['callsign_hours'].upper() else 'HO'
            area_id = f'cta-{chr(ord("a") + idx)}'
            
            # clean name
            cta_name = f'{name} CTA'
            if 'sector a' in title.lower() or 'sector a' in c0.lower():
                cta_name = f'{name} CTA Sector A'
            elif 'sector b' in title.lower() or 'sector b' in c0.lower():
                cta_name = f'{name} CTA Sector B'
            elif 'area a' in title.lower() or 'area- a' in title.lower() or 'area-a' in title.lower():
                cta_name = f'{name} CTA Area A'
            elif 'area b' in title.lower() or 'area- b' in title.lower() or 'area-b' in title.lower():
                cta_name = f'{name} CTA Area B'
                
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
                
            if rad2 and c_pt2:
                cta_obj = {
                    'id': area_id,
                    'name': cta_name,
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
                    boundary(prof, cta_obj)
                    enr_areas.append(cta_obj)
                except Exception as e:
                    issues.append(f'ENR 2.1 {title}: Circle boundary failed: {e}')
            else:
                try:
                    edges = parse_polygon(c0, prof)
                    cta_obj = {
                        'id': area_id,
                        'name': cta_name,
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
                    boundary(prof, cta_obj)
                    enr_areas.append(cta_obj)
                except Exception as e:
                    issues.append(f'ENR 2.1 {title}: Polygon failed: {e}')
                    
        areas.extend(enr_areas)
        
    if not issues and areas:
        candidate = {
            'schema_version': 1,
            'icao': code,
            'reviewed': True,
            'notes': [
                'Training airspace membership only; not permission to enter or an operational jurisdiction model.',
                'Extracted from official AAI AIP AD 2.17 and ENR 2.1 publications.',
                'Pressure altitude is not supplied by the current simulation adapter; FL boundaries remain uncertain where relevant.'
            ],
            'areas': areas
        }
        try:
            validate(candidate, code)
            for a in areas:
                boundary(prof, a)
            reviewed[code] = candidate
        except Exception as e:
            drafts[code] = f'Full validation failed: {e}'
    else:
        drafts[code] = f'Issues: {issues}'

print(f'Total Reviewed: {len(reviewed)}')
print(f'Total Drafts: {len(drafts)}')
