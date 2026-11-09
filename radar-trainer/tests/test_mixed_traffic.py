import math
import os

import pytest

from airport_profiles import get_profile
from traffic_scenario import catalogue
from simple_demo import validate


def test_scenario_discovery_and_spoken_target():
    profile = get_profile('VOCB')
    assert len(catalogue(profile)['routine-23'].flights) == 4
    assert not catalogue(get_profile('VEAT'))
    aircraft = [dict(id='BAW452', role='departure'), dict(id='AFR123', role='arrival')]
    order = [dict(callsign='BAW452', action='TAKEOFF', runway='23')]
    assert not validate('Speedbird four five two, runway two three cleared for takeoff', order, aircraft, profile)
    assert validate('Air France one two three, runway two three cleared for takeoff', order, aircraft, profile)
    assert validate('Speedbird four five two, after landing traffic cleared for takeoff', order, aircraft, profile)


def test_routes_clip_at_cta_and_arrivals_spawn_on_the_inbound_leg():
    airport = get_profile('VOCB')
    routes = airport.ats_routes
    assert {b['route'] for b in routes.branches} == {'J16','R461','V34','W114','W115','W118','W119','W43'}
    overlay = routes.overlay()
    assert len(overlay) == 11
    assert next(b for b in overlay if b['waypoint'] == 'CLC')['routes'] == ['J16','W119']
    assert not get_profile('VEAT').ats_routes.overlay()
    from msaw import contains
    area = next(a['points'] for a in airport.control_areas.areas if a['id'] == 'cta-b')
    for route, via, outside in [('W118','SATBI','AKTIM'), ('W43','DODSI','DODSI')]:
        branch = next(b for b in routes.branches if b['route'] == route and b['via'] == via)
        assert branch['outside'] == outside
        edge = branch['points'][-1]
        start = routes.entry(route, via)
        assert math.dist(edge, (start['x'],start['y'])) == pytest.approx(1)
        assert contains(start['x'],start['y'],area)
        assert not contains(2*edge[0]-start['x'],2*edge[1]-start['y'],area)
        assert start['inbound'][-1] == 'CCB'


@pytest.mark.skipif(os.getenv('ATC_TEST_LIVE_TRAFFIC') != '1', reason='opt-in detached BlueSky integration')
def test_live_four_handoffs(monkeypatch):
    import atc_sim
    import bluesky_runtime as bsk

    monkeypatch.setenv('ATC_SIMPLE_DEMO', '1')
    sim = atc_sim.SimManager()
    bsk.reset()
    airport = get_profile('VOCB')
    spec = catalogue(airport)['routine-23']
    def load():
        sim._apply(dict(kind='airport', profile=airport, scenario=spec))
        sim.resume()

    def clearance(cs, action, **fields):
        item = dict(kind='procedure', order=dict(callsign=cs, action=action, **fields))
        sim._apply(item)
        return item.get('rejected')

    load()
    initial = sim.snapshot()['aircraft']
    satbi = airport.to_nm(*airport.ats_routes.fixes['SATBI'])
    ccb = airport.to_nm(*airport.ats_routes.fixes['CCB'])
    first = next(a for a in initial if a['id'] == 'AFR123')
    assert math.dist((first['x'], first['y']), satbi) + math.dist(satbi, ccb) == pytest.approx(30, abs=0.01)
    seen_four = False
    issued_level = False
    on_base = set()
    joining_final = set()
    for tick in range(0, 4200, 3):
        sim._advance(3)
        sim._update_snapshot(False, 1)
        snap = sim.snapshot()
        seen_four |= len(snap['aircraft']) == 4
        for ac in snap['aircraft']:
            if tick == 42 and ac['role'] == 'arrival':
                assert ac['lnav'] and len(ac['route']) >= 1
            if tick == 57 and ac['role'] == 'arrival':
                assert not ac['lnav']
            cs, phase = ac['id'], ac['phase']
            if phase == 'awaiting_clearance':
                assert not clearance(cs, 'CLEAR_ILS', runway='23')
            if ac['role'] == 'arrival' and tick > 45 and phase in ('armed', 'awaiting_clearance'):
                along, cross = airport.approach_geometry(ac['x'], ac['y'])
                if math.hypot(along-30, cross-6) < 1.8:
                    on_base.add(cs)
                if cs in on_base and math.hypot(along-20, cross) < 1.5:
                    joining_final.add(cs)
                if cs in joining_final:
                    target = airport.approach_point(along-3)
                elif cs in on_base:
                    target = airport.approach_point(20)
                else:
                    target = airport.approach_point(30, 6)
                heading = math.degrees(math.atan2(target[0]-ac['x'], target[1]-ac['y'])) % 360
                if tick % 9 == 0:
                    sim._apply(dict(kind='cmd', line=f'HDG {cs} {heading:.2f}'))
                    if cs in on_base:
                        sim._apply(dict(kind='cmd', line=f'ALT {cs} 3200'))
            if phase == 'ready':
                assert ac['gs'] == 0
                if tick == 45:
                    assert clearance(cs, 'TAKEOFF', runway='05')
                    assert not clearance(cs, 'TAKEOFF', runway='23')
            if phase == 'transiting' and not issued_level:
                sim._apply(dict(kind='cmd', line=f'ALT {cs} 7000'))
                issued_level = True
            if phase == 'handoff_requested':
                assert clearance(cs, 'CONTACT_UNIT', station='Coimbatore Approach', frequency='118.000')
                assert not clearance(cs, 'CONTACT_UNIT', station='Coimbatore Approach', frequency='120.050')
            if phase == 'glideslope':
                assert not clearance(cs, 'CONTACT_TOWER', station='tower', frequency=airport.tower['frequency_mhz'])
        if sim.snapshot()['traffic']['complete']:
            break
    assert seen_four and issued_level
    final = sim.snapshot()
    assert final['traffic']['complete'], [(a['id'], a.get('ils'), a['alt_ft']) for a in final['aircraft']]
    assert final['paused'] and not final['aircraft']
    assert any('entering' in c['text'] for c in final['traffic_calls'])
    load()
    assert [(a['id'], a['lat'], a['lon']) for a in sim.snapshot()['aircraft']] == [
        (a['id'], a['lat'], a['lon']) for a in initial]
    assert not sim.snapshot()['traffic']['complete']

