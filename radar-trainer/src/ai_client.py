"""
Client IA unifie (contrat OpenAI-compatible) - Application d'entrainement ATC
=============================================================================
UN SEUL mode de fonctionnement : STT, LLM et TTS sont des services REST au
contrat OpenAI, configures par variables d'environnement (ou fichier .env a la
racine, voir .env.example) :

    ATC_STT_URL / ATC_STT_KEY / ATC_STT_MODEL   -> POST {url}/v1/audio/transcriptions
    ATC_LLM_URL / ATC_LLM_KEY / ATC_LLM_MODEL   -> POST {url}/v1/chat/completions
    ATC_TTS_URL / ATC_TTS_KEY / ATC_TTS_MODEL   -> POST {url}/v1/audio/speech
    ATC_TTS_VOICES  pool de voix (CSV) ; ATC_TTS_VHF degradation radio cote client

Changer de fournisseur (facade auto-hebergee server.py, OpenAI, Mistral API,
Groq, serveur TTS compatible...) = changer URL + cle + modele. Rien d'autre.

AUCUN repli silencieux : toute erreur de fournisseur leve ProviderError, que
l'application remonte visiblement (HTTP 502 + log UI). L'__init__ ne fait AUCUN
appel reseau (import instantane, testable sans reseau).

Command interpretation uses the English capability schema in command_interpreter.
The legacy scenario generator remains separate from the command boundary.
"""
import io
import os
import logging
from dataclasses import dataclass

import requests

try:                                   # .env optionnel ; os.environ reste prioritaire
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:                    # python-dotenv absent : config par env uniquement
    pass

import voices

_log = logging.getLogger("ai_client")


# --- erreurs typees --------------------------------------------------------
class ProviderError(RuntimeError):
    """Erreur d'un fournisseur IA (reseau, HTTP, reponse invalide). Toujours
    remontee a l'appelant - jamais de repli silencieux."""

    def __init__(self, provider, message, status=None):
        self.provider = provider
        self.status = status
        prefix = f"HTTP {status} - " if status else ""
        super().__init__(f"{provider.upper()} : {prefix}{message}")


class ProviderConfigError(ProviderError):
    """Configuration manquante (URL/modele) detectee A L'APPEL, pas a l'init."""


# --- configuration ----------------------------------------------------------
@dataclass(frozen=True)
class ProviderConfig:
    name: str      # "stt" | "llm" | "tts"
    url: str       # normalisee : sans "/" final ni suffixe "/v1"
    key: str       # "" -> pas d'en-tete Authorization
    model: str

    @classmethod
    def from_env(cls, name):
        prefix = f"ATC_{name.upper()}"
        url = os.environ.get(f"{prefix}_URL", "").strip().rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3].rstrip("/")
        return cls(name=name.lower(), url=url,
                   key=os.environ.get(f"{prefix}_KEY", "").strip(),
                   model=os.environ.get(f"{prefix}_MODEL", "").strip())


def _headers(cfg):
    return {"Authorization": f"Bearer {cfg.key}"} if cfg.key else {}


def _require_url(cfg):
    if not cfg.url:
        raise ProviderConfigError(
            cfg.name, f"ATC_{cfg.name.upper()}_URL non configuree (copiez .env.example en .env)")


def _http_detail(r):
    """Message d'erreur court et lisible depuis une reponse HTTP non-2xx.
    Robuste a un corps JSON non-objet (liste / chaine) : on ne suppose jamais
    .get() sur le corps (sinon AttributeError -> 500 brut au lieu d'un 502)."""
    try:
        j = r.json()
    except ValueError:
        return (r.text or "")[:200] or r.reason
    if isinstance(j, dict):
        err = j.get("error")
        if isinstance(err, dict):
            err = err.get("message")
        msg = err or j.get("detail")
        if msg:
            return str(msg)
    return (r.text or "")[:200] or r.reason


def ping(cfg):
    """Sante d'un fournisseur : GET {url}/v1/models. Booleen, jamais d'exception."""
    if not cfg.url:
        return False
    try:
        return bool(requests.get(f"{cfg.url}/v1/models", headers=_headers(cfg), timeout=3).ok)
    except Exception:
        return False


# --- clients ----------------------------------------------------------------
def radio_keywords(airport=None, aircraft=()):
    """Recognition vocabulary from live traffic, without clearance/answer data."""
    from atc_callsign import AIRLINE, PHON
    from readback import callsign_telephony
    import re

    terms = set(PHON)
    for ac in aircraft:
        callsign = ac.get('id')
        if not isinstance(callsign, str):
            continue
        callsign = callsign.strip().upper()
        if not re.fullmatch(r'[A-Z][A-Z0-9-]{1,11}', callsign):
            continue
        terms.add(callsign)
        terms.add(callsign_telephony(callsign))
        for telephony, code in AIRLINE.items():
            suffix = callsign[len(code):] if callsign.startswith(code) else ''
            if suffix and suffix[0].isdigit():
                terms.add(telephony)
                terms.add(telephony + ' ' + callsign_telephony(suffix))
    if airport:
        terms.add(airport.NAME)
        terms.update(getattr(airport.ats_routes, 'fixes', {}))
        terms.update(p['fix'] for p in airport.holds.values())
    return sorted(t for t in terms if re.fullmatch(r"[A-Za-z][A-Za-z0-9 '-]{0,127}", t))


class SttClient:
    def __init__(self, cfg):
        self.cfg = cfg

    def transcribe(self, wav_bytes, keywords=()):
        """wav 16 kHz mono -> texte. POST /v1/audio/transcriptions (multipart)."""
        _require_url(self.cfg)
        prompt = ("English air traffic control radio. Aircraft identifiers may use airline "
                  "telephony, phonetic letters and spoken digits. Preserve numbers, direction, "
                  "negation and repetitions as heard. Do not supply missing speech. "
                  "Vocabulary hints are possible spellings, not a required answer list. "
                  "An aircraft identifier may be absent from the hints. Never substitute "
                  "a listed identifier or change its digits to fit the hints.")
        data = {"model": self.cfg.model, "response_format": "json", "prompt": prompt}
        if self.cfg.model == 'gpt-transcribe':
            data['languages[]'] = 'en'
            if keywords:
                data['keywords[]'] = keywords
        elif keywords:
            # Compatible endpoints may only support an ordinary prompt.
            data['prompt'] += ' Possible spellings: ' + ', '.join(keywords) + '.'
        try:
            r = requests.post(f"{self.cfg.url}/v1/audio/transcriptions",
                              headers=_headers(self.cfg),
                              files={"file": ("utterance.wav", wav_bytes, "audio/wav")},
                              data=data,
                              timeout=60)
        except requests.RequestException as e:
            raise ProviderError("stt", f"{self.cfg.url} injoignable : {e}") from e
        if not r.ok:
            raise ProviderError("stt", _http_detail(r), r.status_code)
        try:
            j = r.json()
        except ValueError as e:
            raise ProviderError("stt", f"reponse non JSON : {r.text[:200]}") from e
        if not isinstance(j, dict):
            # un 200 au corps JSON non-objet (liste, chaine) leverait sinon
            # AttributeError -> 500 brut au lieu d'un 502 type
            raise ProviderError("stt", f"reponse JSON inattendue (objet requis) : {r.text[:200]}")
        return str(j.get("text", "")).strip()


class LlmClient:
    def __init__(self, cfg):
        self.cfg = cfg

    def chat(self, messages, temperature=0.0, max_tokens=512, timeout=90, response_format=None):
        """messages chat -> contenu texte de la 1re completion. POST /v1/chat/completions."""
        _require_url(self.cfg)
        payload = {"model": self.cfg.model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        if response_format is not None:
            payload['response_format'] = response_format
        try:
            r = requests.post(f"{self.cfg.url}/v1/chat/completions",
                              headers=_headers(self.cfg), json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise ProviderError("llm", f"{self.cfg.url} injoignable : {e}") from e
        if not r.ok:
            raise ProviderError("llm", _http_detail(r), r.status_code)
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ProviderError("llm", f"reponse chat.completion invalide : {r.text[:200]}") from e
        if content is None:
            # content:null (refus/tool-call) deviendrait la chaine 'None' puis
            # silencieusement zero ordre - on prefere une erreur visible
            raise ProviderError("llm", "reponse chat.completion sans contenu (content null)")
        return str(content)


class TtsClient:
    def __init__(self, cfg):
        self.cfg = cfg

    def speak(self, text, voice, response_format="wav"):
        """texte -> audio (bytes). POST /v1/audio/speech."""
        _require_url(self.cfg)
        payload = {"model": self.cfg.model, "input": text, "voice": voice,
                   "response_format": response_format}
        try:
            r = requests.post(f"{self.cfg.url}/v1/audio/speech",
                              headers=_headers(self.cfg), json=payload, timeout=120)
        except requests.RequestException as e:
            raise ProviderError("tts", f"{self.cfg.url} injoignable : {e}") from e
        if not r.ok:
            raise ProviderError("tts", _http_detail(r), r.status_code)
        if not r.content:
            raise ProviderError("tts", "reponse audio vide")
        if r.headers.get("content-type", "").lower().startswith("application/json"):
            # certains fournisseurs renvoient 200 + corps JSON d'erreur :
            # sans cette garde l'UI recevrait un 'audio' injouable sans message
            raise ProviderError("tts", f"reponse JSON au lieu d'audio : {_http_detail(r)}")
        return r.content


# --- degradation VHF cote client (provider-agnostique) -----------------------
def _apply_vhf(audio_bytes):
    """Applique la bande passante radio 300-3400 Hz a un WAV (bytes -> bytes).
    Contenu non-WAV (mp3...) : renvoye tel quel avec un avertissement - l'audio
    reste jouable, seule la coloration radio est perdue (ATC_TTS_FORMAT=wav requis)."""
    if audio_bytes[:4] != b"RIFF":
        _log.warning("TTS : contenu non WAV, degradation VHF ignoree "
                     "(mettre ATC_TTS_FORMAT=wav ou ATC_TTS_VHF=0)")
        return audio_bytes
    try:
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly
        from atc_audio import FS, preprocess_waveform
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != FS:
            data = resample_poly(data, FS, sr).astype(np.float32)
        data = preprocess_waveform(data, training=False)
        buf = io.BytesIO()
        sf.write(buf, data, FS, format="WAV")
        return buf.getvalue()
    except Exception:
        _log.exception("TTS : degradation VHF echouee, audio original conserve")
        return audio_bytes


# --- facade ------------------------------------------------------------------
class AIClient:
    """Facade unique de l'application. __init__ SANS appel reseau."""

    def __init__(self):
        self._stt = SttClient(ProviderConfig.from_env("stt"))
        self._llm = LlmClient(ProviderConfig.from_env("llm"))
        self._tts = TtsClient(ProviderConfig.from_env("tts"))
        self.tts_pool = voices.parse_pool(os.environ.get("ATC_TTS_VOICES"))
        self._tts_vhf = (os.environ.get("ATC_TTS_VHF", "1").strip().lower()
                         not in ("0", "false", "no", "off", ""))
        self._tts_format = os.environ.get("ATC_TTS_FORMAT", "wav").strip() or "wav"

    # --- sante ---------------------------------------------------------------
    def health(self):
        """{'stt': bool, 'llm': bool, 'tts': bool} - pings legers, sans exception."""
        return {"stt": ping(self._stt.cfg), "llm": ping(self._llm.cfg), "tts": ping(self._tts.cfg)}

    # --- STT -------------------------------------------------------------------
    def asr(self, wav_bytes, keywords=()):
        return self._stt.transcribe(wav_bytes, keywords)

    # Command interpretation has no dependency on the legacy RAG pipeline.
    def interpret(self, text):
        from command_interpreter import interpret
        return interpret(text, self._llm.chat)

    # --- generation de scenario --------------------------------------------------
    def scenario(self, description):
        """Description instructeur -> liste d'avions prets pour SIM.create_aircraft."""
        import atc_llm
        import atc_ai                        # _items_to_aircraft (bibliotheque pure)
        raw = self._llm.chat(atc_llm.build_scenario_messages(description),
                             max_tokens=768, timeout=120)
        items = atc_llm.clean_scenario_items(atc_llm.parse_orders(raw))
        return atc_ai._items_to_aircraft(items)

    # --- TTS -----------------------------------------------------------------------
    def tts(self, text, voice=None, *, clear=False):
        """Texte -> audio WAV (bytes). voice=None -> 1re voix du pool ; degradation
        VHF appliquee cote client si ATC_TTS_VHF=1 (independant du fournisseur)."""
        voice = voice or (self.tts_pool[0] if self.tts_pool else "default")
        audio = self._tts.speak(text, voice, response_format=self._tts_format)
        return _apply_vhf(audio) if self._tts_vhf and not clear else audio
