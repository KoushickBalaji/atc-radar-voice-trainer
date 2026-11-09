"""Catalogue-wide contracts and reachable ILS objectives, without provider calls."""
import math
import pytest
from airport_profiles import available, get_profile
from ils_trainer import ILSTrainer
from simple_demo import validate


def test_catalogue_obeys_import_policy():
    rows = available()
    codes = {r['icao'] for r in rows}
    assert len(rows) == len(codes) == 124
    assert {'VOBG', 'VANM', 'VOCB', 'VOML'} <= codes
    assert not codes & {'VOBL','VABB','VOMM','VEMN','VIHR','VOMD','VOTV','VOTP','VOBZ'}
    assert sum(r['mode'] == 'vectoring' for r in rows) == 51


@pytest.mark.parametrize('code', [r['icao'] for r in available()])
def test_each_profile_loads_and_has_usable_exercise(code):
    p = get_profile(code)
    nav = p.nav()
    ac = p.aircraft()
    assert all(math.isfinite(ac[k]) for k in ('lat','lon','alt_ft','hdg','spd_kt'))
    assert 0 <= ac['hdg'] < 360
    x, y = p.to_nm(ac['lat'], ac['lon'])
    assert math.hypot(x, y) < p.display_range()
    along, cross = p.approach_geometry(x, y)
    assert along > 0
    assert cross == pytest.approx(p.exercise['start']['cross_nm'])
    for field in ('callsign', 'type', 'alt_ft', 'spd_kt', 'hdg'):
        assert ac[field] == p.exercise['start'][field]
    assert len(nav['runways']) == 1 and len(p.THRESHOLDS) == 2
    assert p.data['runway']['length_m'] > 0
    assert all(-90 <= e['lat'] <= 90 and -180 <= e['lon'] <= 180 for e in p.THRESHOLDS)
    level = p.INTERCEPT_ALT_FT if p.approach else p.exercise['practice_alt_ft']
    assert validate(f"{ac['callsign']} descend", [dict(callsign=ac['callsign'],action='ALT',value=level)],
                    [dict(id=ac['callsign'],hdg=ac['hdg'])], p) is None
    if not p.approach:
        assert nav['approach'] is None
        return
    assert p.threshold['name'] == p.approach['runway']
    trainer = ILSTrainer(p)
    trainer.clear_approach()
    def aircraft(along, alt, vs=0):
        x,y = p.approach_point(along)
        return dict(x=x,y=y,hdg=p.COURSE,trk=p.COURSE,alt_ft=alt,
                    cas_kt=p.training['speed_max_kt'],gs=180,vs_fpm=vs)
    trainer.update(aircraft(p.training['localizer_max_nm']-1,level),1)
    assert trainer.phase == 'localizer'
    along = (level-p.threshold['elevation_ft']-p.RDH_FT)/(p.FT_PER_NM*math.tan(math.radians(p.GLIDE_ANGLE)))
    trainer.update(aircraft(along,level),1)
    assert trainer.phase == 'glideslope'
    for _ in range(p.training['stable_seconds']):
        along -= .05
        trainer.update(aircraft(along,p.glide_altitude(along),-900),1)
    assert trainer.phase == ('glideslope' if p.ICAO == 'VOCB' else 'handoff_ready')
