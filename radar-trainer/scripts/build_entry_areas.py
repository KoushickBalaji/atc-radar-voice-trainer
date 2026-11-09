"""Build lateral entry envelopes from supplied AAI AD 2.17 and ENR 2.1.

Run after scratch/ats-airspace-excerpts.json and scratch/enr-2.1.html have
been extracted. Unsupported borders, exclusions and conditional geometries
are listed for review; no display-range or guessed circle is substituted.
These envelopes locate training entries, not altitude-dependent jurisdiction.
"""
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COORD = r'(\d{6}(?:\.\d+)?)[N]\s*(\d{7}(?:\.\d+)?)[E]'
PAIR = re.compile(COORD, re.I)


def dms(value):
    number = float(value)
    degrees, rest = divmod(number, 10000)
    minutes, seconds = divmod(rest, 100)
    if minutes >= 60 or seconds >= 60:
        raise ValueError('Invalid DMS')
    return degrees + minutes / 60 + seconds / 3600


def point(match):
    return [dms(match[1]), dms(match[2])]


def geometry(text):
    """Parse only explicit circles and straight/arc polygons, fail closed."""
    text = re.sub(r'\s+', ' ', text).strip()
    if re.search(r'border|river|line of control|when |portion|except|excluding (?!the airspace contained)', text, re.I):
        raise ValueError('Border, exclusion or conditional geometry needs review')
    # The CTR hole is filled separately by AD 2.17; an entry envelope only
    # needs the outer boundary, never a clearance/jurisdiction decision.
    if re.search(r'circular|by (?:a )?circle', text, re.I):
        coords = list(PAIR.finditer(text))
        if len(coords) != 1:
            raise ValueError('Circle centre is not explicit')
        radii = re.findall(r'(\d+(?:\.\d+)?)\s*NM', text[:coords[0].start()] + text[coords[0].end():], re.I)
        if not radii:
            raise ValueError('No explicit radius')
        return dict(shape='circle', center=point(coords[0]), radius_nm=max(map(float, radii)))
    if 'point of origin' not in text.lower():
        raise ValueError('No explicit polygon closure')
    text = re.split(r'(?:to (?:the )?|up to )point of origin', text, flags=re.I)[0]
    coords = list(PAIR.finditer(text))
    if not coords:
        raise ValueError('No coordinates')
    edges = [dict(point=point(coords[0]))]
    i = 1
    while i < len(coords):
        between = text[coords[i-1].end():coords[i].start()]
        if re.search(r'arc', between, re.I):
            if not re.search(r'(?:center(?:ed)?|centre(?:d)?)\s+(?:at|on)', between, re.I):
                raise ValueError('Arc centre not explicit')
            if not re.search(r'clockwise', between, re.I):
                raise ValueError('Arc direction not explicit')
            center = point(coords[i])
            end = point(coords[i+1]) if i+1 < len(coords) else edges[0]['point']
            edges.append(dict(point=end, center=center, clockwise=not bool(re.search(r'counter\s*clockwise', between, re.I))))
            i += 2
        else:
            edges.append(dict(point=point(coords[i])))
            i += 1
    if len(edges) < 2 or (len(edges) == 2 and 'center' not in edges[1]):
        raise ValueError('Incomplete polygon')
    return dict(shape='polygon', edges=edges)


def build():
    profiles = {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'data/airports').glob('*.json') if p.stem != 'training'}
    excerpts = json.loads((ROOT/'scratch/ats-airspace-excerpts.json').read_text())
    result = {code:dict(areas=[], unresolved=[]) for code in profiles}
    for row in excerpts:
        match = re.search(r'AD 2\.1(\w+)\.pdf', row['file'])
        if not match or match[1] not in result:
            continue
        code = match[1]
        text = ' '.join(row['text'].split())
        text = re.split(r'2 Vertical limits', text)[0]
        text = re.split(r'lateral limits', text, flags=re.I)[-1].strip()
        try:
            shape = geometry(text)
            result[code]['areas'].append(dict(name=f'{code} AD 2.17', source=dict(file=row['file'].replace('\\','/'),page=row['page'],section='AD 2.17'), **shape))
        except ValueError as e:
            result[code]['unresolved'].append(f'AD 2.17: {e}')
    page = (ROOT/'scratch/enr-2.1.html').read_text(encoding='utf-8')
    seen = set()
    aliases = {'Mangaluru':'Mangalore','Shamshabad (RGI)':'Hyderabad','Mopa':'Goa','Shirdi':'Shirdi','Bengaluru (HAL)':'HAL'}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',page,re.S|re.I):
        cells = [re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',c))).strip() for c in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S|re.I)]
        if len(cells)<2 or not re.search('APP|Approach',cells[1]) or 'Control Area' not in cells[0]:
            continue
        text = cells[0]
        if text in seen: continue
        seen.add(text)
        for code, profile in profiles.items():
            name = aliases.get(profile['name'],profile['name'])
            if not text.lower().startswith(name.lower()+' '): continue
            # Do not attribute Bengaluru KIA's APP sectors to HAL.
            if code == 'VOBG': continue
            label = re.split(r'Area bounded|Circular area|\d{6}N',text,flags=re.I)[0].strip()
            try:
                shape = geometry(text)
                result[code]['areas'].append(dict(name=label,source=dict(url='https://aim-india.aai.aero/eaip/eaip-v2-07-2026/eAIP/IN-ENR%202.1-en-GB.html',section='ENR 2.1',edition='July 2026'),**shape))
            except ValueError as e:
                result[code]['unresolved'].append(f'{label}: {e}')
    (ROOT/'data/entry_areas.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Published lateral geometries:',sum(len(v['areas']) for v in result.values()))
    print('Airports with geometry:',sum(bool(v['areas']) for v in result.values()),'/',len(result))
    print('No usable published geometry:',[k for k,v in result.items() if not v['areas']])


if __name__ == '__main__': build()
