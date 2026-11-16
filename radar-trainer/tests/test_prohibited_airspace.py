import math
import pytest
from airport_profiles import get_profile


def aircraft(bearing, radius, **kwargs):
    p = get_profile('VOCB')
    cx, cy = p.to_nm(11+21/60+56/3600, 76+45/60+48/3600)
    angle = math.radians(bearing)
    lat, lon = p.from_nm(cx+radius*math.sin(angle), cy+radius*math.cos(angle))
    return dict(lat=lat, lon=lon, alt_ft=10000, trk=0, gs=0, vs_fpm=0) | kwargs


def evaluate(bearing, radius, **kwargs):
    return get_profile('VOCB').prohibited_airspace.evaluate(aircraft(bearing, radius, **kwargs))


@pytest.mark.parametrize('bearing,radius,inside', [
    (100,1.25,True), (100,1.251,False), (0,5,True), (0,5.001,False),
    (250,4,True), (60,4,True), (170,4,True), (61,4,False), (169,4,False), (0,0,True),
])
def test_sectors(bearing, radius, inside):
    assert bool(evaluate(bearing, radius)) == inside


def test_altitude_limits_and_prediction():
    assert evaluate(0,1,alt_ft=17500)[0]['status'] == 'inside'
    assert not evaluate(0,1,alt_ft=17501)
    assert evaluate(0,1,alt_ft=18000,vs_fpm=-1000)[0]['entry_in_s'] == 30
    assert not evaluate(0,1,alt_ft=19000,vs_fpm=-1000)
    assert evaluate(0,6,trk=180,gs=120)[0]['entry_in_s'] == 30
    assert not evaluate(0,6,trk=0,gs=120)
    assert not evaluate(0,6,trk=180,gs=120,alt_ft=17400,vs_fpm=1000)


def test_fast_crossing_and_clearing():
    assert evaluate(100,2,trk=280,gs=1000)[0]['status'] == 'approaching'
    assert evaluate(100,1)[0]['status'] == 'inside'
    assert not evaluate(100,2)
    assert not evaluate(0,6,trk=float('nan'),gs=200)


def test_nav_and_airport_scope():
    nav = get_profile('VOCB').nav()['prohibited_airspace']
    assert nav[0]['id'] == 'VOP 190'
    assert nav[0]['ceiling_ft'] == 17500
    assert len(nav[0]['points']) > 1000
    assert get_profile('VOML').nav()['prohibited_airspace'] == []


def sulur_aircraft(along=0, cross=0, **kwargs):
    p = get_profile('VOCB')
    zone = next(z for z in p.data['prohibited_airspace'] if z['id'] == 'SLR')
    cx, cy = p.to_nm(*zone['center'])
    a = math.radians(zone['rectangle']['bearing_true'])
    u, v = math.sin(a), math.cos(a)
    lat, lon = p.from_nm(cx+along*u+cross*v, cy+along*v-cross*u)
    return dict(lat=lat, lon=lon, alt_ft=3500, pressure_alt_ft=3500, trk=225.72, gs=0, vs_fpm=0) | kwargs


def test_sulur_geometry():
    p = get_profile('VOCB')
    zone = next(z for z in p.nav()['prohibited_airspace'] if z['id'] == 'SLR')
    ccb = p.to_nm(p.data['navaids'][0]['lat'], p.data['navaids'][0]['lon'])
    dx, dy = (zone['label'][i]-ccb[i] for i in range(2))
    assert math.hypot(dx, dy) == pytest.approx(7.5)
    assert dx == pytest.approx(-dy)
    assert dx > 0
    points = zone['points']
    assert math.dist(points[0], points[1]) == pytest.approx(8+10000/p.FT_PER_NM)
    assert math.dist(points[1], points[2]) == pytest.approx(4)
    assert math.dist(*zone['runway']) == pytest.approx(10000/p.FT_PER_NM)


def test_sulur_limits_and_prediction():
    p = get_profile('VOCB')
    evaluate = p.prohibited_airspace.evaluate
    half = 4+5000/p.FT_PER_NM
    assert evaluate(sulur_aircraft(half, 2))[0]['id'] == 'SLR'
    assert not evaluate(sulur_aircraft(half+.001))
    assert not evaluate(sulur_aircraft(cross=2.001))
    assert evaluate(sulur_aircraft(pressure_alt_ft=3999, alt_ft=4200))[0]['status'] == 'inside'
    assert not evaluate(sulur_aircraft(pressure_alt_ft=4000))
    assert not evaluate(sulur_aircraft(pressure_alt_ft=None))
    snapshot = sulur_aircraft()
    del snapshot['pressure_alt_ft']
    assert evaluate(snapshot)[0]['status'] == 'inside'
    assert evaluate(sulur_aircraft(-half-1, gs=120))[0]['entry_in_s'] == 30
    assert evaluate(sulur_aircraft(pressure_alt_ft=4500, vs_fpm=-1000))[0]['entry_in_s'] == 30
    assert not evaluate(sulur_aircraft(pressure_alt_ft=5000, vs_fpm=-1000))
    assert not evaluate(sulur_aircraft(-half-1, gs=120, trk=45.72))
    assert evaluate(sulur_aircraft(-half-1, gs=2000))[0]['status'] == 'approaching'
