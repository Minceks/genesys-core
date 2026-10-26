import json
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions


def test_verification_only_retry_repairs_coverage_then_selector_and_executes(tmp_path):
    requirements = [{'id': 'R1', 'name': 'Ready'}, {'id': 'R8', 'name': 'Feedback'}]
    first = {'name': 'Ready', 'covers': ['R1'], 'steps': [
        {'action': 'visible', 'target': {'by': 'text', 'name': 'Ready'}}]}
    feedback = {'name': 'Feedback', 'covers': ['R8'], 'independent': True, 'steps': [
        {'action': 'visible', 'target': {'by': 'text', 'name': ''}}]}
    plans = [dict(requirements=requirements, checks=[first]),
             dict(requirements=[requirements[1]], checks=[feedback]),
             dict(requirements=requirements, checks=[first, dict(feedback, steps=[
                 {'action': 'visible', 'target': {'by': 'role', 'role': 'alert', 'name': ''}}])])]
    messages = []
    def generate(history, *_):
        messages.append(history)
        return SimpleNamespace(text=json.dumps(plans[len(messages)-1]))
    contract = {'requirements': [dict(item, scope='browser', acceptance=item['name']) for item in requirements]}
    (tmp_path/'index.html').write_text('<h1>Ready</h1><div role="alert">Feedback</div>')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            result = verify_functions(page, 'Show ready and feedback', SimpleNamespace(generate=generate),
                                      attempt=1, contract=contract)
            assert len(messages) == 3
            assert [r['id'] for r in json.loads(messages[1][1]['content'])['missingRequirements']] == ['R8']
            assert 'empty target name' in messages[2][0]['content']
            assert result['testedInteractions'] == ['Ready', 'Feedback']
            assert not result['unverifiedCore']
            assert not result['issues']
        finally:
            browser.close()
            server.shutdown()
            server.server_close()


def test_invalid_verification_only_retry_has_bounded_planner_budget():
    from tests.test_verification_plans import Page, Provider
    plan = {'requirements': [{'id': 'R8', 'name': 'Feedback'}], 'checks': [
        {'name': 'Feedback', 'covers': ['R8'], 'steps': [
            {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': ''}}]}]}
    page, provider = Page(), Provider(plan)
    result = verify_functions(page, 'Show feedback', provider, attempt=1)
    assert provider.calls == 3
    assert page.mutations == 0
    assert not result['testedInteractions']
    assert not result['issues']
    assert 'empty target name' in result['unverifiedCore'][0]


@pytest.mark.parametrize('name', ['', ' ', '\t', '\n', '\u00a0'])
def test_empty_name_error_identifies_workflow_and_step_without_mutating(name):
    from tests.test_verification_plans import Page, Provider
    plan = {'requirements': [{'id': 'R1', 'name': 'Start a game'}], 'checks': [
        {'name': 'Keyboard activation', 'covers': ['R1'], 'steps': [
            {'action': 'tab'},
            {'action': 'focused', 'target': {'by': 'role', 'role': 'button', 'name': name}},
            {'action': 'visible', 'target': {'by': 'text', 'name': 'Playing'}}]}]}
    page = Page()
    result = verify_functions(page, 'Start a game', Provider(plan), attempt=1)
    assert page.mutations == 0
    detail = result['unverifiedCore'][0]
    assert 'Keyboard activation, step 2, action=focused, by=role, role=button' in detail
    assert '_verifiedPlan' not in result


def test_unnamed_alert_executes_real_browser_assertion():
    plan = {'requirements': [{'id': 'feedback', 'name': 'Show feedback'}],
            'checks': [{'name': 'Feedback appears', 'covers': ['feedback'],
                        'steps': [{'action': 'visible', 'target': {'by': 'role', 'role': 'alert', 'name': ''}}]}]}
    provider = SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(plan)))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            # Use an HTTP origin so verification can snapshot localStorage.
            page.route('http://verification.test/**', lambda route: route.fulfill(
                body='<div role="alert">Invalid email address</div>', content_type='text/html'))
            page.goto('http://verification.test/')
            result = verify_functions(page, 'Show feedback', provider, attempt=1)
            assert result['testedInteractions'] == ['Feedback appears']
            assert not result['unverifiedCore']
            assert not result['issues']
            assert result['_verifiedPlan']['checks'][0]['name'] == 'Feedback appears'
        finally:
            browser.close()


@pytest.mark.parametrize('action', ['click', 'fill'])
def test_unnamed_action_target_stays_rejected(action):
    from tests.test_verification_plans import Page, Provider
    plan = {'requirements': [{'id': 'feedback', 'name': 'Show feedback'}],
            'checks': [{'name': 'Invalid mutation', 'covers': ['feedback'],
                        'steps': [{'action': action, 'target': {'by': 'role', 'role': 'alert', 'name': ''}},
                                  {'action': 'visible', 'target': {'by': 'text', 'name': 'Done'}}]}]}
    page = Page()
    result = verify_functions(page, 'Show feedback', Provider(plan), attempt=1)
    assert page.mutations == 0
    assert 'empty target name' in result['unverifiedCore'][0]


def test_field_label_resolves_after_dialog_opens():
    plan = {'requirements': [{'id': 'form', 'name': 'Edit form'}],
            'checks': [{'name': 'Open form and edit', 'covers': ['form'], 'steps': [
                {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Open'},
                 'unlessVisible': {'by': 'role', 'role': 'dialog', 'name': ''}},
                {'action': 'fill', 'target': {'by': 'field', 'name': 'Email address'}, 'value': 'buyer@example.com'},
                {'action': 'value', 'target': {'by': 'field', 'name': 'Email address'}, 'value': 'buyer@example.com'}]}]}
    provider = SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(plan)))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.route('http://verification.test/**', lambda route: route.fulfill(
                body='''<button onclick="document.querySelector('dialog').showModal()">Open</button>
                        <dialog><label>Email address<input name="email"></label></dialog>''',
                content_type='text/html'))
            page.goto('http://verification.test/')
            result = verify_functions(page, 'Edit form', provider, attempt=1)
            assert result['testedInteractions'] == ['Open form and edit']
            assert not result['unverifiedCore']
        finally:
            browser.close()


def test_visible_cart_satisfies_open_action_without_clicking_blocked_control():
    from agent.functional_verification import open_destination_visible
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('<aside role="dialog" aria-label="Cart">Cart contents</aside>')
            assert open_destination_visible(page, {'name': 'Open cart, 1 items'})
            assert not open_destination_visible(page, {'name': 'Close cart'})
            assert not open_destination_visible(page, {'name': 'Open checkout'})
            page.set_content('<aside role="dialog" aria-label="Cart" hidden>Cart contents</aside>')
            assert not open_destination_visible(page, {'name': 'Open cart, 1 items'})
        finally:
            browser.close()


def test_structural_item_title_is_resolved_as_contained_text_not_invented_accessible_name():
    from agent.functional_verification import target
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('''<ul><li><button>Entry Alpha</button><span>Updated today</span></li>
                <li><button>Entry Alpha extra</button></li></ul><h2>Entry Alpha</h2>''')
            spec = {'by':'role','role':'listitem','name':'Entry Alpha','exact':True}
            assert page.get_by_role('listitem', name='Entry Alpha', exact=True).count() == 0
            assert target(page, spec).count() == 1
            assert target(page, spec).get_by_role('button',name='Entry Alpha',exact=True).count() == 1
            page.set_content('<ul><li aria-label="Different record"><span>Entry Alpha</span></li></ul>')
            assert target(page, spec).count() == 0, 'Explicit accessible names must not be overridden'
        finally: browser.close()


def test_repeated_structural_items_keep_mutations_ambiguous():
    plan = {'requirements':[{'id':'R1','name':'Select a record'}], 'checks':[
        {'name':'Ambiguous selection','covers':['R1'],'steps':[
            {'action':'click','target':{'by':'role','role':'listitem','name':'Entry Alpha','exact':True}},
            {'action':'visible','target':{'by':'text','name':'Selected'}}]}]}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page=browser.new_page()
            page.route('http://verification.test/**', lambda route:route.fulfill(content_type='text/html',body='''
                <ul><li onclick="window.changed=true"><span>Entry Alpha</span></li>
                <li onclick="window.changed=true"><span>Entry Alpha</span></li></ul>'''))
            page.goto('http://verification.test/')
            result=verify_functions(page,'Select a record',SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps(plan))),attempt=1)
            assert not page.evaluate('Boolean(window.changed)')
            assert any('ambiguous' in item for item in result['unverifiedCore'])
        finally: browser.close()


def test_exact_labelled_panel_scope_resolves_without_global_fallback():
    from agent.functional_verification import target
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            spec = {'by':'role','role':'button','name':'Touch','withinText':'Input mode'}
            page.set_content('''<button onclick="window.wrong=true">Touch</button>
                <div aria-label="Input mode"><button onclick="window.correct=true">Touch</button></div>''')
            target(page, spec).click()
            assert page.evaluate('Boolean(window.correct)')
            assert not page.evaluate('Boolean(window.wrong)')
            for markup in (
                '<button>Touch</button>',
                '<div aria-label="Input mode"><button>Keyboard</button></div><button>Touch</button>',
                '<div aria-label="Input mode"><button>Touch</button><button>Touch</button></div>',
                '<div aria-label="Input mode"><button>Touch</button></div><div aria-label="Input mode"><button>Touch</button></div>',
                '<div aria-label="Input mode" hidden><button>Touch</button></div><button>Touch</button>',
            ):
                page.set_content(markup)
                with pytest.raises(ValueError, match='could not be uniquely identified'):
                    target(page, spec)
        finally:
            browser.close()


def test_exhausted_model_deadline_is_not_retried_as_invalid_json():
    from agent.progress import ModelDeadlineExceeded
    from tests.test_verification_plans import Page
    calls = []
    def generate(*_):
        calls.append(True)
        raise ModelDeadlineExceeded('The model request time budget ended')
    page = Page()
    result = verify_functions(page, 'Build a game', SimpleNamespace(generate=generate))
    assert len(calls) == 1 and page.mutations == 0
    assert 'time budget ended' in result['unverifiedCore'][0]
