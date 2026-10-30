import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.functional_verification import contract_browser_checks, verify_functions


CONTRACT = {'requirements': [
    {'id': 'B1', 'name': 'Increment counter', 'scope': 'browser', 'acceptance': 'Click Increase and see Count 1'},
    {'id': 'V1', 'name': 'Hero art review', 'scope': 'visual', 'acceptance': 'Review subject accuracy'},
    {'id': 'E1', 'name': 'Real payment', 'scope': 'external', 'acceptance': 'Requires provider integration'},
]}


@pytest.mark.parametrize('expected,passes', [('25 25 50 50', True), ('0 0 100 100', False)])
def test_svg_geometry_assertion_proves_a_real_zoom_change(tmp_path, expected, passes):
    (tmp_path/'index.html').write_text('''<svg role="group" aria-label="Map" viewBox="0 0 100 100"></svg>
    <button onclick="document.querySelector('svg').setAttribute('viewBox','25 25 50 50')">Zoom in</button>''')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    contract={'requirements':[{'id':'zoom','name':'Zoom map','scope':'browser','acceptance':'Zoom in changes the actual map viewBox.'}]}
    class Provider:
        def generate(self,messages,*_):
            if messages[0]['content'].startswith('Diagnose browser'):
                return SimpleNamespace(text='{"kind":"verification_failure","evidence":"Expected geometry is incorrect."}')
            return SimpleNamespace(text=json.dumps({'requirements':[{'id':'zoom','name':'Zoom map'}], 'checks':[
                {'name':'Actual map zoom','covers':['zoom'],'steps':[
                    {'action':'click','target':{'by':'role','role':'button','name':'Zoom in'}},
                    {'action':'attribute','target':{'by':'role','role':'group','name':'Map'},'attribute':'viewBox','value':expected}]}], 'unverified':[], 'unverifiedCore':[]}))
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/')
                result=verify_functions(page,'Zoom the map',Provider(),attempt=1,contract=contract)
                assert ('zoom' in result['coverage']['passedIds']) is passes
                assert (not result['unverifiedCore']) is passes
                assert ('_verifiedPlan' in result) is passes
            finally: browser.close()
    finally: server.shutdown()


def test_contract_scopes_remove_only_known_nonbrowser_ids_without_mutating_input():
    checks = [{'covers': ['B1', 'V1']}, {'covers': ['V1']}, {'covers': ['UNKNOWN', 'E1']},
              {'covers': []}, {'covers': 'V1'}]
    assert contract_browser_checks(checks, CONTRACT) == [
        {'covers': ['B1']}, {'covers': ['UNKNOWN']}, {'covers': []}, {'covers': 'V1'}]
    assert checks[0]['covers'] == ['B1', 'V1']


@pytest.mark.parametrize('kind,passes', [('mixed', True), ('unknown', False), ('missing', False)])
def test_real_browser_contract_coverage_is_preserved(tmp_path, kind, passes):
    (tmp_path / 'index.html').write_text('''<button onclick="document.querySelector('p').textContent='Count 1'">Increase</button><p>Count 0</p>''')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    check = {'name': 'Counter interaction', 'covers': ['B1', 'V1'] + (['UNKNOWN'] if kind=='unknown' else []),
        'steps': [{'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Increase'}},
                  {'action': 'visible', 'target': {'by': 'text', 'name': 'Count 1'}}]}
    visual = {'name': 'Separate art review', 'covers': ['V1'], 'steps': [
        {'action': 'visible', 'target': {'by': 'text', 'name': 'Not a browser assertion'}}]}
    plan = {'requirements': [{'id': r['id'], 'name': r['name']} for r in CONTRACT['requirements']],
            'checks': ([check] if kind!='missing' else [])+[visual], 'unverified': [], 'unverifiedCore': []}
    class Provider:
        def generate(self, *_):
            return SimpleNamespace(text=json.dumps(plan))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                result = verify_functions(page, 'Increment a counter', Provider(), attempt=1, contract=CONTRACT)
                assert ('B1' in result.get('coverage', {}).get('passedIds', [])) is passes
                if passes:
                    assert result['coverage']['passedIds'] == ['B1']
                    assert result['testedInteractions'] == ['Counter interaction']
                    assert any('Hero art review' in item for item in result['unverified'])
                    assert any('Real payment' in item for item in result['unverified'])
                else:
                    assert page.get_by_text('Count 0').is_visible()  # Reject before mutations.
                    assert result['unverifiedCore']
            finally:
                browser.close()
    finally:
        server.shutdown()
