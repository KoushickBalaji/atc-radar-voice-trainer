import json
from copy import deepcopy

import pytest
import approach_radio
import atc_sim
import simple_demo
from airport_profiles import get_profile
from ils_trainer import ILSTrainer
from missed_approach import procedure_for


def test_key_includes_direction_suffix_and_variant():
    airport = deepcopy(get_profile('VOCB'))
    assert procedure_for(airport)['runway'] == '23'
    for runway, variant in [('05','ILS-Z'),('23R','ILS-Z'),('23','ILS-Y')]:
        airport.approach.update(runway=runway,procedure_id=variant)
        assert procedure_for(airport) is None


def sample(p, along, alt):
    x,y = p.approach_point(along)
    return dict(id='AFR123',x=x,y=y,hdg=p.COURSE,trk=p.COURSE,alt_ft=alt,cas_kt=175)


def test_default_waits_for_both_threshold_and_altitude():
    p=get_profile('VOCB')
    trainer=ILSTrainer(p)
    trainer.phase='going_around'
    trainer.update(sample(p,.1,2500),1)
    assert trainer.missed.index==0
    trainer.update(sample(p,-.1,1990),1)
    assert trainer.missed.index==0
    trainer.update(sample(p,-.1,2000),1)
    assert trainer.missed.index==1


@pytest.mark.parametrize('phase',['awaiting_clearance','armed','localizer','glideslope','handoff_ready'])
def test_arm_waits_for_valid_handoff_and_preserves_overrides(monkeypatch,phase):
    sim=atc_sim.SimManager()
    sim.airport=p=get_profile('VOCB')
    sim._ils=trainer=ILSTrainer(p)
    trainer.phase=phase
    sim.pause()
    ac=sample(p,1,2700)
    monkeypatch.setattr(atc_sim.bsk,'state',lambda:[ac])
    sim._update_snapshot=lambda *_: None
    trainer.missed.assign('HDG',270,conditional=True)
    arm=dict(action='SET_GO_AROUND_ON_HANDOFF',icao='VOCB',runway='23',approach_id='ILS-Z',callsign='AFR123',armed=True)
    wrong=dict(kind='procedure',order=dict(arm,approach_id='ILS-Y'))
    sim._apply(wrong)
    assert wrong['rejected']
    sim._apply(dict(kind='procedure',order=arm))
    assert trainer.phase==phase and sim._paused and trainer.go_around_on_handoff
    # It is idempotent, and can be cancelled without changing flight guidance.
    sim._apply(dict(kind='procedure',order=arm))
    sim._apply(dict(kind='procedure',order=dict(arm,armed=False)))
    assert not trainer.go_around_on_handoff and trainer.phase==phase
    sim._apply(dict(kind='procedure',order=arm))
    trainer.manual_command('HDG AFR123 230')
    assert trainer.go_around_on_handoff
    assert trainer.missed.overrides=={'HDG':270}
    contact=dict(action='CONTACT_TOWER',callsign='AFR123',frequency='118.150',station='tower')
    trainer.phase='armed'
    early=dict(kind='procedure',order=contact)
    sim._apply(early)
    assert early['rejected'] and trainer.phase=='armed'
    trainer.phase='handoff_ready'
    wrong=dict(kind='procedure',order=dict(contact,frequency='118.750'))
    sim._apply(wrong)
    assert wrong['rejected'] and trainer.go_around_on_handoff
    sim._apply(dict(kind='procedure',order=contact))
    assert trainer.phase=='going_around' and not sim._paused
    assert not trainer.go_around_on_handoff and trainer.repeat_after_missed
    assert 'HDG AFR123 270' in trainer.update(ac,1)
    trainer.manual_command('HDG AFR123 300')
    assert 'HDG AFR123 300.0' in trainer.update(ac,1)


def test_repeat_returns_to_vectoring_without_teleporting_or_old_overrides():
    p=get_profile('VOCB')
    trainer=ILSTrainer(p)
    trainer.phase='going_around'
    trainer.repeat_after_missed=True
    trainer.missed.index=2
    trainer.missed.turn_established=True
    x,y=p.to_nm(*trainer.missed.plan['fixes']['CCB'])
    ac=dict(id='AFR123',x=x,y=y-.2,hdg=0,trk=0,alt_ft=6300,cas_kt=180)
    trainer.update(ac,1)
    assert trainer.phase=='holding'
    trainer.manual_command('HDG AFR123 090')
    assert trainer.phase=='awaiting_clearance' and trainer.retry_ready
    assert not trainer.missed.overrides and not trainer.go_around_on_handoff
    # At the fix, the aircraft may be beyond the original approach boundary.
    # Awaiting another clearance must not immediately fail the new attempt.
    trainer.update(sample(p,-1,6300),1)
    assert trainer.phase=='awaiting_clearance'
    assert 'another attempt' in trainer.status['message']
    trainer.clear_approach()
    trainer.update(sample(p,9,3200),1)
    assert trainer.phase=='localizer'
    assert not ILSTrainer(p).go_around_on_handoff


@pytest.mark.parametrize('phase',['complete','missed','going_around','missed_finished','missed_fix_altitude'])
def test_cannot_arm_after_attempt_ends_or_during_go_around(phase):
    sim=atc_sim.SimManager()
    sim.airport=get_profile('VOCB')
    sim._ils=ILSTrainer(sim.airport)
    sim._ils.phase=phase
    item=dict(kind='procedure',order=dict(action='SET_GO_AROUND_ON_HANDOFF',icao='VOCB',runway='23',approach_id='ILS-Z',callsign='AFR123'))
    sim._apply(item)
    assert item['rejected'] and sim._ils.phase==phase


def test_voice_conditional_requires_explicit_scope_and_one_assignment():
    order=dict(action='MISSED_INSTRUCTION',callsign='AFR123',axis='HDG',value=270)
    parse=lambda text: approach_radio.interpret(text,lambda _:json.dumps([order]))
    text='Air France one two three, on missed approach fly heading two seven zero'
    assert parse(text)['orders']==[order]
    assert parse('Air France one two three fly heading two seven zero')['rejected']
    p=get_profile('VOCB')
    for suffix in [' and climb to six thousand feet',' after the threshold',' then contact tower']:
        assert simple_demo.validate(text+suffix,[order],[{'id':'AFR123'}],p)
    assert approach_radio.validate(dict(order,callsign='BAW123'),p,'armed')
    assert approach_radio.readback(order).startswith('on missed approach, fly heading two seven zero')


@pytest.mark.parametrize('scope',['in case of missed approach','in case of a missed approach',
                                  'in the event of a missed approach','if you go around'])
def test_alternative_scopes_reserve_heading_090(scope):
    text = f'Air France one two three, fly heading zero nine zero {scope}'
    order = dict(callsign='AFR123',action='MISSED_INSTRUCTION',axis='HDG',value=90)
    assert approach_radio.interpret(text,lambda _:json.dumps([order]))['orders'] == [order]
    assert simple_demo.validate(text,[order],[{'id':'AFR123'}],get_profile('VOCB')) is None
    assert 'zero niner zero' in approach_radio.readback(order)


def test_outbound_pass_near_fix_does_not_complete_before_return_turn():
    p=get_profile('VOCB')
    trainer=ILSTrainer(p)
    trainer.phase='going_around'
    trainer.missed.index=2
    x,y=p.to_nm(*trainer.missed.plan['fixes']['CCB'])
    ac=dict(id='AFR123',x=x,y=y-.2,hdg=200,trk=200,alt_ft=5000,cas_kt=180)
    lines=trainer.update(ac,1)
    assert trainer.phase=='going_around' and 'ALT AFR123 6300' in lines
    trainer.missed.turn_established=True
    trainer.update(dict(ac,hdg=0,trk=0,alt_ft=6300),1)
    assert trainer.phase=='holding'
