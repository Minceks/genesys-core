"""Exercise serialized provider schemas, including the production enum regression."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.ai_provider import OpenAIProvider
from agent.structured_schema import StructuredSchemaError, schema_size, validate_schema_limits
from agent.verification_planning import contract_plan_schema
from agent.verification_schema import PLAN_SCHEMA, SCOPE, TARGET, VISIBILITY_TARGET, DESTINATION_TARGET, obj


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def resolve(root, pointer):
    assert pointer.startswith('#/'), 'No remote definitions are needed for the verifier'
    value = root
    for part in pointer[2:].split('/'):
        value = value[part.replace('~1', '/').replace('~0', '~')]
    return value


def expanded(value, root):
    if isinstance(value, dict):
        if '$ref' in value:
            return expanded(resolve(root, value['$ref']), root)
        return {key: expanded(child, root) for key, child in value.items() if key != '$defs'}
    if isinstance(value, list):
        return [expanded(child, root) for child in value]
    return value


def contract(count):
    return {'requirements': [{'id': 'general-'+str(i), 'name': 'Required outcome '+str(i),
                             'scope': 'browser', 'acceptance': 'Use the named control and verify its saved visible state.'}
                            for i in range(count)]}


def test_old_inline_layout_reproduces_production_rejection_but_refs_fit():
    old = expanded(PLAN_SCHEMA, PLAN_SCHEMA)
    # The API reported 1006 as it crossed the limit; the full tree has 1017.
    assert schema_size(old)['enumValues'] > 1000
    with pytest.raises(StructuredSchemaError, match='> 1000'):
        validate_schema_limits(old)
    compact = validate_schema_limits(json.loads(json.dumps(PLAN_SCHEMA)))
    assert compact['enumValues'] < 300
    assert compact['objectProperties'] < 500
    assert len(json.dumps(PLAN_SCHEMA)) < len(json.dumps(old)) / 2


@pytest.mark.parametrize('count', [0, 1, 4, 8, 12])
def test_base_and_all_supported_contract_sizes_remain_under_provider_limits(count):
    schema = json.loads(json.dumps(contract_plan_schema(contract(count))))
    assert validate_schema_limits(schema)['enumValues'] < 300  # Headroom for future actions.
    if count:
        assert set(schema['properties']['coverage']['required']) == {r['id'] for r in contract(count)['requirements']}
    for node in walk(schema):
        if '$ref' in node:
            assert isinstance(resolve(schema, node['$ref']), dict)
        if node.get('type') == 'object':
            assert node['additionalProperties'] is False
            assert set(node['required']) == set(node['properties'])


def test_shared_targets_preserve_scope_names_and_action_safety():
    assert PLAN_SCHEMA['$defs'] == {'scope': SCOPE, 'target': TARGET,
                                    'visibilityTarget': VISIBILITY_TARGET, 'destinationTarget': DESTINATION_TARGET}
    full = expanded(PLAN_SCHEMA, PLAN_SCHEMA)
    check = full['properties']['checks']['items']
    final_actions = {action for branch in check['properties']['finalAssertion']['anyOf'] for action in branch['properties']['action']['enum']}
    assert 'style' in final_actions
    assert not final_actions & {'click', 'fill', 'reload', 'emulateMedia', 'hold', 'pointer', 'key'}
    for branch in check['properties']['steps']['items']['anyOf']:
        props = branch['properties']
        actions = props['action']['enum']
        if 'target' not in props: continue
        targets = props['target']['anyOf']
        if not set(actions) <= {'visible', 'absent'}:
            assert all(target['properties']['name'].get('minLength') == 1 for target in targets)
        for target in targets:
            scope = target['properties']['withinRole']['anyOf'][0]
            assert scope == SCOPE
    assert check['properties']['steps']['maxItems'] == 23
    assert 'finalAssertion' in check['required']


def test_counts_serialized_copies_and_handles_property_names_like_schema_keywords():
    same = {'type': 'string', 'enum': ['A', 'B']}
    schema = obj({'one': same, 'two': same})
    assert schema_size(schema)['enumValues'] == 4
    assert schema_size(schema) == schema_size(json.loads(json.dumps(schema)))
    assert schema_size(obj({'properties': same, 'enum': same})) == {
        'enumValues': 4, 'objectProperties': 2, 'nameCharacters': len('propertiesenum')+4}


@pytest.mark.parametrize('size,allowed', [(999, True), (1000, True), (1001, False)])
def test_enum_limit_boundaries(size, allowed):
    schema = obj({'choice': {'type': 'string', 'enum': [str(i) for i in range(size)]}})
    if allowed: assert validate_schema_limits(schema)['enumValues'] == size
    else:
        with pytest.raises(StructuredSchemaError, match='enumValues'): validate_schema_limits(schema)


@pytest.mark.parametrize('schema,metric', [
    (obj({str(i): {'type': 'string'} for i in range(5001)}), 'objectProperties'),
    (obj({'choice': {'type': 'string', 'enum': ['x'*120001]}}), 'nameCharacters')])
def test_other_shared_size_limits_are_checked(schema, metric):
    with pytest.raises(StructuredSchemaError, match=metric): validate_schema_limits(schema)


def provider_with_mock(monkeypatch, create):
    monkeypatch.setattr('agent.ai_provider.bounded_messages', lambda messages, _: messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage', lambda _: None)
    return OpenAIProvider(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))


@pytest.mark.parametrize('count', [0, 1, 8, 12])
def test_actual_openai_adapter_serializes_only_compact_strict_schema(monkeypatch, count):
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='{}', tool_calls=[]))]))
    provider = provider_with_mock(monkeypatch, create)
    schema = contract_plan_schema(contract(count))
    provider.generate_structured([{'role': 'system', 'content': 'Return JSON.'}], schema)
    wire = json.loads(json.dumps(create.call_args.kwargs['response_format']))
    assert wire['type'] == 'json_schema' and wire['json_schema']['strict'] is True
    assert validate_schema_limits(wire['json_schema']['schema'])['enumValues'] < 300
    assert create.call_count == 1


def test_oversized_text_and_image_schemas_never_call_api_or_consume_budget(monkeypatch):
    create = Mock(side_effect=AssertionError('No API request permitted'))
    provider = provider_with_mock(monkeypatch, create)
    monkeypatch.setattr('agent.ai_provider.bounded_messages', lambda *_: pytest.fail('No context budget consumed'))
    monkeypatch.setattr('agent.model_context.reserve_model_budget', lambda *_: pytest.fail('No image budget consumed'))
    invalid = expanded(PLAN_SCHEMA, PLAN_SCHEMA)
    with pytest.raises(StructuredSchemaError): provider.generate_structured([], invalid)
    with pytest.raises(StructuredSchemaError): provider.review_images('Review', {}, [], invalid)
    assert create.call_count == 0


def test_configuration_error_is_not_retried_as_a_model_planning_error():
    from agent.functional_verification import verify_functions
    from tests.test_verification_plans import Page
    provider = SimpleNamespace(generate_structured=Mock(side_effect=StructuredSchemaError('Schema configuration exceeds limit')))
    page = Page()
    result = verify_functions(page, 'Build any application', provider, contract=contract(2))
    assert provider.generate_structured.call_count == 1
    assert page.mutations == 0 and not result['testedInteractions']
    assert result['unverifiedCore'] and '_verifiedPlan' not in result


def test_other_current_openai_response_schemas_fit_limits():
    from agent.build_spec import SPEC_SCHEMA
    from agent.visual_review import SCHEMA
    for schema in (SPEC_SCHEMA, SCHEMA):
        assert validate_schema_limits(schema)['enumValues'] < 1000
