"""Publish reviewed local chart extracts; never infer ILS from its absence.

Run extraction scripts first. Existing VOCB/VOML profiles remain authoritative.
The staging evidence and manifest live outside the runtime profile directory.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from airport_profiles import AirportProfile, FT_PER_NM

STAGE = ROOT / 'outputs/airport-import'
DATA = ROOT / 'data/airports'
EXCLUDED = {'VOBL', 'VABB'}
EXISTING = {'VOCB', 'VOML'}
MISSING_ILS = {'VOMM', 'VEMN', 'VIHR', 'VOMD', 'VOTV', 'VOTP', 'VOBZ'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    training = read(DATA / 'training.json')
    rows = read(ROOT / 'outputs/airport-compatibility/inventory.json')
    manifest, pending = [], {}
    for row in rows:
        code = row['icao']
        item = dict(icao=code, name=row['airport'])
        manifest.append(item)
        if code in EXCLUDED | MISSING_ILS:
            item.update(status='excluded', reason='Deferred by user: separate airport model required' if code in EXCLUDED else 'ILS mentioned in supplied documents but ILS chart not supplied')
            continue
        if code in EXISTING:
            item.update(status='retained', mode='ils', msaw='available')
            continue
        base = read(STAGE / 'base' / f'{code}.json')
        evidence = base.pop('extraction')
        base['provenance'] = dict(geometry=evidence['source_pages'], method=evidence['method'], notes=evidence['notes'])
        base['scope_note'] = 'One aircraft and one selected runway. Airborne vectoring practice; no landing, departures, or full instrument procedure.'
        if len(evidence['all_runways']) > 1:
            base['scope_note'] += ' Other airport runways are not modeled.'
        if row['ils']:
            ils = read(STAGE / 'ils' / f'{code}.json')
            assert ils['status'] == 'reviewed', code
            base['runway'] = next(r for r in evidence['all_runways'] if ils['runway'] in [e['name'] for e in r['ends']])
            idx = next(i for i, end in enumerate(base['runway']['ends']) if end['name'] == ils['runway'])
            threshold = base['runway']['ends'][idx]
            threshold['bearing_magnetic_chart'] = ils['course_magnetic']
            course = threshold['bearing_true']
            level = int(ils['intercept_alt_ft'])
            distance = (level - threshold['elevation_ft'] - ils['rdh_ft']) / (FT_PER_NM * math.tan(math.radians(ils['glide_deg'])))
            assert distance > training['miss_distance_nm'] + 0.5, (code, distance)
            loc_min = max(7, math.ceil(distance + .5))
            loc_max = max(12, loc_min + 3)
            base['approach'] = dict(runway=ils['runway'], threshold_index=idx, course_true=course,
                course_magnetic=ils['course_magnetic'], glide_deg=ils['glide_deg'], rdh_ft=ils['rdh_ft'],
                intercept_alt_ft=level, line_length_nm=max(15, loc_max + 4), reference_fixes=[])
            base['training_overrides'] = dict(localizer_min_nm=loc_min, localizer_max_nm=loc_max)
            if 'final_speed_max_kt' in ils:
                base['training_overrides']['speed_max_kt'] = ils['final_speed_max_kt']
            base['exercise'].update(reference_runway_index=idx, command_alt_min_ft=level-200, pre_capture_floor_ft=level-200,
                suggested_heading=round(course+30)%360)
            base['exercise']['start'].update(along_nm=max(16,loc_max+4),alt_ft=max(5000,level+2000),hdg=round(course+15)%360)
            base['sources'].append(ils['source_file'])
            base['provenance']['ils'] = {k:ils[k] for k in ('source_file','source_page','level_basis','visually_reviewed','warnings')}
            base['provenance']['training'] = 'Spawn, speed envelope, localizer capture window, and tolerances are exercise settings, not published procedure minima. Final segment only; omitted chart fixes are not synthesized.'
        else:
            assert not evidence['ils_equipment_in_ad19'] and not row['ils_mentions'], code
            base['scope_note'] += ' No ILS is identified in the supplied documents; no automatic approach capture.'
        # New SMAC geometry is enabled only when an independently reviewed dataset exists.
        smac_path = STAGE / 'smac' / f'{code}.json'
        if smac_path.exists():
            base['msaw'] = read(smac_path)
            msaw = 'available'
        elif row['smac']:
            msaw = 'chart supplied; boundary validation pending'
            if code in {'VEAT','VIAR'}:
                msaw = 'unavailable: chart coverage clipped by borders without numerical boundary data'
            if code == 'VANP':
                msaw = 'unavailable: chart map and altitude table disagree'
        else:
            msaw = 'unavailable: no SMAC supplied'
        base['msaw_availability'] = msaw
        if msaw != 'available':
            base['scope_note'] += ' Minimum-altitude warnings unavailable for this airport.'
        profile = AirportProfile(base, training)
        profile.nav()
        assert -90 <= profile.LAT <= 90 and -180 <= profile.LON <= 180
        assert base['exercise']['start']['alt_ft'] <= 18000
        assert profile.threshold['elevation_ft'] < base['exercise']['command_alt_min_ft']
        pending[code] = base
        item.update(status='added', mode='ils' if base['approach'] else 'vectoring', runway=base['runway']['name'],
                    msaw=msaw, sources=base['sources'])
    assert len(pending) == 122
    assert sum(v['approach'] is None for v in pending.values()) == 51
    # All profiles validate before any runtime data is changed.
    for code, data in pending.items():
        (DATA / f'{code}.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    lines = ['# Airport import catalogue', '', '124 available airports: 73 ILS (including the existing two) and 51 without ILS. Nine excluded.', '',
        'Single-aircraft, single-selected-runway exercises. Source extracts and visual ILS checks are retained in this folder. ILS procedure restrictions, missed approaches, landings, and aircraft/runway suitability are outside this exercise. The documents are local snapshots, not a live operational database.', '',
        'SMAC availability is independent of ILS. Existing Coimbatore and Mangaluru coverage is preserved. New charts with unresolved boundaries or conflicting altitudes do not silently receive warning coverage.', '',
        '| Airport | ICAO | Status | Mode | Runway | Minimum-altitude warnings / reason |',
        '|---|---|---|---|---|---|']
    for item in manifest:
        lines.append('| '+' | '.join(str(item.get(k,'')) for k in ('name','icao','status','mode','runway'))+' | '+item.get('reason',item.get('msaw',''))+' |')
    (STAGE / 'catalogue.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'Published {len(pending)} profiles; preserved 2; excluded 9.')


if __name__ == '__main__':
    main()
