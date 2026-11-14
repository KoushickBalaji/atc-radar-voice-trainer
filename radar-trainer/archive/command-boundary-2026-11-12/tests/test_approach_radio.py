import json
import math
from types import SimpleNamespace
import pytest
import approach_radio as radio
from airport_profiles import get_profile, available
from ils_trainer import ILSTrainer
from atc_sim import SimManager

CLEAR = dict(callsign='AFR123', action='CLEAR_ILS', runway='23')
CONTACT = dict(callsign='AFR123', action='CONTACT_TOWER', frequency='118.150', station='tower')


def test_clearance_required_before_capture_and_handoff_follows_stability():
    p = get_profile('VOCB')
    trainer = ILSTrainer(p)
    def ac(along, alt=3200, vs=0):
        x,y = p.approach_point(along)
        return dict(x=x,y=y,hdg=p.COURSE,trk=p.COURSE,alt_ft=alt,cas_kt=180,gs=180,vs_fpm=vs)
    trainer.update(ac(9),1)
    assert trainer.phase == 'awaiting_clearance'
    assert radio.validate(CONTACT,p,trainer.phase)
    trainer.clear_approach(3200)
    trainer.update(ac(9),1)
    assert trainer.phase == 'localizer'
    assert radio.validate(CONTACT,p,trainer.phase)
    along=(3200-p.threshold['elevation_ft']-p.RDH_FT)/(p.FT_PER_NM*math.tan(math.radians(p.GLIDE_ANGLE)))
    trainer.update(ac(along),1)
    for _ in range(10):
        along-=.05
        trainer.update(ac(along,p.glide_altitude(along),-900),1)
    assert trainer.phase=='glideslope'
    assert radio.validate(CONTACT,p,trainer.phase) is None
    # Sim-thread command handling advances only an accepted transfer.
    sim = SimManager()
    sim.airport=p;sim._ils=trainer
    sim._update_snapshot=lambda *args: None
    wrong=dict(kind='procedure',order={**CONTACT,'frequency':'118.750'})
    sim._apply(wrong)
    assert wrong['rejected'] and trainer.phase=='glideslope'
    sim._apply(dict(kind='procedure',order=CONTACT))
    assert trainer.phase=='complete'
    assert trainer.pilot_call is None
    sim.pause();sim.resume();assert sim._paused


def test_handover_at_capture_before_request_ends_exercise():
    p = get_profile('VOCB')
    trainer = ILSTrainer(p)
    trainer.phase = 'localizer'
    trainer.below_seen = True
    distance = 6.01
    x, y = p.approach_point(distance)
    trainer.update(dict(x=x, y=y, hdg=p.COURSE, alt_ft=p.glide_altitude(distance),
                        cas_kt=175, vs_fpm=0), 1)
    assert trainer.phase == 'glideslope' and trainer.pilot_call is None
    sim = SimManager()
    sim.airport, sim._ils = p, trainer
    sim._update_snapshot = lambda *args: None
    item = dict(kind='procedure', order=CONTACT)
    sim._apply(item)
    assert not item['rejected'] and trainer.phase == 'complete'


@pytest.mark.parametrize('still_current', [True, False])
def test_autonomous_pilot_audio_uses_callsign_voice_and_drops_superseded_calls(monkeypatch, still_current):
    import asyncio
    import atc_app as app
    call = dict(id='call1', callsign='AFR123', text='Air France one two three, confirm contact tower.')
    generated, events = [], []
    def speak(text, voice):
        generated.append((text, voice))
        return b'audio'
    monkeypatch.setattr(app.AI, 'tts', speak)
    monkeypatch.setattr(app.SIM, 'snapshot', lambda: {'pilot_call':call if still_current else None})
    monkeypatch.setattr(app, 'emit', events.append)
    asyncio.run(app._voice_pilot_call(call))
    assert generated == [(call['text'], app.voices.voice_for_callsign('AFR123', app.AI.tts_pool))]
    assert events == ([dict(type='pilot_audio', id='call1', audio_b64='YXVkaW8=')] if still_current else [])


@pytest.mark.parametrize('change', [{'runway':'05'}, {'runway':'23R'}, {'callsign':'BAW123'}])
def test_wrong_clearance_is_not_repaired(change):
    assert radio.validate({**CLEAR,**change},get_profile('VOCB'),'awaiting_clearance')


@pytest.mark.parametrize('change', [{'frequency':'118.750'}, {'frequency':'nan'}, {'station':'Mangaluru Tower'}, {'callsign':'AFR124'}])
def test_wrong_handoff_is_not_accepted(change):
    assert radio.validate({**CONTACT,**change},get_profile('VOCB'),'handoff_ready')


@pytest.mark.parametrize('raw', ['[]', '{}', '[{}]', 'not json', json.dumps([{**CLEAR,'runway':'37'}]),json.dumps([CLEAR,CONTACT])])
def test_interpretation_fails_closed(raw):
    result=radio.interpret('Air France 123 cleared ILS',lambda _:raw)
    assert not result['orders'] and result['rejected']


def test_interpretation_has_no_expected_airport_values():
    def chat(messages):
        assert 'VOCB' not in json.dumps(messages)
        return json.dumps([{**CLEAR,'runway':'24'}])
    r=radio.interpret('Air France 123 cleared ILS approach runway 24',chat)
    assert r['orders'][0]['runway']=='24'  # remains wrong for VOCB; validated later
    assert radio.validate(r['orders'][0],get_profile('VOCB'),'awaiting_clearance')
    assert radio.readback(CONTACT)=='contact tower one one eight decimal one five zero, air france one two three'
    assert 'two three right' in radio.readback({**CLEAR,'runway':'23R'})


@pytest.mark.parametrize('spoken,canonical', [('AIRFRANCE123','AFR123'),('speedbird57','BAW57'),('lufthansa eight eight','DLH88')])
def test_procedure_path_uses_existing_domain_callsign_normalizer(spoken,canonical):
    result=radio.interpret('clearance',lambda _:json.dumps([{**CLEAR,'callsign':spoken}]))
    assert result['orders'][0]['callsign']==canonical


def test_all_ils_airports_have_sourced_channels_and_separate_distance_markers():
    for item in available():
        p=get_profile(item['icao'])
        if p.approach:
            assert p.tower and p.tower['source_page']>0
            nav=p.nav()['approach']
            for marker in nav['distance_markers']:
                along,cross=p.approach_geometry(marker['x'],marker['y'])
                assert along==pytest.approx(float(marker['name'].split()[0]))
                assert abs(cross)<1e-8
            assert 'NM THR' not in ' '.join(f['name'] for f in nav['fixes'])


def test_endpoint_does_not_read_back_rejected_state_change(monkeypatch):
    import atc_app as app
    monkeypatch.setattr(app.simple_demo,'ENABLED',True)
    fake=SimpleNamespace(airport=get_profile('VOCB'),
        snapshot=lambda:dict(aircraft=[dict(id='AFR123')],ils=dict(phase='awaiting_clearance')),
        procedure_command=lambda order:'Establish stable tracking first')
    monkeypatch.setattr(app,'SIM',fake)
    result=app.process_instruction('Air France 123 contact tower 118.150',dict(orders=[CONTACT],trafscript=[],rejected=[]))
    assert result['rejected'] and not result['orders'] and not result['readback_text']

@pytest.mark.parametrize('altitude,assigned,accepted', [
    (4999, None, True), (5000, None, False), (6000, 5000, False), (6000, 4900, True),
])
def test_pilot_enforces_approach_altitude_on_radio(monkeypatch, altitude, assigned, accepted):
    import atc_app as app
    import atc_sim
    sim = SimManager()
    sim.airport = get_profile('VOCB')
    sim._ils = ILSTrainer(sim.airport)
    ac = dict(id='AFR123', alt_ft=altitude)
    monkeypatch.setattr(atc_sim.bsk, 'state', lambda: [ac])
    monkeypatch.setattr(sim, 'snapshot', lambda: dict(aircraft=[ac]))
    monkeypatch.setattr(sim, '_update_snapshot', lambda *_: None)
    def procedure(order):
        item = dict(kind='procedure', order=order)
        sim._apply(item)
        return item.get('rejected')
    monkeypatch.setattr(sim, 'procedure_command', procedure)
    monkeypatch.setattr(app, 'SIM', sim)
    monkeypatch.setattr(app.simple_demo, 'ENABLED', True)
    if assigned:
        sim._ils.manual_command(f'ALT AFR123 {assigned}')
    result = app.process_instruction('Air France 123 cleared ILS approach runway 23', dict(orders=[CLEAR]))
    assert bool(result['orders']) == accepted
    assert sim._ils.phase == ('armed' if accepted else 'awaiting_clearance')
    assert ('cleared ILS' if accepted else 'too high for approach') in result['readback_text']


def test_capture_call_landing_readback_and_completion():
    from simple_demo import validate
    from test_ils_trainer import aircraft
    p = get_profile('VOCB')
    trainer = ILSTrainer(p)
    trainer.clear_approach(3200)
    trainer.update(aircraft(), 1)
    call = trainer.pilot_call
    assert 'request landing clearance' in call['text']
    trainer.update(aircraft(), 1)
    assert trainer.pilot_call == call
    order = dict(CLEAR, action='CLEAR_LAND')
    text = 'Air France one two three, runway two three, cleared to land'
    assert radio.interpret(text, lambda _: json.dumps([order]))['orders'] == [order]
    assert validate(text, [order], [aircraft()], p) is None
    assert radio.validate(order, p, trainer.phase) is None
    assert radio.validate(dict(order, runway='05'), p, trainer.phase)
    assert radio.validate(order, p, 'awaiting_clearance')
    assert 'cleared to land' in radio.readback(order)
    sim = SimManager()
    sim.airport, sim._ils = p, trainer
    sim._update_snapshot = lambda *_: None
    sim._apply(dict(kind='procedure', order=order))
    for distance in (6, 5, 2):
        trainer.update(aircraft(along=distance, heading=p.COURSE, alt=p.glide_altitude(distance)), 1)
        assert trainer.pilot_call is None
    assert trainer.phase == 'complete'
