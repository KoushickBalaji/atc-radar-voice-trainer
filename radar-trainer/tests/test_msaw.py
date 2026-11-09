import math
import pytest
from airport_profiles import AirportProfile, get_profile
from msaw import contains


@pytest.mark.parametrize('lat,lon,minimum', [
    (12.92, 74.62, 2400), (13.36, 75.03, 5500),
    (13.20, 75.08, 6600), (13.16, 75.29, 8400), (12.88, 75.30, 3500),
    (13.015, 75.30, 6600),  # narrow lower continuation of the 6600 region
])
def test_chart_interiors_and_altitude_threshold(lat, lon, minimum):
    monitor = get_profile('VOML').msaw
    ac = dict(lat=lat, lon=lon, alt_ft=minimum - 1)
    assert monitor.evaluate(ac)['minimum_ft'] == minimum
    assert monitor.evaluate(ac)['status'] == 'warning'
    ac['alt_ft'] = minimum
    assert monitor.evaluate(ac)['status'] == 'clear'
    ac['alt_ft'] += 100
    assert monitor.evaluate(ac)['status'] == 'clear'


def test_shared_boundaries_use_highest_minimum():
    p = get_profile('VOML')
    for name, minimum in [('A3', 6600), ('A5', 6600), ('A14', 8400), ('A13', 8400)]:
        lat, lon = p.data['msaw']['points'][name]
        assert p.msaw.evaluate(dict(lat=lat, lon=lon, alt_ft=0))['minimum_ft'] == minimum
    a, b = [p.data['msaw']['points'][name] for name in ('A1', 'A5')]
    ac = dict(lat=(a[0]+b[0])/2, lon=(a[1]+b[1])/2, alt_ft=5000)
    assert p.msaw.evaluate(ac)['minimum_ft'] == 5500
    ac['lon'] -= .001
    assert p.msaw.evaluate(ac)['status'] == 'clear'
    ac['lon'] += .002
    assert p.msaw.evaluate(ac)['status'] == 'warning'


def test_no_uncovered_holes_in_chart_interior():
    p = get_profile('VOML')
    for radius in (0, 5, 10, 15, 20, 25, 29):
        for degrees in range(0, 360, 3):
            lat, lon = p.from_nm(radius*math.sin(math.radians(degrees)), radius*math.cos(math.radians(degrees)))
            assert p.msaw.evaluate(dict(lat=lat, lon=lon, alt_ft=9000))['status'] == 'clear'


def test_missing_data_outside_coverage_and_invalid_state_are_not_clear():
    p = get_profile('VOML')
    assert p.msaw.evaluate(dict(lat=0, lon=0, alt_ft=9000))['status'] == 'outside_coverage'
    assert p.msaw.evaluate(dict(lat=float('nan'), lon=75, alt_ft=9000))['status'] == 'invalid_position'
    data = dict(p.data)
    data.pop('msaw')
    assert AirportProfile(data, p.training).msaw.evaluate(p.aircraft())['status'] == 'unavailable'


def test_ils_suspension_requires_capture_and_current_tracking():
    p = get_profile('VOML')
    lat, lon = p.from_nm(*p.approach_point(5))
    ac = dict(lat=lat, lon=lon, alt_ft=p.glide_altitude(5), hdg=p.COURSE)
    for phase in ('armed', 'localizer', 'missed', None):
        assert p.msaw.evaluate(ac, phase)['status'] == 'warning'
    for phase in ('glideslope', 'complete'):
        assert p.msaw.evaluate(ac, phase)['status'] == 'approach_suspended'
    ac['alt_ft'] -= 100
    assert p.msaw.evaluate(ac, 'glideslope')['status'] == 'warning'
    ac['alt_ft'] += 100
    ac['hdg'] += 20
    assert p.msaw.evaluate(ac, 'glideslope')['status'] == 'warning'


def test_coimbatore_localizer_level_segment_then_glide_descent():
    airport = get_profile('VOCB')
    def status(distance, altitude, phase, cross=0):
        lat, lon = airport.from_nm(*airport.approach_point(distance, cross))
        return airport.msaw.evaluate(dict(lat=lat, lon=lon, alt_ft=altitude, trk=airport.COURSE), phase)['status']
    assert status(9, 3190, 'armed') == 'warning'
    assert status(9, 3190, 'localizer') == 'approach_suspended'
    assert status(9, 2900, 'localizer') == 'warning'
    assert status(9, 3190, 'localizer', cross=.4) == 'warning'
    assert status(4, 3190, 'localizer') == 'warning'
    altitude = airport.glide_altitude(4)
    assert status(4, altitude, 'glideslope') == 'approach_suspended'
    assert status(4, altitude - 200, 'glideslope') == 'warning'
    assert status(4, altitude, 'going_around') == 'warning'


def test_general_polygon_configuration_and_overlap():
    original = get_profile('VOCB')
    data = dict(original.data, msaw=dict(source={}, points={'a':[11,77], 'b':[12,77], 'c':[11,78]},
        regions=[dict(id='one', minimum_ft=4000, boundary=['a','b','c'], label=[11.2,77.2]),
                 dict(id='two', minimum_ft=5000, boundary=['a','b','c'], label=[11.2,77.2])]))
    monitor = AirportProfile(data, original.training).msaw
    assert monitor.evaluate(dict(lat=11.2, lon=77.2, alt_ft=4500))['minimum_ft'] == 5000
    assert contains(0, 0, [(0,0),(1,0),(0,1)])


def test_mangaluru_chart_warning_and_corrective_climb():
    p = get_profile('VOML')
    # Check a known chart location independently of entry placement.
    lat, lon = p.from_nm(*p.approach_point(22, 3))
    ac = dict(lat=lat, lon=lon, alt_ft=5000)
    result = p.msaw.evaluate(ac)
    assert result['status'] == 'warning' and result['deficit_ft'] == 3400
    ac['alt_ft'] = 8400
    assert p.msaw.evaluate(ac)['status'] == 'clear'


@pytest.mark.parametrize('lat,lon,minimum', [
    (11.02,77.27,3200), (10.90,76.97,5800), (11.16,76.88,7400),
    (11.43,76.98,9500), (11.24,76.90,9500), (10.97,76.65,9500),
    (11.17,76.63,11000),
])
def test_coimbatore_chart_regions(lat, lon, minimum):
    monitor = get_profile('VOCB').msaw
    ac = dict(lat=lat, lon=lon, alt_ft=minimum-100)
    result = monitor.evaluate(ac)
    assert result['minimum_ft'] == minimum and result['status'] == 'warning'
    ac['alt_ft'] = minimum
    assert monitor.evaluate(ac)['status'] == 'clear'


def test_coimbatore_shared_vertices_and_coverage():
    p = get_profile('VOCB')
    for name, minimum in [('S',11000), ('W',11000), ('P',11000),
                          ('G',9500), ('Y',9500), ('J1',9500), ('L1',9500),
                          ('L2',7400), ('R',5800), ('L',5800), ('F',9500)]:
        lat, lon = p.data['msaw']['points'][name]
        assert p.msaw.evaluate(dict(lat=lat,lon=lon,alt_ft=0))['minimum_ft'] == minimum
    for radius in (0,5,10,15,20):
        for angle in range(0,360,5):
            lat,lon=p.from_nm(radius*math.sin(math.radians(angle)), radius*math.cos(math.radians(angle)))
            assert p.msaw.evaluate(dict(lat=lat,lon=lon,alt_ft=12000))['status'] == 'clear'
    assert p.msaw.evaluate(dict(lat=12,lon=78,alt_ft=12000))['status'] == 'outside_coverage'
    assert p.msaw.evaluate(p.aircraft())['status'] == 'outside_coverage'


@pytest.mark.parametrize('key,value', [('schema_version',2), ('altitude_unit','m'),
    ('altitude_reference','AGL'), ('coordinate_reference','unknown')])
def test_unsupported_chart_conventions_fail_explicitly(key,value):
    p = get_profile('VOCB')
    data = dict(p.data, msaw=dict(p.data['msaw'], **{key:value}))
    with pytest.raises(ValueError, match='Unsupported SMAC'):
        AirportProfile(data,p.training)


def test_invalid_chart_coordinate_rejected():
    p=get_profile('VOCB')
    data=dict(p.data, msaw=dict(p.data['msaw'], points={'a':[91,77]}))
    with pytest.raises(ValueError, match='latitude/longitude'):
        AirportProfile(data,p.training)
