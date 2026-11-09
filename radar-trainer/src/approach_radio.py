"""Structured voice-only approach clearance and tower transfer commands.

Interpretation sees no selected runway/frequency, so it cannot repair to the answer.
State changes are validated again on the simulation thread before readback.
"""
import json
import re
from decimal import Decimal, InvalidOperation

ACTIONS = {'TAKEOFF', 'CONTACT_UNIT', 'CLEAR_ILS', 'CONTACT_TOWER', 'MISSED_INSTRUCTION', 'HOLD_PUBLISHED'}


def missed_context(text):
    return bool(re.search(
        r'\b(?:on|for|in (?:case|(?:the )?event) of|if)\s+'
        r'(?:(?:the|a|you)\s+)?(?:missed approach|go[ -]?around|going around)\b',
        text, re.I))


def is_procedure_text(text):
    return bool(re.search(r'\b(hold|cleared|clearance|contact|tower|approach|ils|go[ -]?around|going around)\b', text, re.I))


def interpret(text, chat):
    prompt = '''Extract one immediate ATC instruction as a JSON array with exactly one object, or [] if unclear/unsupported.
Supported forms:
{"callsign":"ICAO callsign","action":"CLEAR_ILS","runway":"23"}
{"callsign":"ICAO callsign","action":"CONTACT_TOWER","frequency":"118.150","station":"Coimbatore Tower"}
{"callsign":"ICAO callsign","action":"MISSED_INSTRUCTION","axis":"HDG","value":270}
Preserve the callsign, runway suffix (L/R/C), station and every digit actually spoken.
Normalize airline telephony to ICAO callsign and spoken digits to numbers. Runway uses two digits plus optional L/R/C.
Frequency is a decimal MHz string, pad trailing zeroes to three places. Never guess a missing runway, frequency or callsign.
Station is the spoken station name, or "tower" if only tower was said. Do not infer an airport name.
For immediate approach instructions accept only explicit ILS clearance with runway or contact tower with frequency.
One further supported instruction explicitly assigns a heading (HDG, degrees) or climb altitude (ALT, feet) for a missed approach, such as "on missed approach fly heading two seven zero". It is reserved for the go-around. Reject explicit turn directions, flight levels, descents, additional conditions, or multiple targets in this form. Never interpret a request to go around as a clearance. Reject other conditional, negative, cancelled, corrected, ambiguous, mixed or multiple instructions, landing clearance, approach-controller transfers, and requests/reports rather than instructions.
Return only JSON, no markdown or explanation.'''
    prompt += '\nEquivalent scopes include "in case of a missed approach", "in the event of a missed approach", and "if you go around". The scope may precede or follow the assignment.'
    if re.search(r'\btake[ -]?off\b|\bcontact\b', text, re.I):
        prompt = '''Extract one unconditional immediate ATC clearance. Return a JSON array containing one order, or [] if unclear.
Takeoff requires the explicit words cleared for takeoff and a spoken runway. Use action TAKEOFF, callsign and runway.
A contact instruction requires a spoken station and frequency. Use action CONTACT_TOWER for tower or CONTACT_UNIT for other stations,
with callsign, station (spoken station only) and frequency (MHz string padded to three decimals).
Preserve the spoken callsign and every digit. Never infer missing fields. Reject conditions, corrections, negation,
requests, mixed or additional instructions. Use two runway digits and preserve any L/R/C suffix.'''
    if re.search(r'\bhold\b', text, re.I):
        prompt = '''Extract a published airborne holding clearance as a JSON array containing one object.
Use keys callsign (copy the spoken callsign verbatim including airline name and digits; never produce an airline code), action ("HOLD_PUBLISHED"),
fix (transmitted identifier, decode ICAO phonetic spelling), altitude_ft (integer feet or null),
expected (four UTC HHMM digits as a string or null). Never supply a missing value.
Proceeding or being cleared to the fix, a level assignment, holding as published, and expecting clearance
at a given time are all parts of ONE holding clearance. Return only the JSON array.
For example "Speedbird four, cleared to delta lima mike, climb to eight thousand feet, hold as published,
expect approach clearance at one four five zero" yields
[{"callsign":"Speedbird four","action":"HOLD_PUBLISHED","fix":"DLM","altitude_ft":8000,"expected":"1450"}].
Return [] for an unclear identifier, flight level, custom pattern, additional commands or a conditional hold.'''
    raw = chat([{'role':'system','content':prompt}, {'role':'user','content':text}])
    try:
        orders = json.loads(raw)
        assert isinstance(orders, list) and len(orders) == 1
        order = orders[0]
        assert isinstance(order, dict) and isinstance(order.get('callsign'), str)
        from atc_callsign import normalize_callsign
        order['callsign'] = normalize_callsign(order['callsign'])
        assert re.fullmatch(r'[A-Z0-9]{3,12}', order['callsign'])
        if order['action'] in ('CLEAR_ILS', 'TAKEOFF'):
            assert set(order) == {'callsign','action','runway'}
            assert re.fullmatch(r'(0[1-9]|[12][0-9]|3[0-6])[LRC]?', order['runway'])
        elif order['action'] == 'HOLD_PUBLISHED':
            assert set(order) == {'callsign','action','fix','altitude_ft','expected'}
            assert re.search(r'\bhold\b', text, re.I) and re.search(r'\bas published\b', text, re.I)
            assert re.fullmatch(r'[A-Z0-9]{2,8}', order['fix'])
            assert order['altitude_ft'] is None or type(order['altitude_ft']) is int
            assert order['expected'] is None or re.fullmatch(r'(?:[01]\d|2[0-3])[0-5]\d', order['expected'])
            if order['expected'] and re.search(r'\bexpect(?:ed)? approach clearance\b', text, re.I):
                order['expect_approach'] = True
            if order['altitude_ft'] is not None:
                verb = re.search(r'\b(climb|descend)\b', text, re.I)
                if verb:
                    order['level_verb'] = verb.group().lower()
        elif order['action'] == 'MISSED_INSTRUCTION':
            assert missed_context(text)
            assert set(order) == {'callsign','action','axis','value'}
            assert type(order['value']) is int
            assert order['axis'] in ('HDG','ALT')
            assert (0 <= order['value'] <= 360 if order['axis']=='HDG' else 0 < order['value'] <= 18000)
        else:
            assert order['action'] in ('CONTACT_TOWER', 'CONTACT_UNIT')
            assert set(order) == {'callsign','action','frequency','station'}
            assert isinstance(order['frequency'], str) and re.fullmatch(r'1[123]\d\.\d{3}', order['frequency'])
            assert isinstance(order['station'], str) and order['station'].strip()
            order['station'] = ' '.join(order['station'].lower().split())
    except (ValueError, TypeError, KeyError, AssertionError):
        return dict(orders=[], trafscript=[], rejected=['Unclear or unsupported approach instruction. No action taken.'])
    return dict(orders=orders, trafscript=[], rejected=[])


def validate(order, airport, phase, callsign=None):
    if not airport or not airport.approach:
        return 'No ILS approach sequence is modeled at this airport.'
    if order.get('callsign') != (callsign or airport.exercise['start']['callsign']):
        return 'Callsign is not on this radar. No aircraft was changed.'
    if order['action'] == 'HOLD_PUBLISHED':
        if phase not in ('awaiting_clearance','armed','localizer','glideslope','going_around','holding'):
            return 'Holding clearance unavailable at this stage.'
        return None
    if order['action'] == 'MISSED_INSTRUCTION':
        if phase in ('missed_finished','missed_fix_altitude'):
            return 'Missed approach exercise has ended.'
        if order['axis']=='ALT' and not airport.exercise['command_alt_min_ft'] <= order['value'] <= 18000:
            return 'Assigned altitude outside the exercise limits.'
        return None
    if order['action'] == 'CLEAR_ILS':
        if order.get('runway') != airport.approach['runway']:
            return 'Runway does not match the selected ILS approach. No clearance accepted.'
        if phase not in ('awaiting_clearance','armed','localizer','glideslope'):
            return 'Approach clearance is not available at this exercise stage.'
    else:
        tower = airport.tower
        if not tower:
            return 'No verified tower channel is configured for this airport.'
        try:
            if Decimal(str(order.get('frequency'))) != Decimal(tower['frequency_mhz']):
                return 'Frequency does not match the selected tower channel. No transfer made.'
        except InvalidOperation:
            return 'Unclear tower frequency. No transfer made.'
        station = ' '.join(str(order.get('station','')).lower().split()).replace('twr','tower')
        allowed = {'tower', tower['name'].lower().replace('twr','tower'), tower['name'].split('/')[0].lower().replace('twr','tower')}
        if station not in allowed:
            return 'Station does not match the selected tower. No transfer made.'
        if phase != 'handoff_ready' and not (phase == 'glideslope' and airport.exercise.get('tower_handover')):
            return 'Establish stable ILS tracking before handing over to tower.'
    return None


def readback(order):
    from readback import callsign_telephony, num_words
    if order['action'] == 'HOLD_PUBLISHED':
        from readback import spell
        phrase = 'proceed to ' + spell(order['fix'])
        if order['altitude_ft'] is not None:
            altitude = order['altitude_ft']
            thousands, remainder = divmod(altitude, 1000)
            words = ([num_words(thousands)+' thousand'] if thousands else [])
            if remainder:
                words.append(num_words(remainder//100)+' hundred' if remainder%100 == 0 else num_words(remainder))
            verb = order.get('level_verb')
            phrase += ', ' + (verb+' to ' if verb else 'maintain ') + ' '.join(words) + ' feet'
        phrase += ', hold as published'
        if order['expected']:
            kind = 'approach' if order.get('expect_approach') else 'further'
            phrase += ', expect ' + kind + ' clearance at ' + num_words(order['expected'])
        return phrase + ', ' + callsign_telephony(order['callsign'])
    if order['action'] == 'MISSED_INSTRUCTION':
        phrase = ('fly heading '+num_words(str(order['value']).zfill(3)) if order['axis']=='HDG'
                  else 'climb to '+num_words(str(order['value']))+' feet')
        return 'on missed approach, '+phrase+', '+callsign_telephony(order['callsign'])
    if order['action'] in ('CLEAR_ILS', 'TAKEOFF'):
        runway = order['runway']
        suffix = {'L':' left','R':' right','C':' centre'}.get(runway[-1], '')
        phrase = ('runway ' + num_words(runway[:2]) + suffix + ', cleared for takeoff' if order['action'] == 'TAKEOFF'
                  else 'cleared ILS approach runway ' + num_words(runway[:2]) + suffix)
    else:
        whole, fraction = order['frequency'].split('.')
        phrase = 'contact ' + order['station'] + ' ' + num_words(whole) + ' decimal ' + num_words(fraction)
    return phrase + ', ' + callsign_telephony(order['callsign'])
