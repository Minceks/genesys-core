from types import SimpleNamespace
from unittest.mock import Mock

from agent.ai_provider import OpenAIProvider
from agent.verification_schema import PLAN_SCHEMA, executable_plan


def test_every_named_target_rejects_whitespace_and_control_characters():
    import re
    from agent.verification_schema import TARGET, VISIBILITY_TARGET, DESTINATION_TARGET
    for schema in (TARGET, VISIBILITY_TARGET, DESTINATION_TARGET):
        for branch in schema['anyOf']:
            name = branch['properties']['name']
            if name.get('enum') == ['']:
                continue  # The explicit unnamed-role branch is intentional.
            assert name['minLength'] == 1
            for invalid in ('', ' ', '\t', '\n', '\r\n', '\u00a0', '\u2003', '\x01', 'Ready\x01'):
                assert not re.fullmatch(name['pattern'], invalid), repr(invalid)
            for valid in ('Play', 'Game canvas', ' Wave 1 ', 'Resume\nlevel', '\u0100trums'):
                assert re.fullmatch(name['pattern'], valid), repr(valid)


def test_final_assertion_is_required_and_executable():
    check = PLAN_SCHEMA['properties']['checks']['items']
    assert 'finalAssertion' in check['required']
    assert all('click' not in variant['properties']['action']['enum']
               for variant in check['properties']['finalAssertion']['anyOf'])
    plan = executable_plan({'checks': [{'steps': [], 'finalAssertion': {
        'action': 'visible', 'target': {'by': 'text', 'name': 'Saved', 'role': None,
                                       'withinRole': None, 'withinText': None, 'exact': True}}}]})
    assert plan['checks'][0]['steps'] == [{'action': 'visible', 'target': {
        'by': 'text', 'name': 'Saved', 'exact': True}}]


def test_openai_planner_requests_strict_schema(monkeypatch):
    monkeypatch.setattr('agent.ai_provider.bounded_messages', lambda messages, _: messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage', lambda _: None)
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='{}', tool_calls=[]))]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider = OpenAIProvider(client=client)
    provider.generate_structured([{'role': 'system', 'content': 'Return JSON only.'}], PLAN_SCHEMA)
    format = create.call_args.kwargs['response_format']
    assert format['type'] == 'json_schema'
    assert format['json_schema']['strict'] is True
    assert format['json_schema']['schema'] == PLAN_SCHEMA
