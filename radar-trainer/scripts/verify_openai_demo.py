"""Paid synthetic-audio integration check, explicitly not a human ASR benchmark."""
import base64
import argparse
import io
import json
import sys
import time
from pathlib import Path
import wave
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_openai import configure
configure()
from ai_client import AIClient

BASE = 'http://127.0.0.1:8000'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--airport', choices=['VOCB', 'VOML'], default='VOCB')
ARGS = parser.parse_args()
OUT = ROOT / 'outputs' / 'verification' / ARGS.airport
OUT.mkdir(parents=True, exist_ok=True)


def post(path, **kwargs):
    r = requests.post(BASE + path, timeout=180, **kwargs)
    r.raise_for_status()
    return r.json()


def main():
    post('/api/demo/airport', json={'icao': ARGS.airport})
    post('/api/demo/reset')
    time.sleep(1)
    ai = AIClient()
    results = []
    commands = [
        ('ils-heading', 'Air France one two three, turn right heading two five five.', 'HDG', 255),
        ('ils-level', 'Air France one two three, descend to three thousand two hundred feet.', 'ALT', 3200),
        ('speed', 'Air France one two three, reduce speed to one eight zero knots.', 'SPD', 180),
    ]
    if ARGS.airport == 'VOML':
        commands[:2] = [
            ('ils-heading', 'Air France one two three, turn right heading two six eight.', 'HDG', 268),
            ('ils-level', 'Air France one two three, descend to two thousand four hundred feet.', 'ALT', 2400),
        ]
    def transmission(name, text, expected):
        path = OUT / (name + '-input.wav')
        audio = path.read_bytes() if path.exists() else ai.tts(text, 'alloy')
        # Speech API streams WAV with an unspecified length. Finalize the fixture
        # header before uploading; the browser recorder already emits finite WAV.
        import soundfile as sf
        samples, rate = sf.read(io.BytesIO(audio))
        buffer = io.BytesIO()
        sf.write(buffer, samples, rate, format='WAV', subtype='PCM_16')
        audio = buffer.getvalue()
        path.write_bytes(audio)
        # TTS WAV is mono; use the production upload route unchanged.
        r = post('/api/voice', files={'file': ('transmission.wav', audio, 'audio/wav')})
        raw_audio = r.pop('audio_b64', None)
        print(name, json.dumps(r), flush=True)
        assert r['orders'] == [expected], r
        assert not r['tts_error'] and raw_audio, r
        readback = base64.b64decode(raw_audio)
        with wave.open(io.BytesIO(readback)) as wav:
            assert wav.getnframes() > 100
        (OUT / (name + '-readback.wav')).write_bytes(readback)
        results.append(r)
    for name, text, action, value in commands:
        transmission(name, text, dict(callsign='AFR123', action=action, value=value))
    from airport_profiles import get_profile
    from readback import num_words
    profile = get_profile(ARGS.airport)
    transmission('approach-clearance',
        'Air France one two three, cleared ILS approach runway ' + num_words(profile.approach['runway']) + '.',
        dict(callsign='AFR123',action='CLEAR_ILS',runway=profile.approach['runway']))
    post('/api/sim/speed', json={'value': 20})
    post('/api/sim/resume')
    deadline = time.monotonic() + 60
    phases = []
    while time.monotonic() < deadline:
        state = requests.get(BASE + '/api/state', timeout=5).json()
        assert state['airport_id'] == ARGS.airport
        ac = state['aircraft'][0]
        phase = state.get('ils', {}).get('phase')
        if not phases or phases[-1] != phase:
            phases.append(phase)
            print('ILS', json.dumps(state.get('ils')), flush=True)
        if phase == 'handoff_ready' or (profile.exercise.get('tower_handover') and phase == 'glideslope'):
            break
        assert phase != 'missed', state
        time.sleep(1)
    else:
        raise AssertionError(state)
    post('/api/sim/pause')
    post('/api/sim/speed', json={'value': 1})
    results.append({'observed_aircraft': ac, 'ils': state['ils'], 'phases': phases,
                    'sim_errors': state['command_errors']})
    if not profile.exercise.get('tower_handover'):
        assert state['paused'] and state['ils']['stable_s'] >= 10
    assert not state['command_errors']
    whole, fraction = profile.tower['frequency_mhz'].split('.')
    transmission('tower-handoff',
        'Air France one two three, contact tower ' + num_words(whole) + ' decimal ' + num_words(fraction) + '.',
        dict(callsign='AFR123',action='CONTACT_TOWER',frequency=profile.tower['frequency_mhz'],station='tower'))
    final = requests.get(BASE + '/api/state', timeout=5).json()
    assert final['ils']['phase']=='complete' and final['paused'], final
    results.append({'final_ils':final['ils']})
    (OUT / 'result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('PASS: live STT, command interpretation, TTS and full clearance / tracking / tower handoff sequence.', flush=True)
    post('/api/demo/reset')


if __name__ == '__main__':
    try:
        main()
    finally:
        post('/api/sim/pause')
        post('/api/sim/speed', json={'value': 1})
