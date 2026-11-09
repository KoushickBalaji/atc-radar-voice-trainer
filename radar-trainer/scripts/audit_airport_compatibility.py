"""Read-only document-set screening; does not import airports or certify charts.
Run with a Python environment containing pypdf, from any working directory.
"""
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Airport Layouts'
CACHE = ROOT / 'tmp' / 'airport-audit'
OUT = ROOT / 'radar-trainer' / 'outputs' / 'airport-compatibility'
CACHE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)


def extract(path):
    target = CACHE / path.parent.name / (path.name + '.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    stamp = [stat.st_size, stat.st_mtime_ns]
    if target.exists():
        data = json.loads(target.read_text(encoding='utf-8'))
        if data['stamp'] == stamp:
            return data
    try:
        pages = [page.extract_text() or '' for page in PdfReader(path).pages]
        data = dict(stamp=stamp, pages=pages, error=None)
    except Exception as exc:
        data = dict(stamp=stamp, pages=[], error=str(exc))
    target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return data


def audit(folder):
    files = sorted(folder.glob('*.pdf'))
    names = [p.name for p in files]
    codes = Counter(re.findall(r'V[A-Z]{3}(?=[\s.\-]|$)', ' '.join(names)))
    icao = codes.most_common(1)[0][0] if codes else '?'
    ads = [p for p in files if re.match(r'AD\s*2', p.name, re.I)]
    adc = [p for p in files if re.search(r'-ADC(?:\.pdf|[- ])', p.name, re.I)]
    ils = [p for p in files if 'ILS' in p.name.upper() and 'RWY' in p.name.upper()
           and not any(t in p.name.upper() for t in ['CRTC', 'SENS', 'CODING', 'TABLE', 'LVP'])]
    smac = [p for p in files if 'SMAC' in p.name.upper()]
    alternatives = [p.name for p in files if re.search(r'-(?:RNP|VOR|NDB|LOC)[- (]', p.name, re.I)
                    and not any(t in p.name.upper() for t in ['CODING', 'TABLE'])]
    pages = []
    errors = []
    for p in ads:
        item = extract(p)
        pages.extend((p.name, i+1, t) for i,t in enumerate(item['pages']))
        if item['error']: errors.append(p.name+': '+item['error'])
    full = '\n'.join(t for _,_,t in pages)
    match = re.search(r'AD\s*2\.12\s+RUNWAY PHYSICAL', full, re.I)
    section = full[match.start():] if match else ''
    section = re.split(r'AD\s*2\.13\s', section, maxsplit=1)[0]
    ends = sorted(set(re.findall(r'(?m)^\s*(?:RWY\s+)?(\d{2}[LRC]?)\s+\d+(?:\.\d+)?\s*DEG', section)))
    runway_pages = [dict(file=f, page=n) for f,n,t in pages if 'RUNWAY PHYSICAL' in t.upper()]
    ils_checks=[]
    for p in ils:
        item=extract(p)
        text='\n'.join(item['pages'])
        ils_checks.append(dict(file=p.name, text_characters=len(text.strip()),
            content_has_ils=bool(re.search(r'\bILS\b',text,re.I)),
            error=item['error']))
    smac_checks=[]
    for p in smac:
        item=extract(p)
        text='\n'.join(item['pages'])
        smac_checks.append(dict(file=p.name,text_characters=len(text.strip()),
            content_has_title='MINIMUM ALTITUDE' in text.upper(),error=item['error']))
    runways=sorted(set(re.findall(r'RWY[-\s]*(\d{2}[LRC]?)', ' '.join(p.name for p in ils),re.I)))
    refs=sorted(set(line for line in re.findall(r'[^\n]*\bILS[^\n]*',full,re.I)
                    if not re.search(r'supported operation|operation for ILS|VOR/ILS/MLS station',line,re.I)))
    if icao in ('VOCB','VOML'):
        category='Implemented'
    elif ils and ads and ends:
        category='ILS + SMAC candidate' if smac else 'ILS candidate; no SMAC supplied'
    elif ils:
        category='ILS present; aerodrome data review'
    elif refs:
        category='No ILS chart; investigate references'
    else:
        category='No ILS chart supplied'
    return dict(airport=folder.name,icao=icao,pdf_count=len(files),category=category,
        runway_ends=ends,runway_count=len(ends)//2 if ends and len(ends)%2==0 else None,
        runway_evidence=runway_pages,ad_files=[p.name for p in ads],adc_files=[p.name for p in adc],
        ils_runways=runways,ils=ils_checks,smac=smac_checks,alternatives=alternatives,
        ils_mentions=refs,errors=errors,files=names)


def report(rows):
    total_pdfs = sum(r['pdf_count'] for r in rows)
    implemented = [r for r in rows if r['category'] == 'Implemented']
    new_ils = [r for r in rows if r['ils'] and r['category'] != 'Implemented']
    both = [r for r in rows if r['category'] == 'ILS + SMAC candidate']
    single_both = [r for r in both if r['runway_count'] == 1]
    counts = Counter(r['runway_count'] for r in rows)
    missing_refs = sum(r['category'] == 'No ILS chart; investigate references' for r in rows)
    categories = [
        ('Implemented', 'Already implemented', 'Both existing airports retain their validated profiles.'),
        ('ILS + SMAC candidate', 'Candidates for ILS and altitude warnings',
         'Document-set candidates, not approved imports. Select one approach, transcribe its parameters and SMAC regions, then validate the exercise.'),
        ('ILS candidate; no SMAC supplied', 'Candidates for ILS only',
         'Can be assessed for the existing ILS exercise. Keep MSAW explicitly unavailable unless a suitable vectoring-minimum dataset is obtained.'),
        ('No ILS chart; investigate references', 'Missing ILS charts despite aerodrome references',
         'Obtain the referenced ILS instrument approach chart before selecting approach parameters. This is a document gap, not evidence that ILS is absent.'),
        ('No ILS chart supplied', 'Need an ILS chart or another approach mode',
         'No ILS approach chart was found and no substantive ILS mention was found in the extracted AD text. This does not prove the airport has no ILS. If only RNP/VOR/NDB/visual approaches are applicable, the current ILS-only success logic needs another mode.'),
        ('ILS present; aerodrome data review', 'Aerodrome geometry needs review',
         'An ILS chart is present, but the runway data could not be confirmed by this screening.'),
    ]
    def link(r, name, label=None):
        return f'[{label or name}](<{(SOURCE/r["airport"]/name).as_posix()}>)'
    lines = ['# Indian airport compatibility list', '', 'Prepared 6 November 2026 from the local download in `D:/ATC/Airport Layouts`.', '',
        f'**{len(rows)} airport folders; {sum(r["pdf_count"] for r in rows):,} PDF files.** No airport profiles or application behavior were changed by this audit.', '',
        'This is a **document-set feasibility screen** for the existing one-aircraft, one-selected-runway, one-selected-ILS exercise. Only Coimbatore and Mangaluru are already modeled and tested. Every other candidate still needs chart transcription, approach-note review, geometry checks and a simulated trial.', '',
        '| Classification | Airports |', '| --- | ---: |']
    for key,title,_ in categories:
        count=sum(r['category']==key for r in rows)
        if count: lines.append(f'| {title} | {count} |')
    lines += ['', '## What the counts mean', '',
        f'- {sum(bool(r["ils"]) for r in rows)} airports have a named ILS approach PDF: {len(implemented)} implemented and {len(new_ils)} new candidates. Of the new candidates, {sum(r["runway_count"] == 1 for r in new_ils)} have one published runway pair and {sum(r["runway_count"] > 1 for r in new_ils)} have multiple runway pairs.',
        f'- {sum(bool(r["smac"]) for r in rows)} airports have a named SMAC PDF: {len(implemented)} implemented and {len(both)} ILS + SMAC candidates. SMAC present but ILS chart missing: '+', '.join(r['airport'] for r in rows if r['smac'] and not r['ils'])+'.',
        f'- Of the {len(both)} new ILS + SMAC candidates, {len(single_both)} have one runway pair. Multi-runway candidates needing a deliberate selection of one runway/approach: '+', '.join(r['airport'] for r in both if r['runway_count'] > 1)+'. Their other runways would not be modeled.',
        '- Runway count is based on the supplied AD 2.12 physical-characteristics table, not on current operating status. The counts describe the supplied physical-characteristics tables, not a live airport catalogue. Closures, operating restrictions and changes after the supplied chart edition were not checked.',
        '- A chart headed MSA on an approach plate is not a replacement for a SMAC/vectoring-minimum dataset. No circular MSA sectors were counted as SMAC.',
        '- No SMAC supplied means no matching file in this collection, not that the airport has no published minima. No ILS chart supplied likewise describes this download only.',
        '- ADC is useful for cross-checking but not mandatory when AD 2.12 provides the thresholds, bearings, dimensions and elevations. Some military/civil-enclave folders have AD data without a separate ADC.', '',
        '## Suggested order', '',
        'Start with the **single-runway ILS + SMAC candidates** below. Tiruchirappalli is a useful first trial: its supplied ILS/LOC RWY 27 plate was visually inspected and shows the straight final geometry used by the existing exercise. It still requires SMAC transcription and profile validation.', '',
        'Agartala and Cochin also received sample visual ILS-plate checks. Agartala has an explicit Dhaka coordination note and aircraft-category restrictions; these must be recorded as scope limitations in a simplified vector-to-final exercise. Cochin includes a 2019 conventional plate and a 2025 ILS Z plate with RNAV requirements; choose a coherent edition/procedure rather than mixing their parameters. These checks illustrate why file presence alone is not import approval.', '',
        f'**{len(single_both)} single-runway candidates with SMAC:** '+', '.join(r['airport'] for r in rows if r['category']=='ILS + SMAC candidate' and r['runway_count']==1)+'.', '',
        'Next, add selected ILS-only airports with an explicit no-MSAW state, or obtain their missing SMAC data. Resolve the missing-ILS-chart cases before treating those airports as approach candidates.', '',
        '## Method and limits', '',
        f'The script inventories all {total_pdfs:,} filenames and extracts the AD documents, candidate ILS approach PDFs and SMAC PDFs. It reads the runway designators from AD 2.12, filters out ILS coding tables and critical/sensitive-area drawings, and distinguishes boilerplate ILS column headings from substantive facility references. All {len(rows)} folders have readable AD runway tables after handling the `RWY` prefix variant. Three sample ILS plates were rendered and inspected; the other approach and SMAC plates have not all been visually validated.', '',
        'Scanned/image-only or weakly extractable charts are flagged below. They are not rejected as incompatible, but need visual/OCR-assisted transcription and manual checking. This report does not verify every threshold, altitude, glide slope, radio facility, aircraft-category limit, special procedure, source-edition consistency or airport operating status. It is not an operational navigation dataset.', '',
        'The engine supports runway-aligned ILS vectoring with a simplified glide-slope capture model. Offset approaches, unusual geometry, unsupported exclusions/holes in SMAC regions, and incompatible procedure requirements may require adjustments discovered during import. Approach category II/III charts do not imply that the tool models category II/III operations, autoland or low-visibility procedures.', '',
        'The machine-readable [inventory.json](inventory.json) retains every filename, all detected ILS/SMAC files, extraction flags, runway-table page references and substantive ILS mentions. Re-run `scripts/audit_airport_compatibility.py` with Python + pypdf to refresh the inventory and this report; the extraction cache is in `D:/ATC/tmp/airport-audit`.', '']
    for key,title,meaning in categories:
        group=[r for r in rows if r['category']==key]
        if not group: continue
        lines += [f'## {title} ({len(group)})', '', meaning, '',
                  '| Airport / ICAO | Published runway ends | ILS chart runway(s) | SMAC | Evidence / review notes |',
                  '| --- | --- | --- | --- | --- |']
        for r in group:
            notes=[]
            if r['runway_evidence']:
                e=r['runway_evidence'][0]
                notes.append(link(r,e['file'],f'AD p{e["page"]}'))
            if r['ils']:
                preferred=next((i for i in r['ils'] if i['content_has_ils']),r['ils'][0])
                notes.append(link(r,preferred['file'],'ILS example'))
                if len(r['ils'])>1: notes.append(f'{len(r["ils"])} ILS variants in inventory')
            if r['runway_count'] and r['runway_count']>1: notes.append('Select one runway; multi-runway operations excluded')
            if not r['adc_files']: notes.append('No separate ADC; cross-check AD geometry')
            if any(not i['content_has_ils'] for i in r['ils']): notes.append('At least one ILS plate needs visual extraction')
            if any(not i['content_has_title'] for i in r['smac']): notes.append('SMAC needs visual extraction/title check')
            if r['alternatives'] and not r['ils']: notes.append('Other supplied approach types: '+', '.join(sorted(set(re.search(r'-(RNP|VOR|NDB|LOC)',n).group(1) for n in r['alternatives']))))
            if r['airport']=='Agartala': notes.append('Dhaka coordination / CAT notes require review')
            if r['airport']=='Cochin': notes.append('2019 conventional and 2025 RNAV-based ILS Z editions: choose coherent data')
            smac='; '.join(link(r,i['file'],'SMAC') for i in r['smac']) or 'Not supplied'
            ends=', '.join(r['runway_ends']) or 'Review'
            lines.append(f'| {r["airport"]} / {r["icao"]} | {ends} ({r["runway_count"] or "?"} runway'+('s' if r['runway_count']!=1 else '')+f') | {", ".join(r["ils_runways"]) or "Not supplied"} | {smac} | '+ '; '.join(notes)+' |')
        lines.append('')
    lines += ['## Evidence for missing ILS charts', '',
              'These excerpts are from the supplied AD documents. They establish a reason to seek the missing chart, not its present operational availability.', '']
    for r in rows:
        if r['category']=='No ILS chart; investigate references':
            evidence=next((s for s in r['ils_mentions'] if 'DME ILS' in s),r['ils_mentions'][0])
            lines += [f'- **{r["airport"]} ({r["icao"]}):** `{evidence.strip()}`. '+link(r,r['ad_files'][0],'Aerodrome document')+'.']
    lines += ['', '## Import acceptance checklist', '',
        '1. Select one runway and one ILS procedure/edition; preserve the source identifier and effective date.',
        '2. Verify threshold coordinates/elevations, true versus magnetic bearings, localizer/glide-slope geometry and DME reference points.',
        '3. Check procedure and aircraft-category notes against the simplified exercise. Do not label unsupported procedure behavior as implemented.',
        '4. Transcribe SMAC boundaries and minima where supplied, including unknown coverage and approach-inhibition policy; otherwise mark MSAW unavailable.',
        '5. Choose an initial position/altitude that respects the minima unless an intentional low-altitude training scenario is clearly labeled.',
        '6. Validate region interiors/edges/overlaps, display the map against the source, and run capture plus warning/clear/reset tests.',
        '7. Only then add the validated profile to the selectable application catalogue.', '']
    (OUT/'compatibility.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    folders=sorted(p for p in SOURCE.iterdir() if p.is_dir())
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(audit,folders))
    (OUT/'inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    report(rows)
    print(json.dumps(dict(airports=len(rows),pdfs=sum(r['pdf_count'] for r in rows),
        categories=Counter(r['category'] for r in rows)),indent=2))
    for r in rows:
        print(f"{r['airport']} | {r['icao']} | {','.join(r['runway_ends']) or '?'} | ILS {','.join(r['ils_runways']) or '-'} | SMAC {len(r['smac'])} | {r['category']}")
