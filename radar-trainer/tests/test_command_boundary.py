import builtins
import json
from types import SimpleNamespace

import pytest

import command_interpreter as interpreter
from command_feedback import assess_instruction
from command_fixtures import response


def parse(text, orders, unresolved=()):
    return interpreter.interpret(text, lambda *args, **kwargs: response(text, orders, unresolved))


def test_command_path_does_not_import_legacy_interpretation(monkeypatch):
    from ai_client import AIClient
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in {'atc_llm', 'kb_oaci', 'graph_secteur', '04_ner_extraction', '03_bluesky_connector'}
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    text = 'Air France one two three climb to eight thousand feet'
    order = dict(action='ALT', callsign='Air France one two three', value=8000)
    client = AIClient()
    calls = []
    def chat(messages, **kwargs):
        calls.append(messages)
        assert kwargs['response_format']['json_schema']['strict'] is True
        assert messages[1]['content'] == text
        assert 'Applicable ICAO' not in messages[0]['content']
        return response(text, [order])
    monkeypatch.setattr(client._llm, 'chat', chat)
    result = client.interpret(text)
    assert len(calls) == 1
    assert result['trafscript'] == ['ALT AFR123 8000']


@pytest.mark.parametrize('raw', ['[{"callsign":"AFR123","action":"HDG","value":090}]',
                                '```json\n{}\n```', '{}', 'null'])
def test_malformed_output_is_a_system_issue_not_repaired(raw):
    result = interpreter.interpret('AFR123 heading 090', lambda *a, **k: raw)
    assert not result['orders'] and not result['trafscript']
    assert result['feedback'][0]['category'] == 'system'


def test_out_of_range_proposal_is_retained_for_feedback():
    order = dict(action='HDG', callsign='AFR123', value=400)
    result = parse('AFR123 heading four zero zero', [order])
    assert result['proposed_orders'] == [order]
    assert not result['orders'] and not result['trafscript']
    assert '400' in result['feedback'][0]['message']


@pytest.mark.parametrize('value', [True, 180.5, '180'])
def test_numbers_are_not_coerced_or_rounded(value):
    result = parse('AFR123 heading 180', [dict(action='HDG', callsign='AFR123', value=value)])
    assert result['rejected'] and not result['orders']


def test_unresolved_alternative_blocks_whole_compound_instruction():
    text = 'AFR123 heading 090, or continue to the fix if unable'
    result = parse(text, [dict(action='HDG', callsign='AFR123', value=90)], ['or continue to the fix if unable'])
    assert result['proposed_orders'][0]['value'] == 90
    assert not result['orders'] and not result['trafscript']
    assert result['feedback'][0]['code'] == 'unresolved_meaning'


def test_conditions_are_preserved_without_becoming_immediate_commands():
    text = 'AFR123 after passing CCB climb 8000 feet'
    payload = json.loads(response(text, [dict(action='ALT', callsign='AFR123', value=8000)]))
    payload['proposals'][0].update(timing='other_condition', condition='after passing CCB')
    result = interpreter.interpret(text, lambda *a, **k: json.dumps(payload))
    assert result['proposals'][0]['condition'] == 'after passing CCB'
    assert not result['trafscript'] and result['feedback'][0]['category'] == 'capability'


def test_missed_approach_assignment_remains_a_deferred_procedure():
    text = 'AFR123 on missed approach climb to 8000 feet'
    order = dict(action='MISSED_INSTRUCTION', callsign='AFR123', axis='ALT', value=8000)
    result = parse(text, [order])
    assert result['orders'] == [order] and result['trafscript'] == []
    assert result['proposals'][0]['timing'] == 'on_missed_approach'


@pytest.mark.parametrize('text', ['AFR123 if unable climb 8000 feet', 'AFR123 do not climb 8000 feet',
                                'AFR123 after passing CCB climb 8000 feet'])
def test_model_cannot_flatten_negation_or_conditions_into_immediate_command(text):
    result = parse(text, [dict(action='ALT', callsign='AFR123', value=8000)])
    assert result['rejected'] and not result['orders'] and not result['trafscript']


def test_unquoted_evidence_blocks_execution():
    payload = response('AFR123 heading 090', [dict(action='HDG', callsign='AFR123', value=90)])
    result = interpreter.interpret('AFR124 heading 090', lambda *a, **k: payload)
    assert result['feedback'][0]['code'] == 'missing_evidence' and not result['orders']


@pytest.mark.parametrize('verb,current,target,suggestion', [('descend', 5000, 8000, 'climb'), ('climb', 8000, 5000, 'descend')])
def test_feedback_grounds_correction_in_state_without_assuming_intent(verb, current, target, suggestion):
    text = f'AFR123 {verb} to {target} feet'
    result = parse(text, [dict(action='ALT', callsign='AFR123', value=target)])
    issue, = assess_instruction(text, result, {'aircraft': [dict(id='AFR123', alt_ft=current)]})
    assert issue['code'] == 'vertical_direction_conflict'
    assert issue['evidence']['suggested_verb_if_target_intended'] == suggestion
    assert 'If that target was intended' in issue['message']
    assert result['orders'][0]['value'] == target


def setup_app(monkeypatch, *, altitude=5000, procedure=None):
    import atc_app as app
    from airport_profiles import get_profile
    queued = []
    monkeypatch.setattr(app, 'SIM', SimpleNamespace(
        airport=get_profile('VOCB'),
        snapshot=lambda: {'t': 42, 'aircraft': [dict(id='AFR123', alt_ft=altitude, hdg=240)]},
        enqueue=lambda *a, **k: queued.append(a), procedure_command=procedure))
    monkeypatch.setattr(app, 'EX', SimpleNamespace(active=False))
    monkeypatch.setattr(app.simple_demo, 'ENABLED', True)
    return app, queued


def test_feedback_reaches_exchange_without_executing_or_speaking_correction(monkeypatch):
    app, queued = setup_app(monkeypatch)
    events = []
    monkeypatch.setattr(app, 'emit', events.append)
    monkeypatch.setattr(app.AI, 'tts', lambda *a: pytest.fail('A coaching correction is not a pilot readback'))
    text = 'Air France one two three descend to 8000 feet'
    result = parse(text, [dict(action='ALT', callsign='AFR123', value=8000)])
    out = app._handle_instruction(text, result)
    assert not queued and out['orders'] == [] and out['readback_text'] == ''
    assert out['execution_status'] == 'blocked'
    assert out['proposed_orders'][0]['value'] == 8000
    assert events[-1]['feedback'] == out['feedback']
    assert events[-1]['addressed_callsigns'] == ['AFR123']


def test_invalid_member_prevents_partial_compound_execution(monkeypatch):
    app, queued = setup_app(monkeypatch)
    text = 'AFR123 heading 270 and descend to 8000 feet'
    result = parse(text, [dict(action='HDG', callsign='AFR123', value=270),
                          dict(action='ALT', callsign='AFR123', value=8000)])
    out = app.process_instruction(text, result)
    assert not queued and not out['orders'] and len(out['proposed_orders']) == 2


def test_procedure_state_rejection_is_visible_trainer_feedback(monkeypatch):
    calls = []
    def procedure(order):
        calls.append(order)
        return 'Establish stable ILS tracking before handing over to tower.'
    app, queued = setup_app(monkeypatch, procedure=procedure)
    text = 'AFR123 contact tower 118.150'
    order = dict(action='CONTACT_TOWER', callsign='AFR123', station='tower', frequency='118.150')
    out = app.process_instruction(text, parse(text, [order]))
    assert calls == [order] and not queued and not out['orders']
    assert out['feedback'][0]['code'] == 'procedure_state'
    assert 'Review the aircraft state' in out['feedback'][0]['message']


def test_long_turn_is_labelled_as_limitation_not_student_error(monkeypatch):
    app, queued = setup_app(monkeypatch)
    text = 'AFR123 turn left heading 270'
    out = app.process_instruction(text, parse(text, [dict(action='HDG', callsign='AFR123', value=270)]))
    assert not queued
    assert out['feedback'][0]['code'] == 'forced_turn_unsupported'
    assert 'not automatically a phraseology error' in out['feedback'][0]['message']
