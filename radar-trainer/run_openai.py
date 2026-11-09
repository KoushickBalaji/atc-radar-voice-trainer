"""Local OpenAI demo. Reads the existing workspace key without copying it."""
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


def configure():
    values = dotenv_values(ROOT.parent / '.env')
    key = values.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not key:
        raise SystemExit('Set OPENAI_API_KEY in D:\\ATC\\.env first.')
    defaults = {'stt': values.get('OPENAI_TRANSCRIPTION_MODEL') or 'gpt-transcribe',
                'llm': 'gpt-4.1-mini', 'tts': 'gpt-4o-mini-tts'}
    for service, model in defaults.items():
        prefix = 'ATC_' + service.upper()
        # This launcher explicitly routes all paid calls to OpenAI only.
        os.environ[prefix + '_URL'] = 'https://api.openai.com'
        os.environ[prefix + '_KEY'] = key
        os.environ[prefix + '_MODEL'] = os.environ.get(prefix + '_MODEL', model)
    os.environ['ATC_TTS_VOICES'] = 'alloy,echo,onyx'
    os.environ['ATC_TTS_VHF'] = '0'
    os.environ['ATC_TTS_FORMAT'] = 'wav'
    os.environ['ATC_SIMPLE_DEMO'] = '1'
    os.environ['ATC_BLUESKY_WORKDIR'] = str(ROOT / 'bluesky')
    os.environ.setdefault('ATC_APP_PORT', '8000')
    os.environ.setdefault('ATC_APP_NOBROWSER', '1')
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'bluesky' / 'matplotlib'))
    sys.path.insert(0, str(ROOT / 'src'))


if __name__ == '__main__':
    configure()
    from atc_app import main
    main()
