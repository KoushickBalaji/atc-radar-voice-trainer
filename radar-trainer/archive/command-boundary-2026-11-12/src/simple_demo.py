"""Bounded demonstration setup, not a real aerodrome procedure."""
import json
import os
import re
from pathlib import Path

ENABLED = os.environ.get('ATC_SIMPLE_DEMO') == '1'


def heading_instruction(text):
    """Parse a complete standard heading transmission without model inference.

    No aircraft list is used: preserve the spoken identifier, even if unknown.
    Other grammar continues through the existing interpreter and validators.
    """
    from atc_callsign import DIGI, normalize_callsign
    match = re.fullmatch(r'([a-z0-9 -]+?),?\s+(?:turn\s+(?:left|right)\s+)?heading\s+([a-z0-9 ]+)[.!]?',
                         text.strip(), re.I)
    if not match:
        return None
    callsign = normalize_callsign(match[1])
    if not re.fullmatch(r'[A-Z]{2,3}\d+[A-Z]{0,2}', callsign):
        return None
    words = match[2].lower().split()
    if len(words) == 1 and re.fullmatch(r'\d{1,3}', words[0]):
        value = int(words[0])
    elif len(words) == 3 and all(w in DIGI for w in words):
        value = int(''.join(DIGI[w] for w in words))
    else:
        return None
    if value > 360:
        return None
    order = dict(callsign=callsign, action='HDG', value=value)
    return dict(text=text, orders=[order], trafscript=[f'HDG {callsign} {value}'], rejected=[], cited=[])


def validate_audio(wav):
    import io
    import wave
    import numpy as np
    with wave.open(io.BytesIO(wav), 'rb') as audio:
        duration = audio.getnframes() / audio.getframerate()
        if not 0.15 <= duration <= 30 or audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError('Record a mono 16-bit transmission between 0.15 and 30 seconds.')
        pcm = audio.readframes(audio.getnframes())
        if len(pcm) != audio.getnframes() * 2:
            raise ValueError('Incomplete recording. Transmit again.')
    samples = np.frombuffer(pcm, dtype='<i2').astype(float) / 32768
    if np.sqrt(np.mean(samples ** 2)) < 0.001:
        raise ValueError('No audible speech. Check your microphone and transmit again.')


def readback(orders, text, altitudes):
    import readback as rb
    phrases = []
    for order in orders:
        phrase = rb.readback_for_order(order, altitudes.get(order['callsign']))
        if order['action'] == 'HDG':
            direction = re.search(r'\b(left|right)\b', text, re.I)
            if direction:
                phrase = 'turn ' + direction.group(1).lower() + ' ' + phrase
        if order['action'] == 'ALT' and not re.search(r'\bflight\s+level\b|\bFL\s*\d', text, re.I):
            value = int(order['value'])
            thousands, remainder = divmod(value, 1000)
            spoken = rb.num_words(thousands) + ' thousand' if thousands else ''
            if remainder:
                spoken += ' ' + rb.num_words(remainder // 100) + ' hundred'
            phrase = phrase.split(' flight level')[0] + ' ' + spoken.strip() + ' feet'
        phrases.append(phrase)
    return ', '.join(phrases) + ', ' + rb.callsign_telephony(orders[0]['callsign']) if orders else ''


def guidance():
    path = Path(__file__).resolve().parents[2] / 'data' / 'manual_excerpts.json'
    if not path.exists():
        return ''
    data = json.loads(path.read_text(encoding='utf-8'))
    return '\n'.join(e['paragraph_reference'] + ': ' + e['exact_text']
                     for e in data['excerpts'] if any(p in e['paragraph_reference']
                     for p in ('12.5.1', '12.14', '12.17.1.3', '12.16.1.1', '12.16.1.2')))


def spoken_callsigns(text, aircraft):
    from atc_callsign import DIGI, PHON, normalize_callsign
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    known = {a['id'] for a in aircraft}
    # Never accept a known flight as a prefix of a longer spoken identifier.
    return {normalize_callsign(' '.join(tokens[i:j])) for i in range(len(tokens))
            for j in range(i+1, min(i+12,len(tokens))+1)
            if j == len(tokens) or not (tokens[j] in DIGI or tokens[j] in PHON
                                        or tokens[j].isdigit())} & known


def validate(text, orders, aircraft, airport=None):
    """Do not silently drop unsupported meaning or force the wrong turn."""
    from approach_radio import ACTIONS
    if orders:
        spoken = spoken_callsigns(text, aircraft)
        if spoken != {orders[0].get('callsign')}:
            return 'Callsign unclear. Address one aircraft and transmit again.'
    if any(o.get('action') in ACTIONS for o in orders):
        if len(orders) != 1:
            return 'Issue approach clearance or tower handoff as a separate transmission.'
        action = orders[0]['action']
        from approach_radio import RADIO_ACTIONS
        if action in RADIO_ACTIONS:
            if re.search(r'\b(not|negative|cancel|correction|after|until|when|if|reaching|passing|established|then)\b', text, re.I):
                return 'Issue a standalone immediate radio request or instruction.'
            ac = next((a for a in aircraft if a['id'] == orders[0]['callsign']), None)
            if ac is None or ac.get('phase') in ('scheduled', 'complete', 'inbound'):
                return 'This aircraft is not on your frequency.'
            if action == 'RUNWAY_HEADING':
                from approach_radio import interpret
                parsed = interpret(text, lambda _: '[]')
                if parsed['orders'] != orders:
                    return 'Issue a standalone runway heading instruction.'
                if not airport:
                    return 'No active runway is configured.'
                return None
            # Acknowledgements must never hide a dropped clearance or unsupported action.
            if action == 'ACK':
                from atc_callsign import normalize_callsign
                pattern = {'standby':r'stand\s*by', 'radar_identified':r'radar\s+identified',
                           'continue_present_heading':r'continue\s+present\s+heading'}[orders[0]['kind']]
                remainder, count = re.subn(pattern, '', text, flags=re.I)
                if count != 1 or normalize_callsign(remainder.strip(' ,.!')) != orders[0]['callsign']:
                    return 'Unsupported or combined acknowledgement instruction.'
            if action == 'REPORT' and re.search(r'\b(climb|descend|turn|maintain|reduce|increase|contact)\b|\bcleared\s+(?:to|for)\b', text, re.I):
                return 'Separate data requests from flight instructions.'
            if action in ('SQUAWK', 'QNH', 'DIRECT'):
                blocked = r'\b(and|then|heading|climb|descend|speed|contact|runway|transition|report|say|confirm)\b'
                if re.search(blocked, text, re.I):
                    return 'Issue a standalone radio assignment.'
            return None
        if action in ('TAKEOFF','CONTACT_UNIT','CLEAR_LAND'):
            if len(orders) != 1 or re.search(r'\b(not|negative|cancel|correction|after|until|when|if|behind|and|then|line up|hold|climb|descend|maintain|squawk)\b', text, re.I):
                return 'Issue an unconditional standalone clearance.'
            if action == 'CLEAR_LAND' and not re.search(r'\bcleared to land\b', text, re.I):
                return 'An explicit landing clearance is required.'
            if action == 'TAKEOFF' and not re.search(r'\bcleared\s+for\s+take[ -]?off\b', text, re.I):
                return 'An explicit takeoff clearance is required.'
            if not any(a['id'] == orders[0]['callsign'] for a in aircraft):
                return 'Callsign is not on this radar.'
            return None
        conditional = orders[0]['action'] == 'MISSED_INSTRUCTION'
        from approach_radio import missed_context
        if conditional != missed_context(text):
            return 'Missed approach instruction unclear. No action taken.'
        blocked = r'\b(negative|not|cancel|correction|after|until|when|land|descend|left|right|speed|flight level|contact|hold|direct|then|and)\b' if conditional else r'\b(negative|cancel|correction|after|until|when|land|heading|climb|descend|speed)\b'
        if orders[0]['action'] == 'HOLD_PUBLISHED':
            blocked = r'\b(negative|not|cancel|correction|after|until|when|land|heading|speed|turn|left|right|flight level|radial|outbound|inbound|then)\b'
            if re.search(r'\b(expect|expected)\b', text, re.I) and orders[0]['expected'] is None:
                return 'Expected clearance time unclear.'
            if re.search(r'\b(maintain|climb|descend|feet)\b', text, re.I) and orders[0]['altitude_ft'] is None:
                return 'Holding altitude unclear.'
        if re.search(blocked, text, re.I):
            return 'Conditional or combined procedure instructions are not supported. No action taken.'
        if not any(a['id'] == orders[0].get('callsign') for a in aircraft):
            return 'Callsign is not on this radar. No aircraft was changed.'
        if not airport or not airport.approach:
            return 'No ILS approach sequence is modeled at this airport.'
        return None  # Runway/frequency and stage are checked atomically by the simulator.
    if re.search(r'\b(contact|tower|approach|land|hold|direct|squawk|correction|negative|cancel|after|until|when|by)\b', text, re.I):
        return 'This first exercise supports immediate heading, level and speed instructions only. No action taken.'
    if not orders:
        return 'Unclear instruction. No action taken; transmit again if you wish.'
    if len({o['callsign'] for o in orders}) != 1:
        return 'Address one aircraft per transmission. No action taken.'
    if len({o['action'] for o in orders}) != len(orders):
        return 'Conflicting or repeated instructions. No action taken.'
    for order in orders:
        ac = next((a for a in aircraft if a['id'] == order['callsign']), None)
        if ac is None:
            return 'Callsign is not on this radar. No aircraft was changed.'
        if ac.get('phase') in ('ready', 'rolling', 'complete', 'inbound'):
            return 'This aircraft is not available for airborne instructions.'
        if order['action'] not in ('HDG', 'ALT', 'SPD'):
            return 'Unsupported command in the first exercise. No action taken.'
        if order['action'] == 'SPD' and not 160 <= order['value'] <= 300:
            return 'This A320 exercise supports speeds from 160 to 300 knots. No action taken.'
        minimum = airport.exercise['command_alt_min_ft'] if airport else 3000
        if order['action'] == 'ALT' and not minimum <= order['value'] <= 18000:
            return f'This exercise supports levels from {minimum:,} to 18,000 feet. No action taken.'
        if order['action'] == 'HDG':
            delta = (order['value'] - ac['hdg'] + 180) % 360 - 180
            if (re.search(r'\bleft\b', text, re.I) and delta >= 0 or
                    re.search(r'\bright\b', text, re.I) and delta <= 0):
                return 'That requires a forced long turn, which this demo does not model. No action taken.'
    return None
