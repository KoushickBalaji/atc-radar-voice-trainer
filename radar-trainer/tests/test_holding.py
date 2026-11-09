import json
import pytest

import approach_radio
import simple_demo
from airport_profiles import get_profile
from holding import entry_for
from ils_trainer import ILSTrainer


@pytest.mark.parametrize('direction', [-1, 1])
def test_entry_sectors_rotate_and_mirror(direction):
    for relative, name in [(0,'direct'), (140,'teardrop'), (230,'parallel')]:
        assert entry_for((47 + direction*relative) % 360, 47, direction) == name


def test_published_clearance_and_paused_timing():
    p = get_profile('VOCB')
    text = 'Air France one two three, proceed to Charlie Charlie Bravo, maintain six thousand three hundred feet, hold as published, expect further clearance at one two three zero'
    order = dict(action='HOLD_PUBLISHED', callsign='AFR123', fix='CCB', altitude_ft=6300, expected='1230')
    assert approach_radio.interpret(text, lambda _:json.dumps([order]))['orders'] == [order]
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
