from command_fixtures import reply
import json
import math
import pytest

import approach_radio
import simple_demo
from airport_profiles import get_profile
from holding import HoldingFlight, delta, entry_for
from ils_trainer import ILSTrainer


@pytest.mark.parametrize('direction', [-1, 1])
def test_entry_sectors_rotate_and_mirror(direction):
    for relative, name in [(0,'direct'), (140,'teardrop'), (230,'parallel')]:
        assert entry_for((47 + direction*relative) % 360, 47, direction) == name


@pytest.mark.parametrize('turn,direction', [('left', -1), ('right', 1)])
def test_parallel_entry_returns_toward_holding_side_then_resumes_circuit(turn, direction):
    airport = get_profile('VOCB')
    pattern = dict(airport.holds['CCB-047'], turn=turn)
    hold = HoldingFlight(airport, pattern, 13000)
    course = hold.course
    x, y = hold.fix
    # Arrive in the parallel sector and turn outbound opposite the circuit.
    heading = (course + direction * 200) % 360
    ac = dict(id='AFR123', x=x, y=y, hdg=heading, trk=heading, cas_kt=180)
    hold.update(ac, 1)
    assert hold.entry == 'parallel'
    assert delta(hold.last_targets['HDG'] - heading) * direction < 0

    # At the end of the outbound entry leg, return toward the holding side.
    angle = math.radians(course)
    ac.update(x=x-3*math.sin(angle), y=y-3*math.cos(angle),
              hdg=(course+180)%360, trk=(course+180)%360)
    hold.phase = 'turn inbound'
    hold.update(ac, 1)
    assert delta(hold.last_targets['HDG'] - ac['hdg']) * direction < 0

    # Second fix crossing ends the entry; normal circuits use the published turn.
    ac.update(x=x, y=y, hdg=course, trk=course)
    hold.phase = 'inbound'
    hold.update(ac, 1)
    assert not hold.entry_leg
    assert hold.phase == 'turn outbound'
    assert delta(hold.last_targets['HDG'] - course) * direction > 0


@pytest.mark.parametrize('entry', ['direct', 'teardrop'])
def test_other_entries_keep_published_inbound_turn(entry):
    airport = get_profile('VOCB')
    hold = HoldingFlight(airport, airport.holds['CCB-047'], 13000)
    hold.entry, hold.entry_leg, hold.phase = entry, entry != 'direct', 'turn inbound'
    x, y = hold.fix
    heading = (hold.course+180)%360
    hold.update(dict(id='AFR123', x=x-3, y=y-3, hdg=heading, trk=heading, cas_kt=180), 1)
    assert delta(hold.last_targets['HDG'] - heading) < 0


def test_published_clearance_and_paused_timing():
    p = get_profile('VOCB')
    text = 'Air France one two three, proceed to Charlie Charlie Bravo, maintain six thousand three hundred feet, hold as published, expect further clearance at one two three zero'
    order = dict(action='HOLD_PUBLISHED', callsign='AFR123', fix='CCB', altitude_ft=6300, expected='1230')
    assert approach_radio.interpret(text, lambda messages, **kwargs: reply(messages, [order]))['orders'] == [order]
    assert simple_demo.validate(text, [order], [{'id':'AFR123'}], p) is None
    assert 'charlie charlie bravo' in approach_radio.readback(order)
    t = ILSTrainer(p)
    t.missed.assign('HDG', 270, conditional=True)
    t.start_hold(p.holds['CCB-047'], 6300, '1230')
    t.hold.phase = 'outbound'
    x,y = t.hold.fix
    ac = dict(id=t.callsign,x=x-1,y=y-1,hdg=225,trk=225,cas_kt=185)
    t.update(ac, 22)
    t.update(ac, 0)
    assert t.hold.elapsed == 22
    t.manual_command('ALT AFR123 7000')
    assert t.hold.altitude == 7000
    t.manual_command('HDG AFR123 90')
    assert t.hold is None and t.retry_ready
    assert t.missed.overrides == {'HDG':270}
