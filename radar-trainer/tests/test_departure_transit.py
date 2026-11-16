"""Clearance sequencing and radio transfer must not end a radar track."""
import math
import os

import pytest

from airport_profiles import get_profile
from approach_radio import readback
from command_interpreter import interpret
from command_fixtures import response
from simple_demo import validate
from traffic_scenario import TrafficRun, catalogue, transit_entry


CLEARANCE = dict(action='DEPARTURE_CLEARANCE', callsign='BAW452', runway='23',
                 turn='left', radial=180, altitude_ft=9000, squawk='0421')
TEXT = 'Speedbird four five two departure runway two three turn left establish radial one eight zero climb to flight level zero nine zero squawk zero four two one'


def run_ready():
    airport = get_profile('VOCB')
    run = TrafficRun(airport, catalogue(airport)['routine-23'])
    run.schedule(40, lambda *args: None, lambda line: None)
    return airport, run


def aircraft(airport, cs, x=0, y=0, **kwargs):
    lat, lon = airport.from_nm(x, y)
    return dict(id=cs, x=x, y=y, lat=lat, lon=lon, hdg=kwargs.pop('hdg', 180),
                alt_ft=kwargs.pop('alt_ft', 7000), gs=210, **kwargs)


def test_complete_departure_is_one_assignment_with_full_readback():
    result = interpret(TEXT, lambda *a, **k: response(TEXT, [CLEARANCE]))
    assert result['orders'] == [CLEARANCE] and result['trafscript'] == []
    assert validate(TEXT, result['orders'], [dict(id='BAW452', phase='ready')]) is None
    spoken = readback(CLEARANCE)
    for phrase in ('runway two three', 'turn left', 'radial one eight zero',
                   'flight level zero niner zero', 'squawk zero four two one', 'speedbird'):
        assert phrase in spoken


def test_partial_departure_clearance_is_not_invented():
    incomplete = {k: v for k, v in CLEARANCE.items() if k != 'squawk'}
    result = interpret(TEXT, lambda *a, **k: response(TEXT, [incomplete]))
    assert result['rejected'] and not result['orders']


def test_transferred_report_is_silent_at_http_boundary(monkeypatch):
    import atc_app
    from types import SimpleNamespace
    monkeypatch.setattr(atc_app, 'SIM', SimpleNamespace(snapshot=lambda: dict(
        aircraft=[dict(id='BAW452', phase='transferred', radio_contact=False)])))
    order = dict(action='REPORT', callsign='BAW452', fields=['level'])
    result = atc_app.process_instruction('Speedbird four five two report level', dict(orders=[order], trafscript=[]))
    assert result['rejected'] and not result['orders'] and not result['readback_text']


def test_departure_clearance_readback_then_takeoff_and_revision():
    airport, run = run_ready()
    takeoff = dict(action='TAKEOFF', callsign='BAW452', runway='23')
    assert run.procedure(takeoff, 40, [])
    assert run.procedure(CLEARANCE, 40, []) is None
    assert run.phase['BAW452'] == 'ready'
    assert run.procedure(dict(action='READBACK_CORRECT', callsign='BAW452'), 41, []) is None
    assert run.procedure(dict(CLEARANCE, radial=210, altitude_ft=10000), 42, []) is None
    assert 'BAW452' not in run.departure_confirmed
    assert run.procedure(takeoff, 43, []) is None
    created, commands = [], []
    run.schedule(80, lambda *a: created.append(a), commands.append)
    assert any(a[0] == 'BAW452' for a in created)
    assert 'ALT BAW452 10000' in commands
    assert 'HDG BAW452 217.7' not in commands
    assert run.procedure(CLEARANCE, 80, [])  # Cannot change the preflight clearance in flight.


@pytest.mark.parametrize('change', [dict(runway='05'), dict(squawk='0891'), dict(radial=361),
                                  dict(altitude_ft=1000), dict(altitude_ft=9050)])
def test_invalid_departure_does_not_arm_takeoff(change):
    _, run = run_ready()
    assert run.procedure(dict(CLEARANCE, **change), 40, [])
    assert not run.departure_clearances


def test_departure_tracks_radial_and_manual_heading_cancels_guidance():
    airport, run = run_ready()
    run.procedure(CLEARANCE, 40, [])
    run.phase['BAW452'] = 'climbing'
    ac = aircraft(airport, 'BAW452', x=3, y=-8, hdg=228)
    commands = []
    run.update(ac, 1, commands.append)
    target = float(commands[-1].split()[-1])
    assert (target - ac['hdg'] + 180) % 360 - 180 < 0  # Left turn.
    assert target != 180  # Intercept line, not an arbitrary parallel heading.
    assert run.accept_vector('BAW452', ['ALT', 'BAW452', '11000'])
    assert 'BAW452' in run.departure_navigation
    assert run.accept_vector('BAW452', ['HDG', 'BAW452', '270'])
    commands.clear()
    run.update(ac, 1, commands.append)
    assert not commands


@pytest.mark.parametrize('cs,station,frequency', [('BAW452', 'Kochi', '128.300'), ('UAE681', 'HAL', '127.700')])
def test_early_transfer_retains_track_and_blocks_all_radio(cs, station, frequency):
    airport, run = run_ready()
    run.phase[cs] = 'climbing' if cs == 'BAW452' else 'transiting'
    ac = aircraft(airport, cs)
    run.update(ac, 1, lambda line: None)
    order = dict(action='CONTACT_UNIT', callsign=cs, station=station, frequency=frequency)
    assert run.procedure(dict(order, frequency='120.050'), 40, [ac])
    assert run.procedure(order, 40, [ac]) is None
    run.update(ac, 1, lambda line: None)
    assert ac['phase'] == 'transferred' and ac['radio_contact'] is False
    assert not run.status()['complete']
    assert not run.accept_vector(cs, ['ALT', cs, '10000'])
    assert run.procedure(order, 41, [ac])
    for command in (dict(action='REPORT', fields=['level']), dict(action='SQUAWK', value='1234'),
                    dict(action='HDG', value=90), dict(action='ACK', kind='standby')):
        assert validate(f'{cs} standby', [dict(command, callsign=cs)], [ac], airport)
    count = len(run.calls)
    run.update(aircraft(airport, cs, x=0, y=-60), 1, lambda line: None)
    assert run.phase[cs] == 'complete' and len(run.calls) == count


def test_transit_contacts_by_35nm_and_has_an_onward_route():
    airport = get_profile('VOCB')
    run = TrafficRun(airport, catalogue(airport)['routine-23'])
    created, commands = [], []
    run.schedule(40, lambda *a: created.append(a), commands.append)
    flight = run.flights['UAE681']
    entry = transit_entry(airport, flight)
    assert entry['remaining_nm'] >= 35
    assert 'LNAV UAE681 ON' in commands
    waypoints = [line for line in commands if line.startswith('ADDWPT UAE681')]
    assert waypoints == [f'ADDWPT UAE681 {lat:.7f},{lon:.7f}'
                         for lat, lon in (airport.ats_routes.fixes[fix] for fix in ['CCB', 'LENBO', 'UGABA'])]
    ac = aircraft(airport, 'UAE681', x=0, y=-35, hdg=0)
    run.update(ac, 1, commands.append)
    assert run.phase['UAE681'] == 'transiting'
    assert run.accept_vector('UAE681', ['ALT', 'UAE681', '12000'])
    assert run.accept_vector('UAE681', ['HDG', 'UAE681', '350'])


def test_transit_onward_branch_must_belong_to_the_same_airway():
    routes = get_profile('VOCB').ats_routes
    assert routes.outbound('W43', 'LENBO') == ['LENBO', 'UGABA']
    with pytest.raises(ValueError, match='No outbound W43'):
        routes.outbound('W43', 'PAMLU')


def test_boundary_request_once_and_no_level_based_departure_transfer():
    airport, run = run_ready()
    run.phase['BAW452'] = 'climbing'
    run.update(aircraft(airport, 'BAW452', alt_ft=18000), 1, lambda line: None)
    assert run.phase['BAW452'] == 'climbing'
    ac = aircraft(airport, 'BAW452', y=-23)
    run.update(ac, 1, lambda line: None)
    count = len(run.calls)
    run.update(ac, 1, lambda line: None)
    assert run.phase['BAW452'] == 'handoff_requested' and len(run.calls) == count
    assert 'Kochi' in run.calls[-1]['text']


@pytest.mark.skipif(os.getenv('ATC_TEST_LIVE_TRAFFIC') != '1', reason='opt-in BlueSky integration')
@pytest.mark.parametrize('turn', ['left', 'right'])
def test_live_departure_and_transit_survive_transfer(monkeypatch, turn):
    import atc_sim
    import bluesky_runtime as bsk
    monkeypatch.setenv('ATC_SIMPLE_DEMO', '1')
    airport = get_profile('VOCB')
    spec = catalogue(airport)['routine-23']
    spec.flights = [f for f in spec.flights if f.role != 'arrival']
    sim = atc_sim.SimManager()
    bsk.reset()
    sim._apply(dict(kind='airport', profile=airport, scenario=spec))
    sim.resume()

    def send(order):
        item = dict(kind='procedure', order=order)
        sim._apply(item)
        return item.get('rejected')

    transferred, last, seen_route, level_changed = set(), {}, False, False
    passed_fixes = set()
    for _ in range(1500):
        sim._advance(3)
        sim._update_snapshot(False, 1)
        for ac in sim.snapshot()['aircraft']:
            cs = ac['id']
            if cs == 'UAE681':
                for fix in ('CCB', 'LENBO'):
                    if math.dist((ac['x'], ac['y']), airport.to_nm(*airport.ats_routes.fixes[fix])) < 1:
                        passed_fixes.add(fix)
            if ac['phase'] == 'ready':
                assert send(dict(action='TAKEOFF', callsign=cs, runway='23'))
                assert not send(dict(CLEARANCE, turn=turn))
                assert not send(dict(action='TAKEOFF', callsign=cs, runway='23'))
            elif cs == 'UAE681' and ac['phase'] == 'transiting' and not level_changed:
                seen_route = ac['lnav'] and len(ac['route']) == 3
                sim._apply(dict(kind='cmd', line=f'ALT {cs} 9000'))
                level_changed = True
            elif ac['phase'] in ('climbing', 'transiting') and cs not in transferred and (cs != 'UAE681' or ac['alt_ft'] > 8500):
                flight = sim.traffic.flights[cs]
                assert not send(dict(action='CONTACT_UNIT', callsign=cs, station=flight.station, frequency=flight.frequency))
                transferred.add(cs)
                assert any(a['id'] == cs for a in sim.snapshot()['aircraft'])
                assert send(dict(action='SQUAWK', callsign=cs, value='1234'))
            if ac['phase'] == 'transferred':
                if cs in last:
                    assert math.dist(last[cs], (ac['x'], ac['y'])) > 0
                last[cs] = ac['x'], ac['y']
        if sim.traffic.status()['complete']:
            break
    assert seen_route and level_changed and transferred == {'BAW452', 'UAE681'}
    assert set(last) == transferred
    # The departure establishes the actual radial line even after an early transfer.
    runway = sim.traffic.runway(sim.traffic.flights['BAW452'])
    angle = math.radians(180 + runway['bearing_true'] - runway['bearing_magnetic_chart'])
    cx, cy = airport.to_nm(*airport.ats_routes.fixes['CCB'])
    x, y = last['BAW452']
    assert abs((x-cx)*math.cos(angle) - (y-cy)*math.sin(angle)) < 0.2
    # Follow each W43 waypoint, including the changed course after CCB.
    assert passed_fixes == {'CCB', 'LENBO'}
    lx, ly = airport.to_nm(*airport.ats_routes.fixes['LENBO'])
    px, py = airport.to_nm(*airport.ats_routes.fixes['UGABA'])
    x, y = last['UAE681']
    cross_track = abs((x-lx)*(py-ly) - (y-ly)*(px-lx)) / math.hypot(px-lx, py-ly)
    assert cross_track < 0.2
    assert math.hypot(x-px, y-py) < math.hypot(lx-px, ly-py)
    assert sim.traffic.status()['complete'] and not sim.snapshot()['aircraft']
