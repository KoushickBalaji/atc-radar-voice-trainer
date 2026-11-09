"""Extract explicitly labelled AD 2.18 TWR rows from cached PDF text."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
records = {}
for path in (ROOT/'data/airports').glob('*.json'):
    if path.stem == 'training':
        continue
    profile = json.loads(path.read_text(encoding='utf-8'))
    candidates = []
    for source in (ROOT.parent/'tmp/airport-audit'/profile['name']).glob('AD*.json'):
        for page, text in enumerate(json.loads(source.read_text(encoding='utf-8'))['pages'], 1):
            if 'COMMUNICATION FACILITIES' not in text:
                continue
            section = re.split(r'AD\s*2\.19', text)[0]
            for m in re.finditer(r'(?m)^\s*TWR\s+([^\d]+?)\s+(1[123]\d\.\d{1,3})\s*MHZ', section, re.I):
                name = ' '.join(m[1].split())
                if re.search(r'\b(APP|ATIS|RADAR|GND)\b', name):
                    continue
                candidates.append(dict(name=name, frequency_mhz=f'{float(m[2]):.3f}',
                    source_file=f'Airport Layouts/{profile["name"]}/{source.name[:-5]}',
                    source_page=page, source_row=' '.join(m[0].split())))
    if candidates:
        # First explicitly published TWR channel is the selected exercise channel,
        # not a claim that it is the currently active/primary operational channel.
        records[profile['icao']] = dict(**candidates[0], alternatives=candidates[1:],
            policy='First listed TWR channel selected for training; published hours/activation are not simulated.')
(ROOT/'data/tower_channels.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
print(f'Extracted TWR channels for {len(records)} airports')
