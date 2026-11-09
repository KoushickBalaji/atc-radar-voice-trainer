from copy import deepcopy
import math
import pytest
from airport_profiles import AirportProfile, available, get_profile
from entry_area import catalogue, entry_position, outer_crossing, polygons
from msaw import contains


@pytest.mark.parametrize('code', [a['icao'] for a in available()])
def test_entry_is_outside_every_available_boundary_and_visible(code):
    airport = get_profile(code)
    entry = entry_position(airport)
    aircraft = airport.aircraft()
    x, y = airport.to_nm(aircraft['lat'], aircraft['lon'])
    assert math.hypot(x,y) < airport.display_range()
    if entry['status'] != 'boundary_based':
        assert entry['status'] == 'unverified'
        assert entry['along_nm'] == airport.exercise['start']['along_nm']
        return
    areas = polygons(airport) + airport.msaw.regions
    assert areas
    assert all(not contains(x,y,area['points']) for area in areas)
    crossings = [outer_crossing(airport,area['points'],entry['cross_nm']) for area in areas]
    last = max(c for c in crossings if c is not None)
    assert entry['along_nm'] == pytest.approx(last+2)
    assert entry['source']


def test_coimbatore_entry_uses_smac_and_published_approach_area():
    airport = get_profile('VOCB')
    assert len(catalogue()['VOCB']['areas']) == 3  # CTR + both APP areas
    entry = entry_position(airport)
    assert entry['along_nm'] == pytest.approx(33.6,abs=.1)
    assert airport.msaw.evaluate(airport.aircraft())['status'] == 'outside_coverage'
    # Range is a view preference, never the geographic entry policy.
    data = deepcopy(airport.data)
    data['range_nm'] = 100
    wide = AirportProfile(data, airport.training)
    assert wide.aircraft() == airport.aircraft()


def test_mangaluru_uses_outer_approach_area_instead_of_small_ctr():
    airport = get_profile('VOML')
    entry = entry_position(airport)
    assert entry['boundary'] == 'Mangalore Control Area- B'
    x,y = airport.to_nm(airport.aircraft()['lat'],airport.aircraft()['lon'])
    center = airport.to_nm(*catalogue()['VOML']['areas'][-1]['center'])
    assert math.hypot(x-center[0],y-center[1]) > 50
    assert airport.msaw.evaluate(airport.aircraft())['status'] == 'outside_coverage'


def test_missing_boundary_does_not_invent_a_radius(monkeypatch):
    import entry_area
    airport = get_profile('VOCB')
    data = deepcopy(airport.data)
    data['msaw'] = None
    unknown = AirportProfile(data,airport.training)
    monkeypatch.setattr(entry_area, 'catalogue', lambda: {})
    entry = entry_position(unknown)
    assert entry['status'] == 'unverified'
    assert entry['along_nm'] == data['exercise']['start']['along_nm']
    assert entry['source'] is None
