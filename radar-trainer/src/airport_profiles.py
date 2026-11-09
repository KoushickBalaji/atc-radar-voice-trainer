"""Chart data + exercise configuration; shared projection and ILS geometry."""
import json
import math
from pathlib import Path
from functools import lru_cache

DATA = Path(__file__).resolve().parents[1] / 'data' / 'airports'
FT_PER_NM = 1852 / .3048


class AirportProfile:
    def __init__(self, data, training):
        self.data = data
        self.training = dict(training, **data.get('training_overrides', {}))
        self.ICAO, self.NAME = data['icao'], data['name']
        self.LAT, self.LON = data['center']
        self.THRESHOLDS = data['runway']['ends']
        self.approach = data.get('approach')
        self.exercise = data['exercise']
        self.tower = tower_channels().get(self.ICAO)
        self.COURSE = self.approach['course_true'] if self.approach else self.threshold['bearing_true']
        self.GLIDE_ANGLE = self.approach['glide_deg'] if self.approach else None
        self.RDH_FT = self.approach['rdh_ft'] if self.approach else None
        self.INTERCEPT_ALT_FT = self.approach['intercept_alt_ft'] if self.approach else None
        self.FT_PER_NM = FT_PER_NM
        from msaw import MinimumAltitudeMonitor
        self.msaw = MinimumAltitudeMonitor(self)
        from control_area import ControlAreas
        self.control_areas = ControlAreas(self)
        from ats_routes import AirportRoutes
        self.ats_routes = AirportRoutes(self)
        from holding import load_patterns
        self.holds = load_patterns(self)
        assert len(self.THRESHOLDS) == 2
        if self.approach:
            assert 0 < self.GLIDE_ANGLE < 10
            assert self.threshold['name'] == self.approach['runway']
        else:
            assert self.exercise['practice_alt_ft'] > self.data['elevation_ft']
        assert self.training['speed_min_kt'] < self.training['speed_max_kt']

    @property
    def threshold(self):
        index = self.approach['threshold_index'] if self.approach else self.exercise.get('reference_runway_index', 0)
        return self.THRESHOLDS[index]

    def to_nm(self, lat, lon):
        return (lon-self.LON)*60*math.cos(math.radians(self.LAT)), (lat-self.LAT)*60

    def from_nm(self, x, y):
        return self.LAT+y/60, self.LON+x/(60*math.cos(math.radians(self.LAT)))

    def approach_point(self, along, cross=0):
        x,y = self.to_nm(self.threshold['lat'],self.threshold['lon'])
        a = math.radians(self.COURSE-180)
        u,v = math.sin(a),math.cos(a)
        return x+along*u+cross*v, y+along*v-cross*u

    def approach_geometry(self,x,y):
        tx,ty = self.approach_point(0)
        a = math.radians(self.COURSE-180)
        u,v = math.sin(a),math.cos(a)
        return (x-tx)*u+(y-ty)*v, (x-tx)*v-(y-ty)*u

    def glide_altitude(self, along):
        if not self.approach:
            raise ValueError('This airport has no modeled ILS approach')
        return self.threshold['elevation_ft']+self.RDH_FT+along*FT_PER_NM*math.tan(math.radians(self.GLIDE_ANGLE))

    def navaids(self):
        return [dict(a,x=self.to_nm(a['lat'],a['lon'])[0],y=self.to_nm(a['lat'],a['lon'])[1]) for a in self.data['navaids']]

    def approach_nav(self):
        if not self.approach:
            return None
        aids = self.navaids()
        fixes=[]
        for fix in self.approach['reference_fixes']:
            ref=aids[fix['reference']]
            along,cross=self.approach_geometry(ref['x'],ref['y'])
            x,y=self.approach_point(along+math.sqrt(fix['distance_nm']**2-cross**2))
            fixes.append(dict(name=fix['name'],x=x,y=y))
        distances = [dict(name=f'{d} NM THR', x=self.approach_point(d)[0], y=self.approach_point(d)[1], type='distance')
                     for d in range(5, int(self.approach['line_length_nm'])+1, 5)]
        return dict(self.approach,line=[list(self.approach_point(0)),list(self.approach_point(self.approach['line_length_nm']))],fixes=fixes, distance_markers=distances)

    def aircraft(self):
        start=self.exercise['start']
        from entry_area import entry_position
        entry = entry_position(self)
        lat,lon=self.from_nm(*self.approach_point(entry['along_nm'],entry['cross_nm']))
        return {**{k:v for k,v in start.items() if k not in ('along_nm','cross_nm')},'lat':lat,'lon':lon}

    def display_range(self):
        # Fit the geographically chosen entry; the viewport never sets the entry.
        entry = self.aircraft()
        extents = [math.hypot(*self.to_nm(entry['lat'],entry['lon']))]
        extents.extend(math.hypot(*xy) for branch in self.ats_routes.branches for xy in branch['points'])
        return max(self.data['range_nm'], math.ceil(max(extents)+4))

    def info(self):
        from entry_area import entry_position
        from traffic_scenario import catalogue
        from readback import num_words, callsign_telephony
        level=self.INTERCEPT_ALT_FT if self.approach else self.exercise['practice_alt_ft']
        spoken=num_words(level//1000)+' thousand'
        if level%1000: spoken+=' '+num_words((level%1000)//100)+' hundred'
        cs=callsign_telephony(self.exercise['start']['callsign'])
        return dict(icao=self.ICAO,name=self.NAME,elevation_ft=self.data['elevation_ft'],
                    scenarios=[dict(id=s.id,title=s.title) for s in catalogue(self).values()],
                    mode='ils' if self.approach else 'vectoring',
                    scope_note=self.data.get('scope_note'),
                    tower=self.tower,
                    tower_handover=self.exercise.get('tower_handover'),
                    runway=self.data['runway'],approach=self.approach,training=self.training,
                    range_nm=self.display_range(),aircraft=self.aircraft(),entry=entry_position(self),
                    examples=[f"{cs}, turn right heading {num_words(str(self.exercise['suggested_heading']).zfill(3))}.",
                              f"{cs}, descend to {spoken} feet.",
                              f"{cs}, reduce speed to {num_words(self.training['speed_max_kt'])} knots."])

    def nav(self):
        from entry_area import polygons
        ends=[dict(t,x=self.to_nm(t['lat'],t['lon'])[0],y=self.to_nm(t['lat'],t['lon'])[1]) for t in self.THRESHOLDS]
        holds = [dict(p, xy=self.to_nm(*p['position'])) for p in self.holds.values()]
        return dict(ats_routes=self.ats_routes.overlay(), holds=holds, airports=[dict(name=f'{self.ICAO} · {self.NAME}',x=0,y=0)],
                    runways=[dict(self.data['runway'],ends=ends)],navaids=self.navaids(),approach=self.approach_nav(),
                    center=[self.LAT,self.LON],range_nm=self.display_range(),waypoints=[],fixes=[],routes=[],sector=[],entry_areas=polygons(self),control_areas=self.control_areas.nav(),profile=self.info(), msaw=self.msaw.nav())


@lru_cache
def get_profile(icao='VOCB'):
    # Only registered local JSON files; never resolve user input as a path.
    paths={p.stem:p for p in DATA.glob('*.json') if p.stem != 'training'}
    if icao not in paths: raise ValueError('Unknown airport profile')
    return AirportProfile(json.loads(paths[icao].read_text(encoding='utf-8')),
                          json.loads((DATA/'training.json').read_text(encoding='utf-8')))


@lru_cache
def tower_channels():
    path = DATA.parent / 'tower_channels.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def available():
    # Listing does not construct every airport's geometry or warning polygons.
    result=[]
    for path in sorted(DATA.glob('*.json')):
        if path.stem == 'training':
            continue
        data=json.loads(path.read_text(encoding='utf-8'))
        result.append(dict(icao=data['icao'],name=data['name'],
                           mode='ils' if data.get('approach') else 'vectoring'))
    return sorted(result,key=lambda item:item['name'])
