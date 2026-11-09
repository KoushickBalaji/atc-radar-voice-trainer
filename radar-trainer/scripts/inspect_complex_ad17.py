"""Inspect complex/unparsed AD 2.17 descriptions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ad17 = json.load(open(ROOT / 'scratch/all_ad217_parsed.json', encoding='utf-8'))
complex_codes = ['VADN', 'VAJL', 'VAKP', 'VAKS', 'VAOZ', 'VAPO', 'VAPR', 'VEAY', 'VEGT', 'VEIM', 'VEJR', 'VEJS', 'VEJT', 'VELR', 'VERK', 'VERU', 'VIAG', 'VIBR', 'VIBY', 'VICG', 'VIDD', 'VIKG', 'VIMB', 'VIND', 'VISP', 'VOBM', 'VOBR', 'VOCB', 'VOCI', 'VOGA', 'VOGB', 'VOGO', 'VOHB', 'VOHS', 'VOHY', 'VOPC', 'VOSR', 'VOVI', 'VOVZ', 'VEBI', 'VEDG']

for code in complex_codes:
    d = ad17[code]
    print(f'=== {code} ({d["name"]}) ===')
    print('  Sec 1:', d['sec1'][:160])
    print('  Sec 2:', d['sec2'])
    print('  Sec 3:', d['sec3'])
    print('  Sec 6:', d['sec6'])
