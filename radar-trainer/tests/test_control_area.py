from copy import deepcopy
import math
import pytest
from airport_profiles import get_profile
from control_area import validate


def test_coimbatore_ctr_vertical_and_excluded_cta():
    a = get_profile('VOCB')
    monitor = a.control_areas
    ac = dict(lat=11.0269444444, lon=77.0416666667, alt_ft=3000)
    assert monitor.evaluate(ac)['areas'] == ['Coimbatore CTR']
    assert monitor.evaluate(dict(ac,alt_ft=7500))['areas'] == ['Coimbatore CTR']
    assert monitor.evaluate(dict(ac,alt_ft=7501))['status'] == 'uncertain'
    assert monitor.evaluate(dict(ac,alt_ft=8000,pressure_alt_ft=8100))['areas'] == ['Coimbatore CTA B']
    assert monitor.evaluate(dict(ac,alt_ft=16000,pressure_alt_ft=16000))['status'] == 'outside'


def test_limits_and_exclusions_with_known_geometry():
    # Isolate vertical/exclusion semantics from the complex charted arcs.
    m = deepcopy(get_profile('VOCB').control_areas)
    square = [(-2,-2),(2,-2),(2,2),(-2,2)]
    for area in m.areas: area['points'] = square
    lat,lon=m.airport.from_nm(0,0)
    ac=dict(lat=lat,lon=lon,alt_ft=5500,pressure_alt_ft=5500)
    assert m.evaluate(ac)['areas'] == ['Coimbatore CTR']
    m.areas[0]['points']=[(10,10),(12,10),(12,12),(10,12)]
    assert m.evaluate(dict(ac,alt_ft=1999))['status']=='outside'
    assert m.evaluate(dict(ac,alt_ft=2000))['areas']==['Coimbatore CTA A']
    assert m.evaluate(ac)['areas']==['Coimbatore CTA A','Coimbatore CTA B']
    assert m.evaluate(dict(ac,alt_ft=14500,pressure_alt_ft=14500))['areas']==['Coimbatore CTA B']
    assert m.evaluate(dict(ac,alt_ft=14500,pressure_alt_ft=14501))['status']=='outside'
    m.areas[2]['hours']='HO'
    assert m.evaluate(dict(ac,alt_ft=8000))['status']=='uncertain'


def test_missing_and_invalid_data_never_claim_outside():
    assert get_profile('VOML').control_areas.evaluate({})['status']=='unavailable'
    m=get_profile('VOCB').control_areas
    assert m.evaluate({})['status']=='invalid_position'
    assert m.evaluate(dict(lat=11,lon=77,alt_ft=math.nan))['status']=='invalid_position'
    assert m.evaluate(dict(lat=0,lon=0,alt_ft=3000))['status']=='outside'


@pytest.mark.parametrize('mutation', ['icao','review','coordinate','exclusion','limits','arc'])
def test_invalid_worker_data_rejected(mutation):
    d=deepcopy(get_profile('VOCB').control_areas.config)
    if mutation=='icao': d['icao']='XXXX'
    if mutation=='review': d['reviewed']=False
    if mutation=='coordinate': d['areas'][0]['edges'][0]['point']=[999,77]
    if mutation=='exclusion': d['areas'][1]['excludes']=['missing']
    if mutation=='limits': d['areas'][1]['upper']['value']=1000
    if mutation=='arc': d['areas'][0]['edges'][1]['radius_nm']=-1
    with pytest.raises(ValueError): validate(d,'VOCB')


def test_rendering_metadata_is_airport_specific():
    a=get_profile('VOCB')
    assert len(a.nav()['control_areas'])==3
    assert not get_profile('VOML').nav()['control_areas']
    assert all(area['source']['evidence'] for area in a.control_areas.nav())


def test_predicts_each_aircraft_exit_across_the_union_of_volumes():
    monitor = deepcopy(get_profile('VOCB').control_areas)
    # Two adjoining monitored volumes, then a short gap before a third.
    for area, (west,east) in zip(monitor.areas, [(-5,0),(0,2),(2.2,5)]):
        area.update(points=[(west,-3),(east,-3),(east,3),(west,3)],
                    lower={'reference':'SFC'}, upper={'reference':'AMSL','value':7000}, excludes=[])
    def traffic(cs, x, track):
        lat,lon=monitor.airport.from_nm(x,0)
        return dict(id=cs,lat=lat,lon=lon,alt_ft=3000,trk=track,gs=180,vs_fpm=0)
    aircraft = [traffic('SAFE',-3,90), traffic('EXIT',-.5,90), traffic('INBOUND',-6,90)]
    times = {a['id']: monitor.observe(a)['exit_in_s'] for a in aircraft}
    assert times['EXIT'] == pytest.approx(50,abs=1)
    assert times['SAFE'] is None and times['INBOUND'] is None
    assert monitor.observe(dict(aircraft[1],trk=270))['exit_in_s'] is None
    assert monitor.observe(aircraft[1], handed_off=True)['exit_in_s'] is None
    climb = dict(aircraft[0],gs=0,alt_ft=6500,vs_fpm=1000)
    assert monitor.observe(climb)['exit_in_s'] == 30
    assert monitor.observe(dict(climb,sel_alt_ft=7000))['exit_in_s'] is None
    monitor.areas[0]['upper']={'reference':'FL','value':70}
    assert monitor.observe(climb)['exit_in_s'] is None


def test_lucknow_and_calicut_reviewed_control_areas():
    vilk = get_profile('VILK')
    assert len(vilk.nav()['control_areas']) == 3
    # Aircraft over Lucknow airport at 2000 ft AMSL is uncertain due to non-H24 (HO) watch hours
    ac_vilk = dict(lat=vilk.LAT, lon=vilk.LON, alt_ft=2000, pressure_alt_ft=2000)
    res_vilk = vilk.control_areas.evaluate(ac_vilk)
    assert res_vilk['status'] == 'uncertain'
    assert 'Lucknow CTR' in res_vilk['uncertain']

    vocl = get_profile('VOCL')
    assert len(vocl.nav()['control_areas']) == 3
    # Aircraft over Calicut airport at 3000 ft AMSL is within Calicut CTR
    ac_vocl = dict(lat=vocl.LAT, lon=vocl.LON, alt_ft=3000, pressure_alt_ft=3000)
    res_vocl = vocl.control_areas.evaluate(ac_vocl)
    assert res_vocl['status'] == 'inside'
    assert 'Calicut CTR' in res_vocl['areas']


def test_draft_airports_remain_unavailable():
    # Airports with border cuts, missing vertical limits, or unquantified cuts remain unavailable
    for code in ['VEAT', 'VIAR', 'VEGT', 'VOCI', 'VEBS', 'VOML']:
        p = get_profile(code)
        assert p.control_areas.evaluate({})['status'] == 'unavailable'
        assert len(p.nav()['control_areas']) == 0

