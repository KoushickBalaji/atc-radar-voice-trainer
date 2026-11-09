"""Reviewed airport airspace volumes. Independent of SMAC and entry envelopes."""
import json
import math
from pathlib import Path

from msaw import contains

DATA = Path(__file__).resolve().parents[1] / 'data' / 'control_areas'
EXIT_LOOKAHEAD_S = 60  # Training setting, in simulation seconds.


def validate(data, icao):
    if data.get('schema_version') != 1 or data.get('icao') != icao or data.get('reviewed') is not True:
        raise ValueError('Control-area schema, ICAO or review flag invalid')
    areas = data['areas']
    ids = [a['id'] for a in areas]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Control areas need unique IDs')
    def point(p):
        if len(p) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in p) or not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180):
            raise ValueError('Invalid latitude/longitude')
    for a in areas:
        if not a.get('name') or a['kind'] not in ('CTR', 'CTA', 'TMA', 'ATZ') or not a.get('classification') or not a.get('hours'):
            raise ValueError('Missing airspace metadata')
        if not a.get('source', {}).get('evidence') or not (a['source'].get('file') or a['source'].get('url')):
            raise ValueError('Source and evidence required')
        for limit in (a['lower'], a['upper']):
            if limit['reference'] not in ('SFC', 'AMSL', 'FL', 'UNL'):
                raise ValueError('Unsupported vertical reference')
            if limit['reference'] in ('AMSL', 'FL') and (not isinstance(limit.get('value'), (int, float)) or not math.isfinite(limit['value'])):
                raise ValueError('Invalid vertical limit')
        if a['lower']['reference'] == 'UNL' or a['upper']['reference'] == 'SFC':
            raise ValueError('Invalid vertical ordering')
        if a['lower']['reference'] == a['upper']['reference'] and a['lower']['value'] >= a['upper']['value']:
            raise ValueError('Reversed vertical limits')
        if any(e not in ids or e == a['id'] for e in a['excludes']):
            raise ValueError('Invalid exclusion reference')
        if a['shape'] == 'circle':
            point(a['center'])
            if not 0 < a['radius_nm'] <= 500: raise ValueError('Invalid radius')
        elif a['shape'] == 'polygon':
            if len(a['edges']) < 3 or 'center' in a['edges'][0]: raise ValueError('Invalid polygon')
            for e in a['edges']:
                point(e['point'])
                if 'center' in e:
                    point(e['center'])
                    if type(e['clockwise']) is not bool or not 0 < e['radius_nm'] <= 500: raise ValueError('Invalid arc')
        else:
            raise ValueError('Unsupported shape')
    # Exclusions describe base volumes, not nested Boolean expressions.
    if any(next(b for b in areas if b['id'] == e)['excludes'] for a in areas for e in a['excludes']):
        raise ValueError('Nested exclusions are unsupported')
    return data


def boundary(airport, area):
    if area['shape'] == 'circle':
        cx, cy = airport.to_nm(*area['center'])
        return [(cx + area['radius_nm'] * math.sin(math.radians(a)), cy + area['radius_nm'] * math.cos(math.radians(a))) for a in range(360)]
    points = []
    for e in area['edges']:
        end = airport.to_nm(*e['point'])
        if 'center' in e:
            cx, cy = airport.to_nm(*e['center'])
            start = math.atan2(points[-1][0]-cx, points[-1][1]-cy)
            finish = math.atan2(end[0]-cx, end[1]-cy)
            radius = e['radius_nm']
            if any(abs(math.hypot(x-cx,y-cy)-radius) > .2 for x,y in (points[-1],end)):
                raise ValueError('Arc endpoint does not match published radius')
            direction = 1 if e['clockwise'] else -1
            sweep = (direction*(finish-start)) % (2*math.pi)
            steps = max(1, math.ceil(math.degrees(sweep)/.25))
            for i in range(1,steps):
                angle = start + direction*sweep*i/steps
                points.append((cx+radius*math.sin(angle),cy+radius*math.cos(angle)))
        points.append(end)
    return points


class ControlAreas:
    def __init__(self, airport):
        self.airport = airport
        path = DATA / (airport.ICAO + '.json')
        self.config = validate(json.loads(path.read_text(encoding='utf-8')), airport.ICAO) if path.exists() else None
        self.areas = [dict(a, points=boundary(airport,a)) for a in self.config['areas']] if self.config else []

    def nav(self):
        return self.areas

    def observe(self, aircraft, handed_off=False):
        result = self.evaluate(aircraft)
        # Confirmed presence in any configured volume starts approach control.
        # An arriving aircraft outside, or one transferred to tower, is ineligible.
        result['exit_in_s'] = None
        if result['status'] == 'inside' and not handed_off:
            result['exit_in_s'] = self.project_exit(aircraft)
        return result

    def project_exit(self, aircraft, horizon=EXIT_LOOKAHEAD_S, volume=None):
        track, speed, rate = (aircraft.get(k) for k in ('trk','gs','vs_fpm'))
        if any(v is None or not math.isfinite(v) for v in (track,speed,rate)) or speed < 0:
            return None
        x, y = self.airport.to_nm(aircraft['lat'], aircraft['lon'])
        bearing = math.radians(track)
        vx, vy = speed * math.sin(bearing) / 3600, speed * math.cos(bearing) / 3600
        vz = rate / 60
        alt = aircraft['alt_ft']
        selected = aircraft.get('sel_alt_ft')
        level_at = horizon
        if selected is not None and vz and (selected-alt)/vz >= 0:
            level_at = min(level_at, (selected-alt)/vz)
        pressure = aircraft.get('pressure_alt_ft')
        cuts = {0., float(horizon)}
        # Membership can change only at a lateral edge or a vertical limit.
        # Partition the route there so a short excursion followed by re-entry is visible.
        for area in self.areas:
            points = area['points']
            prev = points[-1]
            for end in points:
                px, py = prev
                ex, ey = end[0]-px, end[1]-py
                prev = end
                det = vx*ey - vy*ex
                if abs(det) < 1e-12:
                    continue
                t = ((px-x)*ey - (py-y)*ex) / det
                u = ((px-x)*vy - (py-y)*vx) / det
                if 0 <= u <= 1 and 0 <= t < horizon:
                    cuts.add(t)
            for limit in (area['lower'], area['upper']):
                ref = limit['reference']
                if not vz or ref not in ('AMSL','FL') or (ref == 'FL' and pressure is None):
                    continue
                delta = limit['value']-alt if ref == 'AMSL' else limit['value']*100-pressure
                t = delta / vz
                if 0 <= t <= level_at:
                    cuts.add(t)
        times = sorted(cuts)
        for start, end in zip(times,times[1:]):
            t = (start+end)/2
            lat, lon = self.airport.from_nm(x+vx*t,y+vy*t)
            climb = vz * min(t, level_at)
            future = dict(lat=lat, lon=lon, alt_ft=alt+climb)
            if pressure is not None:
                future['pressure_alt_ft'] = pressure+climb
            membership = self.evaluate(future)
            outside = membership['status'] == 'outside' if volume is None else (
                volume not in membership['areas'] and volume not in membership['uncertain'])
            if outside:
                return math.ceil(start)
        return None

    def evaluate(self, aircraft):
        if not self.config: return dict(status='unavailable', areas=[], uncertain=[])
        try:
            lat, lon, alt = (float(aircraft[k]) for k in ('lat','lon','alt_ft'))
            if not all(math.isfinite(v) for v in (lat,lon,alt)) or not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError()
        except (KeyError, TypeError, ValueError):
            return dict(status='invalid_position', areas=[], uncertain=[])
        x,y = self.airport.to_nm(lat,lon)
        def membership(a):
            if not contains(x,y,a['points']): return False
            unknown = a['hours'] != 'H24'
            for lower, limit in ((True,a['lower']),(False,a['upper'])):
                ref = limit['reference']
                if ref in ('SFC','UNL'): continue  # airborne simulation; no terrain-height claim
                value = alt if ref == 'AMSL' else aircraft.get('pressure_alt_ft')
                if value is None or not math.isfinite(value):
                    unknown = True
                    continue
                bound = limit['value'] * (100 if ref == 'FL' else 1)
                if (lower and value < bound) or (not lower and value > bound): return False
            return None if unknown else True
        base = {a['id']:membership(a) for a in self.areas}
        inside, uncertain = [], []
        for a in self.areas:
            state = base[a['id']]
            excluded = [base[e] for e in a['excludes']]
            if state is False or True in excluded: continue
            if state is None or None in excluded: uncertain.append(a['name'])
            else: inside.append(a['name'])
        return dict(status='inside' if inside else 'uncertain' if uncertain else 'outside', areas=inside, uncertain=uncertain)
