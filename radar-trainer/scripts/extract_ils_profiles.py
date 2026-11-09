"""Extract ILS chart candidates from the read-only audit cache.

Automatic extraction is staged, not installed. Explicit reviewed overrides fill
scanned/encoded fields; raw source excerpts remain with each staged record.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'tmp' / 'airport-audit'
OUT = ROOT / 'radar-trainer' / 'outputs' / 'airport-import'
HOLD = {'VOCB','VOML','VOBL','VABB'}


def matches(pattern, text, cast=float):
    return [(cast(m.group(1)),m.group(0)) for m in re.finditer(pattern,text,re.I)]


def candidate(row, item):
    path=CACHE / row['airport'] / (item['file']+'.json')
    text='\n'.join(json.loads(path.read_text(encoding='utf-8'))['pages'])
    runway=re.search(r'RWY[- ]*(\d{2}[LRC]?)',item['file'],re.I).group(1)
    rdh=matches(r'\bRDH\s*[:=]?\s*(\d+(?:\.\d+)?)',text)
    gp=matches(r'\bG\s*\.?\s*P\s*\.?\s*(\d(?:\.\d+)?)\s*[°\ufffd]',text)
    level=matches(r'ALTITUDE\s+(?:AT|OVER)\s+FAF\s*[:=]?\s*(\d{3,5})',text,int)
    courses=matches(r'\b(\d{3})\s*[°\ufffd]',text,int)
    courses=[c for c in courses if abs((c[0]-int(runway[:2])*10+180)%360-180)<12]
    course=Counter(c[0] for c in courses).most_common(1)
    data=dict(icao=row['icao'],airport=row['airport'],runway=runway,
        source_file=f'Airport Layouts/{row["airport"]}/{item["file"]}',source_page=1,
        glide_deg=gp[0][0] if gp else None,rdh_ft=rdh[0][0] if rdh else None,
        intercept_alt_ft=level[0][0] if level else None,
        course_magnetic=course[0][0] if course else None,
        reference_fixes=[],
        field_evidence=dict(glide=gp,rdh=rdh,level=level,course_counts=Counter(c[0] for c in courses)),
        level_basis='Chart LOC/GP-inoperative FAF altitude; requires visual check of horizontal final segment',
        warnings=re.findall(r'[^\n]*(?:CAUTION|RESTRICTED|RNAV 1 REQUIRED|OFFSET|Dhaka|PROHIBITED)[^\n]*',text,re.I))
    data['automatic_score']=sum(data[k] is not None for k in ('glide_deg','rdh_ft','intercept_alt_ft','course_magnetic'))
    return data


def main():
    (OUT/'ils').mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'radar-trainer/outputs/airport-compatibility/inventory.json').read_text(encoding='utf-8'))
    overrides_path=OUT/'ils-reviewed-overrides.json'
    overrides=json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path.exists() else {}
    report=[]
    for row in rows:
        if row['icao'] in HOLD or not row['ils']:
            continue
        candidates=[candidate(row,i) for i in row['ils']]
        selected=max(candidates,key=lambda d:d['automatic_score'])
        override=overrides.get(row['icao'])
        if override:
            if override.get('source_file'):
                selected=next(c for c in candidates if c['source_file']==override['source_file'])
            selected.update(override)
        selected['missing_fields']=[k for k in ('glide_deg','rdh_ft','intercept_alt_ft','course_magnetic') if selected[k] is None]
        selected['status']='reviewed' if selected.get('visually_reviewed') and not selected['missing_fields'] else 'needs_review'
        (OUT/'ils'/f'{row["icao"]}.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
        report.append(dict(icao=row['icao'],airport=row['airport'],source_file=selected['source_file'],
            status=selected['status'],missing_fields=selected['missing_fields'],automatic_score=selected['automatic_score']))
    (OUT/'ils-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(Counter(r['status'] for r in report))
    for r in report: print(r['icao'],r['source_file'].split('/')[-1],','.join(r['missing_fields']))


if __name__=='__main__':
    main()
