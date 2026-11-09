"""Parse ENR 2.1 Control Areas for all airports."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

aliases = {
    'Mangaluru': 'Mangalore',
    'Shamshabad (RGI)': 'Hyderabad',
    'Mopa': 'Goa',
    'Bengaluru (HAL)': 'HAL',
    'Bengaluru (KIA)': 'Bengaluru',
    'Rajkot INTL': 'Rajkot',
    'Cochin': 'Cochin',
    'Calicut': 'Calicut',
    'Tiruchirappalli': 'Tiruchirappalli',
    'Bhubaneswar': 'Bhubaneswar',
    'Varanasi': 'Varanasi',
    'Lucknow': 'Lucknow',
    'Jaipur': 'Jaipur',
    'Patna': 'Patna',
    'Nagpur': 'Nagpur',
    'Amritsar': 'Amritsar',
    'Agartala': 'Agartala',
    'Guwahati': 'Guwahati',
    'Durgapur': 'DURGAPUR',
    'Rewa': 'VERW',
    'Shirdi': 'Shirdi',
    'Surat': 'Surat',
    'Vadodara': 'Vadodara',
    'Udaipur': 'Udaipur',
    'Ranchi': 'Ranchi',
    'Gaya': 'Gaya',
    'Gondia': 'Gondia',
    'Indore': 'Indore',
    'Kannur': 'Kannur',
    'Mysuru': 'Mysuru',
    'Bhopal': 'Bhopal',
    'Bhavnagar': 'Bhavnagar',
    'Aurangabad': 'Aurangabad',
    'Ahmedabad': 'Ahmedabad',
    'Rajahmundry': 'Rajahmundry'
}

def parse_enr21():
    page = (ROOT / 'scratch/enr-2.1.html').read_text(encoding='utf-8')
    rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', page, re.S | re.I)
    
    airports = sorted([p.stem for p in (ROOT / 'data/airports').glob('*.json') if p.stem != 'training'])
    profiles = {code: json.loads((ROOT / f'data/airports/{code}.json').read_text(encoding='utf-8')) for code in airports}
    
    by_code = {code: [] for code in airports}
    
    for r in rows:
        cells = [re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', c))).strip() for c in re.findall(r'<td\b[^>]*>(.*?)</td>', r, re.S | re.I)]
        if len(cells) >= 2 and re.search(r'APP|Approach', cells[1], re.I) and 'Control Area' in cells[0]:
            title = cells[0].split('Area bounded')[0].split('Circular area')[0].split('Sector')[0].strip()
            # Find which airport matches
            for code, prof in profiles.items():
                name = prof['name']
                alias = aliases.get(name, name)
                if title.lower().startswith(name.lower()) or title.lower().startswith(alias.lower()):
                    if code == 'VOBG' and 'HAL' not in title:
                        continue
                    by_code[code].append({
                        'title': title,
                        'cell0': cells[0],
                        'unit': cells[1],
                        'callsign_hours': cells[2] if len(cells) > 2 else '',
                        'frequency': cells[3] if len(cells) > 3 else '',
                        'remarks': cells[4] if len(cells) > 4 else ''
                    })
                    break
                    
    return by_code

if __name__ == '__main__':
    data = parse_enr21()
    out = ROOT / 'scratch/all_enr21_parsed.json'
    out.write_text(json.dumps(data, indent=2), encoding='utf-8')
    non_empty = {k: len(v) for k, v in data.items() if v}
    print(f'Found ENR 2.1 entries for {len(non_empty)} airports, total {sum(non_empty.values())} areas')
