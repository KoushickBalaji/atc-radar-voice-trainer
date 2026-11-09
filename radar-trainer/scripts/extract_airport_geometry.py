"""Deterministic AD-table extraction into staging, not automatic publication.

Uses pypdf text cached by audit_airport_compatibility.py. No model/API calls.
Ambiguous/missing values fail closed in geometry-report.json.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'tmp' / 'airport-audit'
OUT = ROOT / 'radar-trainer' / 'outputs' / 'airport-import'
PAIR = re.compile(r'(?<!\d)(\d{6}(?:\.\d+)?)\s*([NS])\s*(\d{7}(?:\.\d+)?)\s*([EW])(?!\w)')
ROW = re.compile(r'(?m)^\s*(?:RWY\s+)?(\d{2}[LRC]?)\s+(\d+(?:\.\d+)?)\s*DEG\b')


def dms(value, hemisphere):
    deglen = 2 if hemisphere in 'NS' else 3
    degree, minute, second = int(value[:deglen]), int(value[deglen:deglen+2]), float(value[deglen+2:])
    if minute >= 60 or second >= 60:
        raise ValueError('Invalid DMS component')
    number = degree + minute / 60 + second / 3600
    if number > (90 if hemisphere in 'NS' else 180):
        raise ValueError('Invalid coordinate range')
    return number * (-1 if hemisphere in 'SW' else 1)


def coordinate(match):
    return [dms(match[1], match[2]), dms(match[3], match[4])]


def section(text, n):
    found = re.search(r'AD\s*2\.' + str(n) + r'\s', text)
    if not found:
        return ''
    tail = text[found.start():]
    return re.split(r'AD\s*2\.'+str(n+1)+r'\s', tail, maxsplit=1)[0]


def distance(a,b):
    lat=math.radians((a[0]+b[0])/2)
    return math.hypot((a[1]-b[1])*math.cos(lat),(a[0]-b[0]))*60*1852


def opposite(name):
    number=(int(name[:2])+17)%36+1
    return f'{number:02d}'+({'L':'R','R':'L','C':'C'}.get(name[2:],''))


def extract(row):
    pages=[]
    for name in row['ad_files']:
        cached=json.loads((CACHE/row['airport']/(name+'.json')).read_text(encoding='utf-8'))
        pages.extend((name,i+1,t) for i,t in enumerate(cached['pages']))
    text='\n'.join(t for _,_,t in pages)
    s2,s12,s13,s19=section(text,2),section(text,12),section(text,13),section(text,19)
    notes=[]
    arp=PAIR.search(s2)
    if not arp:
        raise ValueError('ARP coordinate not unambiguously extractable')
    elevation=re.search(r'Aerodrome elevation and reference temperature\s*([\d,.]+)\s*F(?:T|EET)',s2,re.I)
    if not elevation:
        raise ValueError('Aerodrome elevation in feet not extractable')
    elevation=float(elevation[1].replace(',',''))
    rows=list(ROW.finditer(s12))
    if not rows or len(rows)%2:
        raise ValueError('Runway row extraction incomplete')
    elevations=re.findall(r'THR\s*:\s*(\d+(?:\.\d+)?)\s*FT',s12,re.I)
    if len(elevations)!=len(rows):
        raise ValueError(f'Threshold elevations {len(elevations)} do not match runway ends {len(rows)}')
    ends=[]
    dimensions_in_remarks=re.findall(r'(?:Dimensions? of RWY|RWY Dimensions?)\s*:\s*(\d+(?:\.\d+)?)\s*M?\s*[xX]\s*(\d+(?:\.\d+)?)\s*M',s12,re.I)
    missing_dimension_index=0
    for i,m in enumerate(rows):
        block=s12[m.end():rows[i+1].start() if i+1<len(rows) else len(s12)]
        dims=re.match(r'\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*M\b',block)
        if dims:
            length,width=float(dims[1]),float(dims[2])
        elif missing_dimension_index<len(dimensions_in_remarks):
            length,width=map(float,dimensions_in_remarks[missing_dimension_index])
            missing_dimension_index+=1
            notes.append(f'RWY {m[1]} dimensions from ordered AD 2.12 remarks')
        else:
            raise ValueError('Runway dimensions unavailable for '+m[1])
        thr=re.search(r'THR\s*:\s*',block)
        coord=PAIR.search(block,thr.end()) if thr else None
        if coord is None:
            raise ValueError('Threshold coordinate missing for '+m[1])
        if 'RWY END' in block[thr.end():coord.start()]:
            raise ValueError('Threshold coordinate blank for '+m[1])
        lat,lon=coordinate(coord)
        ends.append(dict(name=m[1],lat=lat,lon=lon,elevation_ft=float(elevations[i]),
                         bearing_true=float(m[2]),length_m=length,width_m=width))
    endmap={e['name']:e for e in ends}
    if len(endmap)!=len(ends):
        raise ValueError('Duplicate runway designators')
    runways=[]
    used=set()
    for e in ends:
        if e['name'] in used:
            continue
        peer=endmap.get(opposite(e['name']))
        if not peer:
            raise ValueError('No reciprocal runway for '+e['name'])
        if abs(((peer['bearing_true']-e['bearing_true'])%360)-180)>2:
            raise ValueError('Non-reciprocal true bearings')
        measured=distance([e['lat'],e['lon']],[peer['lat'],peer['lon']])
        length=e['length_m']
        if not .25*length<=measured<=1.08*length:
            raise ValueError(f'Runway {e["name"]} coordinate separation {measured:.0f}m vs length {length:.0f}m')
        if abs(measured-length)>max(60,.04*length):
            notes.append(f'RWY {e["name"]}/{peer["name"]}: threshold separation {measured:.0f} m vs published length {length:.0f} m; displacement documented' if re.search(r'displac',s12+s13,re.I) else f'RWY {e["name"]}/{peer["name"]}: threshold separation {measured:.0f} m vs published length {length:.0f} m; displacement needs review')
        if e['length_m']!=peer['length_m'] or e['width_m']!=peer['width_m']:
            notes.append(f'RWY {e["name"]}/{peer["name"]}: asymmetric published dimensions; do not select this pair without manual review')
        # Verify published runway direction against coordinates, tolerate rounded legacy coordinates.
        true=math.degrees(math.atan2((peer['lon']-e['lon'])*math.cos(math.radians(e['lat'])),peer['lat']-e['lat']))%360
        if abs((true-e['bearing_true']+180)%360-180)>5:
            raise ValueError(f'Runway bearing inconsistent with threshold coordinates: {e["name"]}')
        runways.append(dict(name=e['name']+'/'+peer['name'],length_m=length,width_m=e['width_m'],
            ends=[{k:v for k,v in a.items() if k not in ('length_m','width_m')} for a in (e,peer)]))
        used.update([e['name'],peer['name']])
    center=coordinate(arp)
    if min(distance(center,[e['lat'],e['lon']]) for e in ends)>10000:
        raise ValueError('ARP far from threshold geometry')
    # AD 2.19 tables print first the descriptors, then coordinates in the same row order.
    aidrow=re.compile(r'(?m)^\s*((?:DVOR/DME|VOR/DME|DVOR|VOR|DME|NDB|LOC|GP|LLZ|TACAN|ILS)(?:[^\n]*))')
    # Header occurrences are removed; keep only descriptor lines after numeric table row marker.
    body=re.split(r'(?m)^\s*1\s*2\s*3\s*4\s*$',s19,maxsplit=1)
    body=body[1] if len(body)==2 else s19
    descriptor_text=body.split('Geographical')[0]
    matches=list(aidrow.finditer(descriptor_text))
    descriptors=[' '.join(descriptor_text[m.start():matches[i+1].start() if i+1<len(matches) else len(descriptor_text)].split())
                 for i,m in enumerate(matches) if not m[1].startswith('VOR/ILS/MLS')]
    coordinates=[coordinate(m) for m in PAIR.finditer(body)]
    aids=[]
    if len(descriptors)==len(coordinates):
        for descriptor,pos in zip(descriptors,coordinates):
            kind='loc' if descriptor.startswith(('LOC','LLZ')) else 'gs' if descriptor.startswith('GP') else 'ndb' if descriptor.startswith('NDB') else 'vor' if 'VOR' in descriptor else 'dme'
            if distance(center,pos)>100000:
                notes.append('Distant navaid retained from AD 2.19: '+descriptor)
            aids.append(dict(name=descriptor,lat=pos[0],lon=pos[1],type=kind))
    elif descriptors or coordinates:
        notes.append(f'Navaids unresolved: {len(descriptors)} descriptor rows / {len(coordinates)} coordinate rows; not plotted')
    ils_equipment=bool(re.search(r'(?m)^\s*(?:LOC|GP|LLZ|ILS)\b|DME\s+ILS',body))
    metadata={}
    variation=re.search(r'annual change\s*([\d.]+)\s*DEG\s*([EW])\s*\((\d{4})\)',s2,re.I)
    if variation:
        metadata['magnetic_variation']=dict(degrees=float(variation[1])*(-1 if variation[2]=='W' else 1),epoch=int(variation[3]),source='AD 2.2; not extrapolated')
    selected=runways[0]
    level=math.ceil(elevation/1000)*1000+3000
    heading=selected['ends'][0]['bearing_true']
    source_files=[f'Airport Layouts/{row["airport"]}/{name}' for name in row['ad_files']]
    source_pages=[dict(file=f'Airport Layouts/{row["airport"]}/{f}',page=n,sections=[key for key in ('AD 2.2 ','AD 2.12 ','AD 2.19 ') if key in t])
                  for f,n,t in pages if any(key in t for key in ('AD 2.2 ','AD 2.12 ','AD 2.19 '))]
    result=dict(icao=row['icao'],name=row['airport'],country_code='IN',center=center,elevation_ft=elevation,
        range_nm=25,runway=selected,approach=None,navaids=aids,
        exercise=dict(reference_runway_index=0,practice_alt_ft=level,command_alt_min_ft=math.ceil((elevation+1000)/100)*100,
            start=dict(callsign='AFR123',type='A320',along_nm=16,cross_nm=3,alt_ft=level+1000,spd_kt=220,hdg=round((heading+15)%360)),
            suggested_heading=round((heading+30)%360)),sources=source_files,**metadata)
    extraction=dict(source_pages=source_pages,all_runways=runways,navaid_descriptors=descriptors,
        navaid_coordinates=coordinates,ad19_text=s19,declared_distances_text=s13,ils_equipment_in_ad19=ils_equipment,notes=notes,
        classification=row['category'],method='Deterministic cached pypdf AD2.2/2.12/2.19 table parsing; chart values plus explicitly synthetic exercise setup')
    result['extraction']=extraction
    return result


def main():
    rows=json.loads((ROOT/'radar-trainer/outputs/airport-compatibility/inventory.json').read_text(encoding='utf-8'))
    (OUT/'base').mkdir(parents=True,exist_ok=True)
    report=[]
    for row in rows:
        record=dict(icao=row['icao'],airport=row['airport'],category=row['category'])
        try:
            data=extract(row)
            (OUT/'base'/f'{row["icao"]}.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
            record.update(status='extracted',notes=data['extraction']['notes'],ils_equipment_in_ad19=data['extraction']['ils_equipment_in_ad19'])
        except Exception as exc:
            record.update(status='unresolved',reason=str(exc))
        report.append(record)
    (OUT/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Extracted',sum(r['status']=='extracted' for r in report),'of',len(report))
    for r in report:
        if r['status']=='unresolved': print(r['icao'],r['airport'],r['reason'])
    conflicts=[r for r in report if r['category']=='No ILS chart supplied' and r.get('ils_equipment_in_ad19')]
    print('No-ILS classification conflicts:',conflicts)


if __name__=='__main__':
    main()
