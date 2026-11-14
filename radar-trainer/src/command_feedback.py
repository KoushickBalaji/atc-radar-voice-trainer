"""Trainer findings are evidence, not executable replacement instructions."""
import re

from command_interpreter import finding


def assess_instruction(text, result, snapshot):
    """Assess proposals against observed state without asking a model to repair them."""
    issues = list(result.get('feedback', []))
    if result.get('rejected'):
        return issues or [finding('interpretation_rejected', 'interpretation', message)
                          for message in result['rejected']]
    orders = result.get('orders', [])
    if not orders:
        return issues or [finding('no_instruction', 'interpretation',
            'No complete instruction was recognized. Check the transcript and transmit again.' if text else
            'No speech was transcribed. Check the microphone and transmit again.')]
    from simple_demo import spoken_callsigns
    spoken = spoken_callsigns(text, snapshot['aircraft'])
    if spoken != {orders[0].get('callsign')} or len({o['callsign'] for o in orders}) != 1:
        issues.append(finding('callsign_evidence', 'interpretation',
                              'Callsign unclear. Address one aircraft using its full callsign and transmit again.'))
    aircraft = {a['id']: a for a in snapshot['aircraft']}
    proposals = result.get('proposals', [])
    for index, order in enumerate(orders):
        ac = aircraft.get(order.get('callsign'))
        if ac is None:
            issues.append(finding('unknown_aircraft', 'interpretation',
                                  'The interpreted callsign is not on this radar. Check the transcript and transmit the full intended callsign.',
                                  evidence={'callsign': order.get('callsign')}))
            continue
        if order.get('action') != 'ALT' or ac.get('alt_ft') is None:
            continue
        source = proposals[index]['evidence'] if index < len(proposals) else text
        verbs = set(re.findall(r'\b(?:climb|descend)\b', source.lower()))
        current, target = ac['alt_ft'], order['value']
        spoken = next(iter(verbs)) if len(verbs) == 1 else None
        inconsistent = (spoken == 'descend' and target > current + 200 or
                        spoken == 'climb' and target < current - 200)
        if inconsistent:
            expected = 'climb' if target > current else 'descend'
            issues.append(finding('vertical_direction_conflict', 'instruction',
                f'The transcript says "{spoken}", but the interpreted target of {target:,.0f} feet is '
                f'{"above" if target > current else "below"} {order["callsign"]}\'s current altitude of {current:,.0f} feet. '
                f'If that target was intended, use "{expected}". Otherwise, correct the target or retransmit if the transcript is wrong. No command was sent.',
                evidence={'callsign': order['callsign'], 'spoken_verb': spoken,
                          'current_altitude_ft': current, 'target_altitude_ft': target,
                          'suggested_verb_if_target_intended': expected}))
    return issues


def policy_feedback(message, snapshot):
    """Adapt existing simulator/exercise checks into the new trainer contract.

    These checks remain authoritative. They can migrate to typed findings one at
    a time without changing the interpreter or introducing more prompt routers.
    """
    lower = message.lower()
    category, code = 'exercise', 'exercise_restriction'
    if 'long turn' in lower:
        category, code = 'capability', 'forced_turn_unsupported'
        message = ('The requested turn direction needs a turn that this simulator does not model; it chooses the shortest turn. '
                   'Your direction may be intentional. This is a simulator limitation, not automatically a phraseology error. No command was sent.')
    elif 'callsign' in lower or 'unclear' in lower:
        category, code = 'interpretation', 'unclear_instruction'
    elif 'unsupported' in lower or 'not supported' in lower or 'does not model' in lower:
        category, code = 'capability', 'unsupported_instruction'
    elif any(word in lower for word in ('frequency', 'runway', 'station')):
        code = 'procedure_parameter_mismatch'
        message += ' Check the active procedure and the transcript, then transmit the intended assignment.'
    elif any(word in lower for word in ('stage', 'establish', 'tracking', 'phase', 'not on your frequency')):
        code = 'procedure_state'
        message += ' Review the aircraft state before issuing this instruction again.'
    return finding(code, category, message, evidence={'simulation_time': snapshot.get('t')})


def attach_feedback(out, result, snapshot):
    feedback = list(result.get('feedback', []))
    messages = {item['message'] for item in feedback}
    for message in out.get('rejected', []):
        if message not in messages:
            feedback.append(policy_feedback(message, snapshot))
    out['feedback'] = feedback
    out['proposed_orders'] = result.get('proposed_orders', result.get('orders', []))
    out['proposals'] = result.get('proposals', [])
    out['execution_status'] = 'blocked' if out.get('rejected') else ('queued' if out.get('trafscript') else 'handled')
    # Backward-compatible clients also receive the improved explanation.
    out['rejected'] = [item['message'] for item in feedback if item['blocking']]
    return out
