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


def test_demo_does_not_execute_hinted_flight_when_verifier_misheard_it(monkeypatch):
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
    def recognize(data, keywords=()):
        assert data == original
        return ('Air France' if keywords else 'Yeah friends') + ' one two three turn right heading 270'
    monkeypatch.setattr(app.AI, 'asr', recognize)
    # Even if the interpreter guesses the same in-sector aircraft twice.
    monkeypatch.setattr(app.AI, 'interpret', lambda _: {
        'orders': [dict(callsign='AFR123', action='HDG', value=270)]})
    monkeypatch.setattr(app, '_handle_instruction', lambda *_: pytest.fail('must not execute'))
    monkeypatch.setattr(app, 'emit', lambda _: None)
    evidence = []
    monkeypatch.setattr(app, '_voice_evidence', evidence)
    out = app.demo_voice(original)
    assert out['orders'] == [] and 'Callsign unclear' in out['rejected'][0]
    assert evidence[0]['transcripts'][1].startswith('Yeah friends')
