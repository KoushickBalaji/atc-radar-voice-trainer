"""Build all control area deliverables:
1. data/control_areas/<ICAO>.json for the 77 reviewed & validated airports
2. outputs/control-area-review/<ICAO>.draft.json for the 47 unresolved airports
3. outputs/control-area-review/<ICAO>.md for all 47 unresolved airports
4. outputs/control-area-review/catalogue.md summarizing all 124 airports
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from airport_profiles import get_profile
from control_area import validate, boundary
import test_classify as tc
from parse_airspace_geometry import parse_polygon, parse_first_coord

ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
enr21 = json.load(open(ROOT / 'scratch/all_enr21_parsed.json', encoding='utf-8'))
airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])

DATA_DIR = ROOT / 'data' / 'control_areas'
DATA_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_DIR = ROOT / 'outputs' / 'control-area-review'
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

draft_overrides = {
    'VABO': 'ENR 2.1 Vadodara Control Area combines Area 1 (circle 25 NM) and Area 2 (arc cut 35/25 NM) in a single published table row without separable discrete bounds.',
    'VAID': 'ENR 2.1 Indore Control Area specifies concentric stepped altitude limits (FL145/2900 ft up to 30 NM, FL145/FL055 beyond 30 NM) within a single polygon boundary.',
    'VANP': 'ENR 2.1 Nagpur Control Area specifies concentric stepped altitude limits (FL460/2100 ft up to 25 NM, FL460/FL55 between 25-50 NM, FL460/FL95 beyond 50 NM) within a single polygon boundary.',
    'VASU': 'ENR 2.1 Surat Control Area Area-B excludes Area-A of CTA, representing an unsupported nested exclusion.',
    'VIJP': 'ENR 2.1 Jaipur Control Area 1 excludes Kishangarh CTR (external aerodrome VIKG), representing an external cross-airport exclusion hole.',
    'VERW': 'ENR 2.1 Rewa Control Area vertical limits overlap Rewa CTR without explicit boundary subtraction or clear ATC delegation boundary.'
}

def extract_date(text):
    m = re.search(r'(\d{2}\s+[A-Z]{3}\s+\d{4})', text)
    if m:
        # e.g. 03 OCT 2024 -> convert to YYYY-MM-DD
        parts = m.group(1).split()
        months = {'JAN':'01','FEB':'02','MAR':'03','APR':'04','MAY':'05','JUN':'06','JUL':'07','AUG':'08','SEP':'09','OCT':'10','NOV':'11','DEC':'12'}
        if len(parts) == 3 and parts[1].upper() in months:
            return f'{parts[2]}-{months[parts[1].upper()]}-{int(parts[0]):02d}'
    return '2026-01-22'

def run():
    reviewed_airports = {}
    draft_airports = {}
    
    for code in airports:
        prof = get_profile(code)
        ad = ad17[code]
        enr_rows = enr21.get(code, [])
        name = prof.NAME
        
        # Check override
        if code in draft_overrides:
            reason = draft_overrides[code]
            draft_airports[code] = {
                'reason': reason,
                'areas': [],
                'ad': ad,
                'enr': enr_rows
            }
            continue
            
        # Existing reviewed VOCB
        if code == 'VOCB':
            vocb_path = DATA_DIR / 'VOCB.json'
            reviewed_airports[code] = json.loads(vocb_path.read_text(encoding='utf-8'))
            continue
            
        ad_sec1 = ad['sec1']
        ad_sec2 = ad['sec2']
        ad_sec3 = ad['sec3']
        ad_sec6 = ad['sec6']
        
        issues = []
        areas = []
        
        # CTR
        if not ad_sec1 or 'not established' in ad_sec1.lower() or 'not established' in ad_sec2.lower():
            issues.append('CTR Not Established in AIP AD 2.17')
        elif 'nil' in ad_sec1.lower() or len(ad_sec1) < 10:
            issues.append('No ATS airspace in AIP AD 2.17 (NIL)')
        elif re.search(r'border|river|line of control|international boundary', ad_sec1, re.I) and not re.search(r'circular area of radius \d+ NM centered', ad_sec1, re.I):
            issues.append('CTR boundary clipped by international border or river without published coordinates')
        elif 'vicinity of ad' in ad_sec1.lower():
            issues.append('CTR boundary unquantified: published as "within vicinity of AD"')
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
                    eff_date = extract_date(ad['full_text'])
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
                            'effective_date': eff_date,
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
                            eff_date = extract_date(ad['full_text'])
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
                                    'effective_date': eff_date,
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

        # ENR 2.1
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
                            'evidence': c0,
                            'snapshot': 'scratch/enr-2.1.html'
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
                                'evidence': c0,
                                'snapshot': 'scratch/enr-2.1.html'
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
                reviewed_airports[code] = candidate
            except Exception as e:
                draft_airports[code] = {
                    'reason': f'Validation failed: {e}',
                    'areas': areas,
                    'ad': ad,
                    'enr': enr_rows
                }
        else:
            draft_airports[code] = {
                'reason': '; '.join(issues) if issues else 'No areas parsed',
                'areas': areas,
                'ad': ad,
                'enr': enr_rows
            }

    # Write reviewed files
    print(f'Writing {len(reviewed_airports)} reviewed files to {DATA_DIR}...')
    for code, data in reviewed_airports.items():
        out_file = DATA_DIR / f'{code}.json'
        out_file.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        
    # Write draft files and markdown reviews
    print(f'Writing {len(draft_airports)} draft files and review notes to {REVIEW_DIR}...')
    for code, info in draft_airports.items():
        draft_file = REVIEW_DIR / f'{code}.draft.json'
        draft_data = {
            'schema_version': 1,
            'icao': code,
            'reviewed': False,
            'notes': [
                f'UNRESOLVED: {info["reason"]}',
                'Draft retained outside data/control_areas; manual official amendment or FIR coordination required.'
            ],
            'areas': info['areas']
        }
        draft_file.write_text(json.dumps(draft_data, indent=2) + '\n', encoding='utf-8')
        
        md_file = REVIEW_DIR / f'{code}.md'
        md_content = f"""# Control Area Review: {code} ({get_profile(code).NAME})

## Status: UNRESOLVED / DRAFT
- **ICAO**: `{code}`
- **Airport**: {get_profile(code).NAME}
- **Reviewed**: `false` (Quarantined in `outputs/control-area-review/`)
- **Reason**: {info['reason']}

---

## Source Extracts

### 1. AD 2.17 Air Traffic Service Airspace
- **File**: `{info['ad'].get('pdf_file', 'N/A')}`
- **Page**: {info['ad'].get('page', 'N/A')}
- **Transcribed Text**:
> {info['ad'].get('full_text', 'No text extracted')}

### 2. ENR 2.1 Control Areas (CTA / TMA)
- **Publication**: eAIP India ENR 2.1 (July 2026 Edition)
- **Matching Rows**: {len(info['enr'])}
"""
        if info['enr']:
            for i, r in enumerate(info['enr']):
                md_content += f"""
#### Row {i+1}: {r['title']}
- **Unit**: `{r['unit']}`
- **Callsign / Hours**: `{r['callsign_hours']}`
- **Cell Text**:
> {r['cell0']}
"""
        else:
            md_content += "\nNo matching Control Area entries found in ENR 2.1 for this aerodrome.\n"

        md_content += f"""
---

## Discrepancy & Technical Analysis
1. **Geometric Issue**: {info['reason']}
2. **Contract Compliance**:
   - According to `radar-trainer/docs/CONTROL_AREA_DATA_HANDOFF.md`, missing or unresolved files must evaluate to `unavailable` rather than incorrectly reporting `outside` or synthesizing border coordinates.
   - Files containing unquantified borders, conflicting limits, arc discrepancies exceeding 0.2 NM, or unsupported nested exclusions must remain drafts outside `data/control_areas/`.
3. **Required Actions**:
   - Obtain official civil aviation FIR coordinates for border cuts or bilateral LoC agreements.
   - Obtain formal AIP amendments for unquantified military airspace exclusions or missing vertical limits.
"""
        md_file.write_text(md_content, encoding='utf-8')

    # Generate Catalogue
    cat_file = REVIEW_DIR / 'catalogue.md'
    cat_content = f"""# Control Area Catalogue

Total Airports Audited: {len(airports)}
- **Reviewed & Validated**: {len(reviewed_airports)} (Available in `data/control_areas/`)
- **Unresolved / Drafts**: {len(draft_airports)} (Quarantined in `outputs/control-area-review/`)

| Airport | ICAO | Status | Control Volumes | Vertical Extent | Hours | Notes / Discrepancy |
|---|---|---|---|---|---|---|
"""
    for code in airports:
        name = get_profile(code).NAME
        if code in reviewed_airports:
            cand = reviewed_airports[code]
            vol_names = '<br>'.join([f"{a['kind']}: {a['name']}" for a in cand['areas']])
            v_exts = '<br>'.join([f"{a['lower']['reference']} - {a['upper'].get('value', '')} {a['upper']['reference']}" for a in cand['areas']])
            hours = '<br>'.join([a['hours'] for a in cand['areas']])
            cat_content += f"| {name} | `{code}` | **Reviewed** | {vol_names} | {v_exts} | {hours} | Available in live simulation |\n"
        else:
            info = draft_airports[code]
            cat_content += f"| {name} | `{code}` | *Draft* | Unavailable | - | - | {info['reason']} |\n"

    cat_file.write_text(cat_content, encoding='utf-8')
    print(f'Catalogue generated at {cat_file}')
    print('All deliverables successfully generated!')

if __name__ == '__main__':
    run()
