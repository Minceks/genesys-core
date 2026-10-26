"""Shared coverage recovery and native preference checks, without paid models."""
from copy import deepcopy
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.build_spec import PLANNING_POLICY_VERSION, prepare_build_spec
from agent.functional_verification import verify_functions
from agent.verification_environment import validate_media
from agent.verification_planning import contract_plan_schema, explicit_coverage, complete_missing_workflows


def requirement(identifier, name=None, scope='browser'):
    return {'id': identifier, 'name': name or identifier, 'scope': scope,
            'acceptance': 'Use the named control and confirm its resulting visible state, including reload when required.'}


def text(value):
    return {'by': 'text', 'name': value, 'exact': True}


def click(name):
    return {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': name, 'exact': True}}


def visible(value):
    return {'action': 'visible', 'target': text(value)}


def check(name, identifier, steps):
    return {'name': name, 'covers': [identifier], 'independent': True, 'steps': steps}


def plan(checks, requirements, coverage=None):
    result = {'checks': checks, 'requirements': [{'id': r['id'], 'name': r['name']} for r in requirements],
              'unverified': [], 'unverifiedCore': [], 'coreRequestEvidence': []}
    if coverage is not None:
        result['coverage'] = coverage
    return result


def claims(checks):
    return {key: {'checkNames': [c['name'] for c in checks if key in c['covers']], 'unverifiedReason': ''}
            for key in {key for c in checks for key in c['covers']}}


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(reduced_motion='no-preference', color_scheme='light')
    page = context.new_page()
    yield page
    context.close()
    for server in getattr(page, '_fixture_servers', []):
        server.shutdown()
        server.server_close()


def serve(page, html):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    page._fixture_servers = getattr(page, '_fixture_servers', []) + [server]
    page.goto(f'http://127.0.0.1:{server.server_port}/')


def test_schema_accounts_for_arbitrary_contract_ids_and_preserves_assertion_gate():
    contract = {'requirements': [requirement('booking:reload'), requirement('portfolio-dark'),
                                 requirement('appearance', scope='visual'), requirement('provider', scope='external')]}
    schema = contract_plan_schema(contract)
    coverage = schema['properties']['coverage']
    assert set(coverage['required']) == {'booking:reload', 'portfolio-dark'}
    assert coverage['additionalProperties'] is False
    assert 'coverage' in schema['required']
    assert 'finalAssertion' in schema['properties']['checks']['items']['required']
    assert contract_plan_schema({'requirements': [requirement(str(i)) for i in range(12)]})['properties']['checks']['maxItems'] == 12


@pytest.mark.parametrize('fault', ['missing', 'unknown', 'wrong-check', 'both'])
def test_bad_coverage_claims_rejected(fault):
    contract = {'requirements': [requirement('A')]}
    checks = [check('Working action', 'A', [visible('Ready')])]
    matrix = claims(checks)
    if fault == 'missing': matrix = {}
    if fault == 'unknown': matrix['unknown'] = matrix['A']
    if fault == 'wrong-check': matrix['A']['checkNames'] = ['Invented passing check']
    if fault == 'both': matrix['A']['unverifiedReason'] = 'Not observed'
    with pytest.raises(ValueError): explicit_coverage(plan(checks, contract['requirements'], matrix), contract)


def test_coverage_schema_prevents_planned_and_unverified_conflict():
    schema = contract_plan_schema({'requirements': [requirement('REDESIGN-BRX-03')]})
    planned, gap = schema['properties']['coverage']['properties']['REDESIGN-BRX-03']['anyOf']
    assert planned['properties']['checkNames']['minItems'] == 1
    assert planned['properties']['unverifiedReason']['enum'] == ['']
    assert gap['properties']['checkNames']['maxItems'] == 0
    assert set(planned['required']) == set(gap['required']) == {'checkNames', 'unverifiedReason'}
    assert planned['additionalProperties'] is gap['additionalProperties'] is False


def test_conflicting_coverage_retry_gets_exact_error_and_executes_corrected_plan(page):
    serve(page, '<button onclick="document.querySelector(\'p\').textContent=\'Done\'">Run</button><p>Ready</p>')
    reqs = [requirement('REDESIGN-BRX-03')]
    checks = [check('Real interaction', reqs[0]['id'], [click('Run'), visible('Done')])]
    class Provider:
        calls = 0
        def generate_structured(self, messages, schema):
            self.calls += 1
            matrix = claims(checks)
            if self.calls == 1:
                matrix[reqs[0]['id']]['unverifiedReason'] = 'Not observed'
            else:
                assert 'both planned and unverified: REDESIGN-BRX-03' in messages[0]['content']
                assert 'Correct this exact error.' in messages[0]['content']
            value = plan(deepcopy(checks), reqs, matrix)
            for workflow in value['checks']:
                workflow['finalAssertion'] = workflow['steps'].pop()
            return SimpleNamespace(text=json.dumps(value))
    provider = Provider()
    result = verify_functions(page, 'Build an app', provider, attempt=1, contract={'requirements': reqs})
    assert provider.calls == 2
    assert result['coverage']['passedIds'] == ['REDESIGN-BRX-03'], result
    assert result['unverifiedCore'] == []


@pytest.mark.parametrize('family,first,second', [
    ('store', 'Add item', 'Remove item'), ('booking', 'Choose slot', 'Cancel slot'),
    ('dashboard', 'Apply filter', 'Reset filter'), ('portfolio', 'Open work', 'Return home')])
def test_additive_recovery_runs_existing_and_missing_workflows(page, family, first, second):
    serve(page, f'''<button onclick="document.querySelector('p').textContent='First outcome'">{first}</button>
        <button onclick="document.querySelector('p').textContent='Second outcome'">{second}</button><p>Ready</p>''')
    reqs = [requirement(family+'-primary'), requirement(family+'-secondary')]
    original = check('Retained primary flow', reqs[0]['id'], [click(first), visible('First outcome')])
    added = check('Recovered secondary flow', reqs[1]['id'], [click(second), visible('Second outcome')])

    class Provider:
        calls = []
        def generate(self, messages, *_):
            self.calls.append(messages)
            if len(self.calls) == 1:
                return SimpleNamespace(text=json.dumps(plan([original], reqs)))
            assert 'FOCUSED COVERAGE RECOVERY' in messages[0]['content']
            evidence = json.loads(messages[-1]['content'])
            assert [r['id'] for r in evidence['missingRequirements']] == [reqs[1]['id']]
            assert evidence['existingCheckNames'] == [original['name']]
            return SimpleNamespace(text=json.dumps(plan([added], [reqs[1]], claims([added]))))

    provider = Provider()
    result = verify_functions(page, 'Create a '+family, provider, attempt=1, contract={'requirements': reqs})
    assert result['coverage']['passedIds'] == sorted([r['id'] for r in reqs]), result
    assert result['unverifiedCore'] == []
    assert result['_verifiedPlan']['checks'][0] == original
    assert result['testedInteractions'] == [original['name'], added['name']]
    assert len(provider.calls) == 2  # Original plan plus the missing flow; no wholesale re-plan.


def test_focused_recovery_cannot_replace_existing_workflows():
    reqs = [requirement('A'), requirement('B')]
    original = plan([check('Existing', 'A', [visible('Ready')])], reqs)
    baseline = deepcopy(original)
    class Provider:
        def generate(self, *_):
            return SimpleNamespace(text=json.dumps(plan([check('Replacement', 'A', [visible('Ready')])], reqs)))
    with pytest.raises(ValueError, match='missing IDs only'):
        complete_missing_workflows(original, {'B'}, {'requirements': reqs}, Provider(), {}, '')
    assert original == baseline


def test_structured_focused_recovery_uses_only_missing_schema_and_keeps_final_proof():
    reqs = [requirement('A'), requirement('B')]
    original = plan([check('Existing', 'A', [visible('Ready')])], reqs)
    addition = check('Missing outcome', 'B', [click('Run')])
    addition['finalAssertion'] = visible('Done')
    class Provider:
        def generate_structured(self, messages, schema):
            assert schema['properties']['coverage']['required'] == ['B']
            return SimpleNamespace(text=json.dumps(plan([addition], [reqs[1]], claims([addition]))))
    merged = complete_missing_workflows(original, {'B'}, {'requirements': reqs}, Provider(), {}, '')
    assert merged['checks'][0] == original['checks'][0]
    assert merged['checks'][1]['steps'] == [click('Run'), visible('Done')]
    assert set(merged['coverage']) == {'A', 'B'}


class StructuredProvider:
    def __init__(self, value):
        self.value, self.schemas = value, []
    def generate_structured(self, messages, schema):
        self.schemas.append(schema)
        return SimpleNamespace(text=json.dumps(self.value))
    def generate(self, *_):
        return SimpleNamespace(text='{"kind":"verification_failure","evidence":"No application defect established."}')


def test_explicit_automation_gap_remains_incomplete_while_other_checks_run(page):
    serve(page, '<button onclick="document.querySelector(\'p\').textContent=\'Done\'">Run</button><p>Ready</p>')
    reqs = [requirement('working'), requirement('canvas-feedback')]
    checks = [check('Real interaction', 'working', [click('Run'), visible('Done')])]
    matrix = {**claims(checks), 'canvas-feedback': {'checkNames': [], 'unverifiedReason': 'Pixel-level feedback cannot be observed with these DOM checks.'}}
    result = verify_functions(page, 'Build an app', StructuredProvider(plan(checks, reqs, matrix)), attempt=1, contract={'requirements': reqs})
    assert result['coverage']['passedIds'] == ['working']
    assert 'canvas-feedback' in result['coverage']['unverified'][0]
    assert any('Automation could not verify' in c for c in result['unverifiedCore'])
    assert '_verifiedPlan' not in result


def test_structured_response_without_matrix_rejects_before_any_click(page):
    serve(page, '<button onclick="document.querySelector(\'p\').textContent=\'Done\'">Run</button><p>Ready</p>')
    reqs = [requirement('working')]
    checks = [check('Real interaction', 'working', [click('Run'), visible('Done')])]
    provider = StructuredProvider(plan(checks, reqs))
    result = verify_functions(page, 'Build an app', provider, attempt=1, contract={'requirements': reqs})
    assert result['unverifiedCore'] and '_verifiedPlan' not in result
    assert page.get_by_text('Ready', exact=True).is_visible()
    assert all('coverage' in s['required'] for s in provider.schemas)


def style(property, value):
    return {'action': 'style', 'target': {'by': 'role', 'role': 'img', 'name': 'Decorative art'}, 'property': property, 'value': value}


@pytest.mark.parametrize('broken', [False, True])
def test_native_motion_and_color_preferences_reload_restore_and_real_feedback(page, broken):
    css = '' if broken else '@media(prefers-reduced-motion:reduce){[role=img]{animation:none}}'
    serve(page, '''<style>[role=img]{animation:spin 2s linear infinite;background-color:rgb(255,255,255)}
        @keyframes spin{to{transform:rotate(360deg)}}
        @media(prefers-color-scheme:dark){[role=img]{background-color:rgb(0,0,0)}}'''+css+'''</style>
        <div role="img" aria-label="Decorative art">Art</div>
        <button onclick="document.querySelector('p').textContent='Feedback received'">Act</button><p>Ready</p>''')
    reqs = [requirement('native-preferences'), requirement('independent-baseline')]
    checks = [check('Environment and feedback', reqs[0]['id'], [
        {'action': 'emulateMedia', 'reducedMotion': 'reduce', 'colorScheme': 'dark'},
        style('animation-name', 'none'), style('background-color', 'rgb(0, 0, 0)'),
        {'action': 'reload'}, style('animation-name', 'none'), click('Act'), visible('Feedback received')]),
        check('Independent original environment', reqs[1]['id'], [style('animation-name', 'spin'), style('background-color', 'rgb(255, 255, 255)')])]
    result = verify_functions(page, 'Build an app', StructuredProvider(plan(checks, reqs, claims(checks))), attempt=1, contract={'requirements': reqs})
    assert ('native-preferences' in result['coverage']['passedIds']) is not broken, result
    assert 'independent-baseline' in result['coverage']['passedIds'], result
    assert bool(result['unverifiedCore']) is broken
    assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches") is False
    assert page.evaluate("matchMedia('(prefers-color-scheme:dark)').matches") is False
    if broken: assert '_verifiedPlan' not in result


@pytest.mark.parametrize('invalid', [{}, {'reducedMotion': 'on'}, {'colorScheme': []}, {'reducedMotion': {}}])
def test_bad_media_settings_fail_with_validation_error(invalid):
    with pytest.raises(ValueError, match='Invalid verification plan'): validate_media(invalid)


@pytest.mark.parametrize('badstep', [
    {'action': 'emulateMedia', 'reducedMotion': 'reduce'},
    style('background-image', 'url(https://untrusted.test/)')])
def test_environment_change_alone_and_unsafe_style_never_prove_outcome(page, badstep):
    serve(page, '<p>Ready</p>')
    reqs = [requirement('preference')]
    provider = SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(plan([check('Invalid', 'preference', [badstep])], reqs))))
    result = verify_functions(page, 'Build an app', provider, attempt=1, contract={'requirements': reqs})
    assert result['unverifiedCore'] and '_verifiedPlan' not in result
    assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches") is False


def test_contract_browser_scope_cannot_be_dropped_based_on_its_name(page):
    serve(page, '<p>Ready</p>')
    reqs = [requirement('A', name='Visual design'), requirement('B')]
    checks = [check('Real A', 'A', [visible('Ready')]), check('Real B', 'B', [visible('Ready')])]
    result = verify_functions(page, 'Build an app', StructuredProvider(plan(checks, reqs, claims(checks))), attempt=1, contract={'requirements': reqs})
    assert result['coverage']['passedIds'] == ['A', 'B']


def test_explicit_automation_gap_does_not_repeat_successful_workflows(page):
    serve(page, '<button onclick="document.querySelector(\'p\').textContent=\'Done\'">Run</button><p>Ready</p>')
    reqs = [requirement('working'), requirement('full-game-completion')]
    checks = [check('Real interaction', 'working', [click('Run'), visible('Done')])]
    matrix = {**claims(checks), 'full-game-completion': {'checkNames': [], 'unverifiedReason': 'A full normal level completion was not exercised.'}}
    class Provider(StructuredProvider):
        diagnoses = 0
        def generate(self, *_):
            self.diagnoses += 1
            raise AssertionError('An explicit automation gap needs no application diagnosis')
    provider = Provider(plan(checks, reqs, matrix))
    result = verify_functions(page, 'Build an app', provider, contract={'requirements': reqs})
    assert len(provider.schemas) == 1 and provider.diagnoses == 0
    assert result['coverage']['passedIds'] == ['working']
    assert result['unverifiedCore'] and '_verifiedPlan' not in result
    assert 'verificationRecovery' not in result


def test_replanning_deadline_preserves_original_executed_evidence(page):
    from agent.progress import ModelDeadlineExceeded
    serve(page, '<p>Ready</p>')
    reqs = [requirement('working'), requirement('missing-control')]
    checks = [check('Working observation', 'working', [visible('Ready')]),
              check('Missing interaction', 'missing-control', [click('Missing button'), visible('Done')])]
    value = plan(checks, reqs, claims(checks))
    class Provider:
        calls = 0
        def generate_structured(self, *_):
            self.calls += 1
            if self.calls > 1:
                raise ModelDeadlineExceeded('The model request time budget ended')
            return SimpleNamespace(text=json.dumps(value))
    provider = Provider()
    result = verify_functions(page, 'Build an app', provider, contract={'requirements': reqs})
    assert provider.calls == 2
    assert result['testedInteractions'] == ['Working observation']
    assert result['coverage']['passedIds'] == ['working']
    assert 'missing-control' in {r['id'] for r in result['coverage']['requirements']}
    assert result['issues'] == []  # A timed-out replan cannot certify an app defect.
    assert any('Missing interaction' in s for s in result['executionIssues'])
    assert any('time budget ended' in s for s in result['unverifiedCore'])
    assert '_verifiedPlan' not in result


def test_limited_remaining_time_keeps_failure_incomplete_without_replanning(page):
    from agent.progress import model_request_scope
    serve(page, '<p>Ready</p>')
    reqs = [requirement('missing-control')]
    checks = [check('Missing interaction', 'missing-control', [click('Missing button'), visible('Done')])]
    provider = StructuredProvider(plan(checks, reqs, claims(checks)))
    with model_request_scope(time.monotonic() + 4):
        result = verify_functions(page, 'Build an app', provider, contract={'requirements': reqs})
    assert len(provider.schemas) == 1
    assert result['coverage']['passedIds'] == []
    assert result['issues'] == []
    assert any('before failure diagnosis' in s for s in result['unverifiedCore'])
    assert any('Missing interaction' in s for s in result['unverifiedCore'])
    assert '_verifiedPlan' not in result


def test_twelve_requirements_can_share_a_complete_workflow(page):
    serve(page, '<p>Ready</p>')
    reqs = [requirement(str(i)) for i in range(12)]
    checks = [dict(check('All observed outcomes', '0', [visible('Ready')]), covers=[r['id'] for r in reqs])]
    result = verify_functions(page, 'Build an app', StructuredProvider(plan(checks, reqs, claims(checks))), attempt=1, contract={'requirements': reqs})
    assert len(result['coverage']['passedIds']) == 12 and not result['unverifiedCore']


def test_expired_execution_budget_preserves_unverified_outcome_before_click(page):
    from agent.progress import model_request_scope
    serve(page, '<button onclick="document.querySelector(\'p\').textContent=\'Done\'">Run</button><p>Ready</p>')
    reqs = [requirement('working')]
    checks = [check('Real interaction', 'working', [click('Run'), visible('Done')])]
    with model_request_scope(time.monotonic()-1):
        result = verify_functions(page, 'Build an app', StructuredProvider(plan(checks, reqs, claims(checks))), attempt=1, contract={'requirements': reqs})
    assert result['coverage']['passedIds'] == []
    assert any('time budget expired' in c for c in result['unverifiedCore'])
    assert page.get_by_text('Ready', exact=True).is_visible()
    assert '_verifiedPlan' not in result


def test_legacy_policy_replanned_once_without_silent_contract_rewrite():
    prompt = 'Improve existing app'
    reqs = [requirement('system-preference')]
    class Workspace:
        saved = {'version': 2, 'requestHash': hashlib.sha256(prompt.encode()).hexdigest(), 'pages': ['App'], 'requirements': reqs}
        def read_file(self, name):
            return {'content': 'Working implementation' if name == 'src/App.jsx' else json.dumps(self.saved)}
        def write_file(self, name, content):
            self.saved = json.loads(content)
            return {'status': 'success'}
    class Provider:
        calls = 0
        def generate(self, messages, *_):
            self.calls += 1
            assert 'do NOT require a localStorage key' in messages[0]['content']
            assert json.loads(messages[-1]['content'])['previousSpecification']['requirements'] == reqs
            return SimpleNamespace(text=json.dumps({'pages': ['App'], 'requirements': reqs}))
    workspace, provider = Workspace(), Provider()
    result = prepare_build_spec(workspace, prompt, {}, provider)
    assert result['planningPolicyVersion'] == PLANNING_POLICY_VERSION
    assert result['requirements'] == reqs
    assert prepare_build_spec(workspace, prompt, {}, provider) == result
    assert provider.calls == 1
