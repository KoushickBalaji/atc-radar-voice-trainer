"""Parse AD 2.17 Air Traffic Service Airspace for all 124 active airports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUTS = Path('d:/ATC/Airport Layouts')
CACHE = Path('d:/ATC/tmp/airport-audit')

COORD_RE = re.compile(r'(\d{6}(?:\.\d+)?)\s*([NS])\s*(\d{7}(?:\.\d+)?)\s*([EW])', re.I)
PAIR_RE = re.compile(r'(\d{6}(?:\.\d+)?)[NS]\s*(\d{7}(?:\.\d+)?)[EW]', re.I)

def dms(deg_min_sec, hemisphere):
    deglen = 2 if hemisphere in 'NS' else 3
    degrees = int(deg_min_sec[:deglen])
    minutes = int(deg_min_sec[deglen:deglen+2])
    seconds = float(deg_min_sec[deglen+2:])
    val = degrees + minutes / 60.0 + seconds / 3600.0
    return -val if hemisphere in 'SW' else val

def parse_ad217():
    airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])
    profiles = {code: json.loads((ROOT / f'data/airports/{code}.json').read_text(encoding='utf-8')) for code in airports}
    
    # Map PDFs
    ad_pdfs = {}
    for p in LAYOUTS.glob('*/AD 2.1*.pdf'):
        icao = p.stem.replace('AD 2.1', '')
        if icao in airports:
            ad_pdfs[icao] = p

    results = {}
    for code in airports:
        p = ad_pdfs[code]
        folder = p.parent.name
        cfile = CACHE / folder / (p.name + '.json')
        data = json.load(open(cfile, encoding='utf-8'))
        pages = data['pages']
        
        start_page = None
        accumulated = []
        for i, page_text in enumerate(pages):
            if 'AD 2.17' in page_text:
                start_page = i + 1
                idx = page_text.find('AD 2.17')
                t = page_text[idx:]
                if 'AD 2.18' in t:
                    accumulated.append(t[:t.find('AD 2.18')])
                    break
                else:
                    accumulated.append(t)
            elif start_page is not None:
                if 'AD 2.18' in page_text:
                    accumulated.append(page_text[:page_text.find('AD 2.18')])
                    break
                else:
                    accumulated.append(page_text)
                    
        full_text = ' '.join(' '.join(accumulated).split())
        
        # Sections
        # 1 Airspace designation...
        # 2 Vertical limits
        # 3 Airspace classification
        # 6 Hours of applicability
        sec1_m = re.search(r'1\s*(?:Airspace designation|Airspace)?.*?(?=2\s*Vertical limits|$)', full_text, re.I)
        sec2_m = re.search(r'2\s*Vertical limits\s*(.*?)(?=3\s*Airspace classification|$)', full_text, re.I)
        sec3_m = re.search(r'3\s*Airspace classification\s*(.*?)(?=4\s*Call sign|$)', full_text, re.I)
        sec6_m = re.search(r'6\s*Hours of applicability\s*(.*?)(?=7\s*Remarks|$)', full_text, re.I)
        
        results[code] = {
            'icao': code,
            'name': profiles[code]['name'],
            'pdf_file': f'Airport Layouts/{folder}/{p.name}',
            'page': start_page,
            'full_text': full_text,
            'sec1': sec1_m.group(0).strip() if sec1_m else '',
            'sec2': sec2_m.group(1).strip() if sec2_m else '',
            'sec3': sec3_m.group(1).strip() if sec3_m else '',
            'sec6': sec6_m.group(1).strip() if sec6_m else ''
        }
    return results

if __name__ == '__main__':
    res = parse_ad217()
    out_path = ROOT / 'scratch/all_ad217_parsed.json'
    out_path.write_text(json.dumps(res, indent=2), encoding='utf-8')
    print(f'Wrote {len(res)} AD 2.17 extractions to {out_path}')
