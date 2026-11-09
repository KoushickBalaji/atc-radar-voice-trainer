"""Verify two Coimbatore holding circuits in BlueSky; optionally test the live voice endpoint."""
import argparse
import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def verify_flight():
    import bluesky_runtime as bsk
    from airport_profiles import get_profile
    from ils_trainer import ILSTrainer

    os.environ.setdefault('ATC_BLUESKY_WORKDIR', str(ROOT / 'bluesky'))
    airport = get_profile('VOCB')
    trainer = ILSTrainer(airport)
    start = airport.aircraft()
    bsk.create(trainer.callsign, start['type'], start['lat'], start['lon'],
               start['hdg'], start['alt_ft'], start['spd_kt'])
    trainer.phase = 'going_around'
    trainer.repeat_after_missed = True
    previous = None
    released = False
    for _ in range(1800):
        dt = bsk.advance(2)
        ac = bsk.state()[0]
        ac['x'], ac['y'] = airport.to_nm(ac['lat'], ac['lon'])
        ac['trk'] = float(bsk.bs().traf.trk[0])
        for command in trainer.update(ac, dt):
            bsk.cmd(command)
        state = (trainer.phase, trainer.hold.phase if trainer.hold else trainer.missed.index)
        if state != previous:
            print(state, ac['alt_ft'], round(ac['trk']), flush=True)
            previous = state
        if trainer.hold and trainer.hold.circuits == 2:
            assert abs(ac['alt_ft'] - 6300) <= 100 and abs(ac['trk'] - 44.92) < 10
            command = 'HDG AFR123 090'
            trainer.manual_command(command)
            bsk.cmd(command)
            released = True
        if released and trainer.phase == 'awaiting_clearance' and abs(ac['hdg']-90) < 1:
            return
    raise AssertionError((trainer.status, ac))


def verify_voice(base):
    import requests
    import soundfile as sf
    sys.path.insert(0, str(ROOT))
    from run_openai import configure
    configure()
    from ai_client import AIClient
    ai = AIClient()
    def post(path, **kwargs):
        response = requests.post(base + path, timeout=150, **kwargs)
        response.raise_for_status()
        return response.json()

    post('/api/demo/airport', json={'icao':'VOCB'})
    transmissions = [
        ('Air France one two three, on missed approach fly heading two seven zero.', 'MISSED_INSTRUCTION'),
        ('Air France one two three, cleared to Charlie Charlie Bravo, climb to six thousand three hundred feet, hold as published, expect further clearance at one two three zero.', 'HOLD_PUBLISHED'),
        ('Air France one two three, fly heading zero niner zero.', 'HDG'),
    ]
    try:
        for phrase, action in transmissions:
            samples, rate = sf.read(io.BytesIO(ai.tts(phrase,'alloy')))
            audio = io.BytesIO()
            sf.write(audio, samples, rate, format='WAV', subtype='PCM_16')
            result = post('/api/voice', files={'file':('test.wav', audio.getvalue(), 'audio/wav')})
            print(result['transcript'], result['orders'], result['rejected'], flush=True)
            assert result['orders'] and result['orders'][0]['action'] == action and result['audio_b64']
            time.sleep(.3)
            ils = requests.get(base+'/api/state', timeout=10).json()['ils']
            if action == 'HOLD_PUBLISHED':
                assert ils['holding']['expected'] == '1230' and ils['holding']['altitude_ft'] == 6300
            elif action == 'HDG':
                assert ils['phase'] == 'awaiting_clearance' and result['orders'][0]['value'] == 90
            else:
                assert ils['missed_approach']['overrides'] == {'HDG':270}
    finally:
        post('/api/demo/reset')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8001')
    parser.add_argument('--voice', action='store_true', help='Also test paid synthetic speech on the demo server')
    args = parser.parse_args()
    verify_flight()
    if args.voice:
        verify_voice(args.base)
