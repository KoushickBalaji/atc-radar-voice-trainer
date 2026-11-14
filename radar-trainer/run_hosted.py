"""Public-preview entry point. One gateway, two sessions by default (hard ceiling five)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))


def configure():
    from dotenv import dotenv_values
    values = dotenv_values(ROOT.parent / '.env')
    key = os.environ.get('OPENAI_API_KEY') or values.get('OPENAI_API_KEY')
    if not key:
        raise SystemExit('Set OPENAI_API_KEY in the host environment before starting.')
    for service, default in [('STT', 'gpt-transcribe'), ('LLM', 'gpt-4.1-mini'), ('TTS', 'gpt-4o-mini-tts')]:
        os.environ['ATC_' + service + '_URL'] = 'https://api.openai.com'
        os.environ['ATC_' + service + '_KEY'] = key
        os.environ.setdefault('ATC_' + service + '_MODEL', default)
    os.environ.setdefault('ATC_TTS_VOICES', 'alloy,echo,onyx')
    os.environ.setdefault('ATC_TTS_VHF', '0')
    os.environ.setdefault('ATC_TTS_FORMAT', 'wav')


if __name__ == '__main__':
    configure()
    import uvicorn
    uvicorn.run('session_gateway:app', host=os.environ.get('ATC_APP_HOST', '127.0.0.1'),
                port=int(os.environ.get('PORT', '8000')), workers=1, access_log=False,
                ws_ping_interval=20, ws_ping_timeout=20)
