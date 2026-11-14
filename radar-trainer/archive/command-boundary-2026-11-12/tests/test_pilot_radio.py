import json
from types import SimpleNamespace

import pytest

import approach_radio as radio
from airport_profiles import get_profile
from readback import pilot_report
from simple_demo import validate
from traffic_scenario import TrafficRun, catalogue


@pytest.mark.parametrize('action,key,value,text', [
    ('REPORT','fields',['level','speed'],'report level and speed'),
    ('SQUAWK','value','0421','squawk zero four two one'),
    ('QNH','value',1009,'QNH one zero zero nine'),
    ('DIRECT','fix','CCB','proceed direct charlie charlie bravo'),
    ('ACK','kind','standby','stand by'),
])
def test_radio_interpretation_preserves_structured_values(action,key,value,text):
    order=dict(callsign='AFR123',action=action,**{key:value})
    transcript='Air France one two three, '+text
    assert radio.is_procedure_text(transcript)
    assert radio.interpret(transcript, lambda messages: json.dumps([order]))['orders'] == [order]
    assert validate(transcript,[order],[dict(id='AFR123')]) is None


@pytest.mark.parametrize('order', [
    dict(action='SQUAWK',value='0890'), dict(action='SQUAWK',value=421),
    dict(action='QNH',value=29.92), dict(action='REPORT',fields=['invented']),
    dict(action='REPORT',fields=[]), dict(action='ACK',kind='anything'),
])
def test_invalid_radio_payload_is_rejected(order):
    order['callsign']='AFR123'
    assert radio.interpret('AFR123 report data', lambda messages:json.dumps([order]))['rejected']


def test_reports_use_actual_values_not_targets_and_keep_unknowns_unknown():
    ac=dict(id='AFR123',alt_ft=14800,sel_alt_ft=13000,level_reference='flight_level',
            hdg=90,cas_kt=220,gs=260,vs_fpm=-1500,squawk='0421',x=3,y=4,
            position_reference='Coimbatore',route_names=['CCB'],actwp=0,assigned_speed=210)
    text=pilot_report(ac,['level','cleared_level','speed','ground_speed','squawk','qnh','route'],'Coimbatore Approach')
    assert 'flight level one four eight' in text
    assert 'cleared flight level one three zero' in text
    assert 'indicated speed two two zero' in text
    assert 'ground speed two six zero' in text
    assert 'squawk zero four two one' in text
    assert 'qnh information unavailable' in text
    assert 'charlie charlie bravo' in text
    assert 'assigned speed two one zero' in text


@pytest.mark.parametrize('text,order', [
    ('AFR123 report reaching flight level 130',dict(action='REPORT',fields=['level'])),
    ('AFR123 report heading and descend 3000 feet',dict(action='REPORT',fields=['heading'])),
    ('AFR123 standby and cleared to land',dict(action='ACK',kind='standby')),
    ('AFR123 expedite descent',dict(action='ACK',kind='standby')),
])
def test_no_false_acknowledgement_or_future_report(text,order):
    assert validate(text,[dict(callsign='AFR123',**order)],[dict(id='AFR123')])


def test_report_request_does_not_command_simulator(monkeypatch):
    import atc_app
    monkeypatch.setattr(atc_app.simple_demo,'ENABLED',True)
    monkeypatch.setattr(atc_app,'SIM',SimpleNamespace(airport=get_profile('VOCB'),
        snapshot=lambda:dict(aircraft=[dict(id='AFR123',hdg=87)])))
    result=atc_app.process_instruction('Air France one two three report heading',dict(
        orders=[dict(callsign='AFR123',action='REPORT',fields=['heading'])],trafscript=[]))
    assert not result['trafscript'] and not result['rejected']
    assert 'heading zero eight seven' in result['readback_text']


def test_level_changeovers_require_explicit_contact_and_only_request_once():
    airport=get_profile('VOCB')
    run=TrafficRun(airport,catalogue(airport)['level-changeovers-23'])
    starts=[]
    run.schedule(10,lambda *args:starts.append(args),lambda line:None)
    assert starts[0][5] == 18000
    assert 'flight level one eight zero' in run.calls[0]['text']
    # Isolate transfer monitoring from the separately tested ILS guidance.
    run.approaches['AFR123']=SimpleNamespace(update=lambda ac,dt:[],phase='awaiting_clearance',pilot_call=None,status={})
    ac=dict(id='AFR123',alt_ft=13000,sel_alt_ft=13000,actwp=0,route=[[],[]],x=30,y=30,level_reference='flight_level')
    for _ in range(2):
        run.update(ac,1,lambda line:None)
    assert sum('confirm frequency change' in c['text'] for c in run.calls) == 1
    assert 'AFR123' not in run.approach_contacted
    order=dict(callsign='AFR123',action='CONTACT_UNIT',station='Coimbatore Approach',frequency='120.050')
    assert run.procedure(dict(order,frequency='120.000'),10,[ac])
    assert run.procedure(order,10,[ac]) is None
    assert run.phase['AFR123'] != 'complete'
    assert run.calls[-1]['text'].startswith('Coimbatore Approach, air france')
    assert run.procedure(order,10,[ac])
    run.phase['BAW452']='climbing'
    dep=dict(id='BAW452',alt_ft=13999)
    run.update(dep,1,lambda line:None)
    assert run.phase['BAW452']=='climbing'
    dep['alt_ft']=14000
    run.update(dep,1,lambda line:None)
    count=len(run.calls)
    run.update(dep,1,lambda line:None)
    assert run.phase['BAW452']=='handoff_requested' and len(run.calls)==count

@pytest.mark.skipif(__import__('os').getenv('ATC_TEST_LIVE_TRAFFIC') != '1', reason='opt-in detached BlueSky integration')
def test_live_radio_and_level_transfer(monkeypatch):
    import atc_sim
    import bluesky_runtime as bsk
    monkeypatch.setenv('ATC_SIMPLE_DEMO','1')
    sim=atc_sim.SimManager()
    bsk.reset()
    airport=get_profile('VOCB')
    sim._apply(dict(kind='airport',profile=airport))
    snap=sim.snapshot()
    assert len(snap['traffic_calls'])==1
    cs=snap['aircraft'][0]['id']
    call=snap['traffic_calls'][0]['id']
    sim._update_snapshot(True,1)
    assert sim.snapshot()['traffic_calls'][0]['id']==call
    for action,value in [('SQUAWK','0421'),('QNH',1009)]:
        item=dict(kind='procedure',order=dict(callsign=cs,action=action,value=value))
        sim._apply(item)
        assert not item['rejected']
        assert sim.snapshot()['aircraft'][0][action.lower()]==value
    item=dict(kind='procedure',order=dict(callsign=cs,action='DIRECT',fix='CCB'))
    sim._apply(item)
    assert not item['rejected']
    ac=sim.snapshot()['aircraft'][0]
    assert ac['lnav'] and ac['route_names']==['CCB']
    sim._apply(dict(kind='airport',profile=airport,scenario=catalogue(airport)['level-changeovers-23']))
    sim.resume()
    ac=sim.snapshot()['aircraft'][0]
    assert round(ac['alt_ft'])==18000 and ac['level_reference']=='flight_level'
    sim._apply(dict(kind='cmd',line='ALT AFR123 13000',level_reference='flight_level'))
    for _ in range(600):
        sim._advance(2)
        sim._update_snapshot(False,1)
        if 'AFR123' in sim.traffic.contact_requested:
            break
    assert 'AFR123' in sim.traffic.contact_requested
    item=dict(kind='procedure',order=dict(callsign='AFR123',action='CONTACT_UNIT',station='Coimbatore Approach',frequency='120.050'))
    sim._apply(item)
    assert not item['rejected']
    assert any(a['id']=='AFR123' for a in sim.snapshot()['aircraft'])
    assert sim.traffic.calls[-1]['text'].startswith('Coimbatore Approach')
    item=dict(kind='procedure',order=dict(callsign='BAW452',action='TAKEOFF',runway='23'))
    sim._apply(item)
    assert not item['rejected']
    for _ in range(600):
        sim._advance(2)
        sim._update_snapshot(False,1)
        if sim.traffic.phase['BAW452']=='handoff_requested':
            break
    assert sim.traffic.phase['BAW452']=='handoff_requested'
    dep=next(a for a in sim.snapshot()['aircraft'] if a['id']=='BAW452')
    assert dep['alt_ft']>=14000

@pytest.mark.parametrize('phrase', ['heading runway', 'runway heading', 'fly runway heading', 'maintain runway heading', 'continue runway heading'])
def test_runway_heading_aliases_preserve_relative_instruction(phrase):
    text='Air France one two three, '+phrase
    result=radio.interpret(text,lambda _:pytest.fail('Runway heading does not need an LLM guess'))
    assert result['orders']==[dict(callsign='AFR123',action='RUNWAY_HEADING')]
    assert radio.is_procedure_text(text)
    assert validate(text,result['orders'],[dict(id='AFR123')],get_profile('VOCB')) is None
    assert radio.readback(result['orders'][0])=='fly runway heading, air france one two three'


@pytest.mark.parametrize('text', ['AFR123 do not fly runway heading', 'AFR123 after departure fly runway heading', 'AFR123 fly runway heading and climb 5000 feet', 'AFR123 fly runway heading two three zero'])
def test_runway_heading_does_not_drop_other_meaning(text):
    result=radio.interpret(text,lambda _:'[]')
    assert result['rejected'] or validate(text,result['orders'],[dict(id='AFR123')],get_profile('VOCB'))


def test_runway_heading_uses_runway_bearing_and_existing_heading_path(monkeypatch):
    import atc_sim
    monkeypatch.setenv('ATC_SIMPLE_DEMO','1')
    sim=atc_sim.SimManager()
    airport=get_profile('VOCB')
    ac=dict(id='AFR123',hdg=90,alt_ft=5000)
    sim._snapshot=dict(aircraft=[ac])
    commands=[]
    monkeypatch.setattr(sim,'_update_snapshot',lambda *args:None)
    monkeypatch.setattr(atc_sim.bsk,'cmd',commands.append)
    monkeypatch.setattr(atc_sim.bsk,'flush_commands',lambda:None)
    item=dict(kind='procedure',order=dict(callsign='AFR123',action='RUNWAY_HEADING'))
    sim._apply(item)
    assert item['rejected'] is None
    assert commands==[f'HDG AFR123 {airport.threshold["bearing_true"]}']
    assert airport.threshold['bearing_true'] != 230  # Do not multiply the runway designator by ten.
    sim.airport=None
    commands.clear()
    sim._apply(item)
    assert item['rejected'] and not commands


def test_departure_uses_assigned_reciprocal_runway_without_changing_scenario(monkeypatch):
    import atc_sim
    monkeypatch.setenv('ATC_SIMPLE_DEMO','1')
    sim=atc_sim.SimManager()
    spec=catalogue(sim.airport)['routine-23']
    departure=next(f for f in spec.flights if f.role=='departure')
    departure.runway='05'
    previous=departure.departure_heading
    sim.traffic=TrafficRun(sim.airport,spec)
    sim.traffic.phase[departure.callsign]='ready'
    sim._snapshot=dict(aircraft=[dict(id=departure.callsign,phase='ready')])
    monkeypatch.setattr(sim,'_update_snapshot',lambda *args:None)
    item=dict(kind='procedure',order=dict(callsign=departure.callsign,action='RUNWAY_HEADING'))
    sim._apply(item)
    assert item['rejected'] is None
    assert sim.traffic.flights[departure.callsign].departure_heading==45.72
    assert departure.departure_heading==previous
    assert sim.traffic.phase[departure.callsign]=='ready'  # Not a takeoff clearance.
