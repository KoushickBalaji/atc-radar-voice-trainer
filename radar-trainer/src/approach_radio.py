"""Structured voice-only approach clearance and tower transfer commands.

Interpretation sees no selected runway/frequency, so it cannot repair to the answer.
State changes are validated again on the simulation thread before readback.
"""
import re
from decimal import Decimal, InvalidOperation

ACTIONS = {'TAKEOFF', 'CONTACT_UNIT', 'CLEAR_LAND', 'CLEAR_ILS', 'CONTACT_TOWER', 'MISSED_INSTRUCTION', 'HOLD_PUBLISHED'}
RADIO_ACTIONS = {'REPORT', 'SQUAWK', 'QNH', 'DIRECT', 'ACK', 'RUNWAY_HEADING'}
ACTIONS |= RADIO_ACTIONS


def missed_context(text):
    return bool(re.search(
        r'\b(?:on|for|in (?:case|(?:the )?event) of|if)\s+'
        r'(?:(?:the|a|you)\s+)?(?:missed approach|go[ -]?around|going around)\b',
        text, re.I))


def is_procedure_text(text):
    return bool(re.search(r'\b(hold|cleared|clearance|contact|tower|approach|ils|go[ -]?around|going around|report|say|confirm|squawk|qnh|direct|stand\s*by|identified|continue|runway)\b', text, re.I))


def interpret(text, chat):
    """Compatibility entry point; all command interpretation uses one schema."""
    from command_interpreter import interpret as interpret_command
    return interpret_command(text, chat)


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
    if order['action'] in ('CLEAR_ILS', 'CLEAR_LAND'):
        if order.get('runway') != airport.approach['runway']:
            return 'Runway does not match the selected ILS approach. No clearance accepted.'
        if order['action'] == 'CLEAR_LAND':
            return None if phase in ('localizer','glideslope','handoff_ready') else 'Establish the localizer before landing clearance.'
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
    if order['action'] in RADIO_ACTIONS:
        from readback import spell
        if order['action'] == 'RUNWAY_HEADING':
            return 'fly runway heading, ' + callsign_telephony(order['callsign'])
        if order['action'] == 'REPORT':
            return ''  # Reports are generated from simulator state, never from model output.
        if order['action'] in ('SQUAWK', 'QNH'):
            phrase = order['action'].lower() + ' ' + num_words(order['value'])
        elif order['action'] == 'DIRECT':
            phrase = 'proceed direct ' + spell(order['fix'])
        else:
            phrase = {'radar_identified':'roger', 'standby':'wilco',
                      'continue_present_heading':'continue present heading'}[order['kind']]
        return phrase + ', ' + callsign_telephony(order['callsign'])
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
    if order['action'] in ('CLEAR_ILS', 'TAKEOFF', 'CLEAR_LAND'):
        runway = order['runway']
        suffix = {'L':' left','R':' right','C':' centre'}.get(runway[-1], '')
        if order['action'] == 'CLEAR_LAND':
            return 'runway ' + num_words(runway[:2]) + suffix + ', cleared to land, ' + callsign_telephony(order['callsign'])
        phrase = ('runway ' + num_words(runway[:2]) + suffix + ', cleared for takeoff' if order['action'] == 'TAKEOFF'
                  else 'cleared ILS approach runway ' + num_words(runway[:2]) + suffix)
    else:
        whole, fraction = order['frequency'].split('.')
        phrase = 'contact ' + order['station'] + ' ' + num_words(whole) + ' decimal ' + num_words(fraction)
    return phrase + ', ' + callsign_telephony(order['callsign'])
