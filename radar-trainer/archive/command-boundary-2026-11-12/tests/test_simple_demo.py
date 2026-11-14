import io
import wave
import pytest
import simple_demo as demo

AIRCRAFT = [{'id': 'AFR123', 'hdg': 240}]


@pytest.mark.parametrize('text,order', [
    ('turn left heading 270', {'callsign': 'AFR123', 'action': 'HDG', 'value': 270}),
    ('contact tower', {'callsign': 'AFR123', 'action': 'HDG', 'value': 270}),
    ('heading 270', {'callsign': 'BAW123', 'action': 'HDG', 'value': 270}),
    ('speed 100', {'callsign': 'AFR123', 'action': 'SPD', 'value': 100}),
])
def test_unsupported_transmissions_rejected(text, order):
    assert demo.validate(text, [order], AIRCRAFT)


def test_short_right_turn_and_direction_readback():
    orders = [{'callsign': 'AFR123', 'action': 'HDG', 'value': 270}]
    assert demo.validate('Air France one two three turn right heading 270', orders, AIRCRAFT) is None
    assert demo.readback(orders, 'turn right heading 270', {}).startswith('turn right heading two seven zero')


@pytest.mark.parametrize('address', ['yeah friends one two three', 'one two three',
                                    'air france one two three four', 'air france one two three bravo'])
def test_single_aircraft_still_requires_its_complete_spoken_address(address):
    assert demo.validate(address + ' turn right heading 270',
                         [{'callsign': 'AFR123', 'action': 'HDG', 'value': 270}], AIRCRAFT)


def test_feet_not_changed_to_flight_level_in_readback():
    orders = [{'callsign': 'AFR123', 'action': 'ALT', 'value': 8000}]
    assert demo.readback(orders, 'descend eight thousand feet', {'AFR123': 10000}).startswith('descend eight thousand feet')
    assert demo.readback(orders, 'descend flight level zero eight zero', {'AFR123': 10000}).startswith('descend flight level zero eight zero')


def test_silent_audio_rejected_before_asr():
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(bytes(32000))
    with pytest.raises(ValueError, match='No audible speech'):
        demo.validate_audio(buf.getvalue())


def test_demo_rejects_misheard_callsign_even_when_interpreter_guesses_known_aircraft(monkeypatch):
    import atc_app as app
    from airport_profiles import get_profile
    from types import SimpleNamespace
    wav = io.BytesIO()
    with wave.open(wav, 'wb') as w:
        w.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        w.writeframes(b'\x00\x40' * 3200)
    original = wav.getvalue()
    sim = SimpleNamespace(snapshot=lambda: {'aircraft': AIRCRAFT}, airport=get_profile('VOCB'))
    monkeypatch.setattr(app, 'SIM', sim)
    contexts = []
    def recognize(data, keywords=()):
        assert data == original
        contexts.append(list(keywords))
        return 'Yeah friends one two three turn right heading 270'
    monkeypatch.setattr(app.AI, 'asr', recognize)
    # The transcript must support the aircraft even if the interpreter guesses it.
    monkeypatch.setattr(app.AI, 'interpret', lambda _: {
        'orders': [dict(callsign='AFR123', action='HDG', value=270)]})
    monkeypatch.setattr(app, '_handle_instruction', lambda *_: pytest.fail('must not execute'))
    monkeypatch.setattr(app, 'emit', lambda _: None)
    evidence = []
    monkeypatch.setattr(app, '_voice_evidence', evidence)
    out = app.demo_voice(original)
    assert len(contexts) == 1
    assert contexts[0] == evidence[0]['recognition_keywords']
    assert 'air france one two three' in contexts[0]
    assert out['orders'] == [] and 'Callsign unclear' in out['rejected'][0]
    assert evidence[0]['transcripts'] == ['Yeah friends one two three turn right heading 270']
    assert out['addressed_callsigns'] == []
    monkeypatch.setattr(app.AI, 'asr', lambda *_: 'Air France one two three turn right heading 270')
    monkeypatch.setattr(app.AI, 'interpret', lambda _: {'orders': []})
    out = app.demo_voice(original)
    assert out['addressed_callsigns'] == ['AFR123']
    assert out['orders'] == [] and out['trafscript'] == []


def test_demo_refreshes_context_per_transmission_and_skips_empty_interpretation(monkeypatch):
    import atc_app as app
    from airport_profiles import get_profile
    from types import SimpleNamespace
    traffic = [{'id': 'AFR123'}]
    sim = SimpleNamespace(snapshot=lambda: {'aircraft': list(traffic)}, airport=get_profile('VOCB'))
    monkeypatch.setattr(app, 'SIM', sim)
    monkeypatch.setattr(app.simple_demo, 'validate_audio', lambda _: None)
    monkeypatch.setattr(app.AI, 'interpret', lambda _: pytest.fail('empty transcript must not be interpreted'))
    monkeypatch.setattr(app, 'emit', lambda _: None)
    monkeypatch.setattr(app, '_voice_evidence', [])
    contexts = []
    def recognize(data, keywords=()):
        contexts.append(list(keywords))
        traffic[:] = [{'id': 'BAW456'}]
        return ''
    monkeypatch.setattr(app.AI, 'asr', recognize)
    app.demo_voice(b'audio one')
    app.demo_voice(b'audio two')
    assert len(contexts) == 2
    assert 'AFR123' in contexts[0] and 'BAW456' not in contexts[0]
    assert 'BAW456' in contexts[1] and 'AFR123' not in contexts[1]


def test_demo_upload_transcribes_and_interprets_once_before_dispatch(monkeypatch):
    import atc_app as app
    from airport_profiles import get_profile
    from types import SimpleNamespace
    calls = []
    queued = []
    aircraft = [dict(id='AFR123', hdg=240, alt_ft=5000)]
    monkeypatch.setattr(app, 'SIM', SimpleNamespace(
        airport=get_profile('VOCB'), snapshot=lambda: {'aircraft': aircraft}, enqueue=queued.append))
    monkeypatch.setattr(app.simple_demo, 'ENABLED', True)
    monkeypatch.setattr(app.simple_demo, 'validate_audio', lambda _: None)
    monkeypatch.setattr(app, 'EX', SimpleNamespace(active=False))
    monkeypatch.setattr(app, 'emit', lambda _: None)
    monkeypatch.setattr(app, '_synthesize_readback',
                        lambda out: dict(out, audio_b64=None, tts_error=None))
    transcript = 'Air France one two three turn right heading two seven zero'
    def recognize(wav, keywords):
        calls.append('asr')
        assert wav == b'audio' and 'air france one two three' in keywords
        return transcript
    def interpret(text):
        calls.append('interpret')
        assert text == transcript
        return dict(orders=[dict(callsign='AFR123', action='HDG', value=270)],
                    trafscript=['HDG AFR123 270'], rejected=[])
    monkeypatch.setattr(app.AI, 'asr', recognize)
    monkeypatch.setattr(app.AI, 'interpret', interpret)
    out = app.voice(SimpleNamespace(file=io.BytesIO(b'audio')))
    assert calls == ['asr', 'interpret']
    assert queued == ['HDG AFR123 270']
    assert out['orders'][0]['value'] == 270
    assert 'two seven zero' in out['readback_text']


def test_voice_upload_passes_live_context_to_recognition(monkeypatch):
    import atc_app as app
    from types import SimpleNamespace
    monkeypatch.setattr(app.simple_demo, 'ENABLED', False)
    monkeypatch.setattr(app, 'SIM', SimpleNamespace(
        airport=None, snapshot=lambda: {'aircraft': [{'id': 'AFR123'}]}))
    def recognize(wav, keywords):
        assert wav == b'uploaded audio'
        assert 'AFR123' in keywords and 'air france one two three' in keywords
        return 'Air France one two four'
    monkeypatch.setattr(app.AI, 'asr', recognize)
    monkeypatch.setattr(app, '_handle_instruction', lambda text: {'transcript': text})
    result = app.voice(SimpleNamespace(file=io.BytesIO(b'uploaded audio')))
    assert result['transcript'] == 'Air France one two four'


@pytest.mark.parametrize('address,cs', [('Air France one two three','AFR123'),
                                      ('Emirates six eight one','UAE681'),
                                      ('Lufthansa nine zero eight','DLH908'),
                                      ('Alpha Bravo Charlie one two','ABC12')])
@pytest.mark.parametrize('direction,heading,value', [('left','zero nine zero',90),
                                                  ('right','two seven zero',270)])
def test_standard_heading_preserves_spoken_address_and_digits(address, cs, direction, heading, value):
    result = demo.heading_instruction(f'{address}, turn {direction} heading {heading}.')
    assert result['orders'] == [dict(callsign=cs,action='HDG',value=value)]


@pytest.mark.parametrize('text', [
    'turn left heading zero nine zero',
    'Air France one two three, after passing CCB turn left heading 090',
    'Air France one two three, turn right heading 090 and descend 5000 feet',
    'Air France one two three, do not turn right heading 090',
    'Air France one two three, turn right heading four zero zero',
])
def test_heading_parser_does_not_drop_extra_meaning(text):
    assert demo.heading_instruction(text) is None


def test_standard_heading_does_not_depend_on_llm(monkeypatch):
    from ai_client import AIClient
    monkeypatch.setenv('ATC_SIMPLE_DEMO', '1')
    client = AIClient()
    monkeypatch.setattr(client._llm, 'chat', lambda *_: pytest.fail('heading must not use model inference'))
    assert client.interpret('Emirates six eight one, turn right heading zero nine zero.')['orders'] == [
        dict(callsign='UAE681', action='HDG', value=90)]
