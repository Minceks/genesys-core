import json
from types import SimpleNamespace
import pytest
from agent.build_spec import prepare_build_spec, SPEC_SCHEMA


class Workspace:
    def __init__(self): self.saved = []
    def read_file(self, name): return {'content': '{}'}
    def write_file(self, name, content):
        self.saved.append(json.loads(content))
        return {'status': 'success'}


def valid():
    return {'pages': ['Home', 'Work'], 'requirements': [
        {'id': 'R1', 'name': 'Explore work', 'scope': 'browser',
         'acceptance': 'Open Work from Home, select a project, reload its detail and return to Home.'}],
        'assetRules': [], 'designIntent': 'Editorial work-led composition'}


def test_exact_logged_failure_sequence_recovers_before_any_spec_is_saved():
    visual = valid(); visual['requirements'][0]['scope'] = 'visual'
    missing_pages = valid(); missing_pages['pages'] = []
    responses = [visual, missing_pages, valid()]
    workspace = Workspace(); calls = []
    def generate(messages, tools):
        assert not workspace.saved
        calls.append(messages[:])
        return SimpleNamespace(text=json.dumps(responses[len(calls)-1]))
    result = prepare_build_spec(workspace, 'Improve my portfolio', {'buildIntent': 'edit-product'},
                                SimpleNamespace(generate=generate))
    assert len(calls) == 3
    assert result['pages'] == ['Home', 'Work']
    assert result['requirements'][0]['scope'] == 'browser'
    assert len(workspace.saved) == 1
    assert 'ALL constraints' in calls[-1][-1]['content']


def test_structured_provider_receives_schema_and_semantics_still_validate():
    calls = []
    def structured(messages, schema):
        calls.append(schema)
        return SimpleNamespace(text=json.dumps(valid()))
    result = prepare_build_spec(Workspace(), 'Build my portfolio', {}, SimpleNamespace(generate_structured=structured))
    assert calls == [SPEC_SCHEMA]
    assert SPEC_SCHEMA['properties']['pages']['minItems'] == 1
    assert result['requirements'][0]['scope'] == 'browser'


def test_invalid_plans_stop_after_three_calls_and_never_persist():
    workspace = Workspace(); calls = []
    def generate(*_):
        calls.append(True)
        spec = valid(); spec['requirements'][0]['scope'] = 'visual'
        return SimpleNamespace(text=json.dumps(spec))
    with pytest.raises(ValueError, match='browser requirement'):
        prepare_build_spec(workspace, 'Redesign my site', {}, SimpleNamespace(generate=generate))
    assert len(calls) == 3
    assert not workspace.saved
