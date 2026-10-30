import json
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import pytest
from playwright.sync_api import sync_playwright
from agent.verification_schema import complete_text_captures, TARGET, VISIBILITY_TARGET
from agent.functional_verification import verify_functions


TARGET_SPEC = {'by':'role', 'role':'heading', 'name':'Record', 'exact':False}


def test_schema_disallows_unnamed_heading_and_mutation_targets():
    assert all(v['properties']['name'].get('minLength') == 1 for v in TARGET['anyOf'])
    anonymous = VISIBILITY_TARGET['anyOf'][-1]['properties']
    assert 'heading' not in anonymous['role']['enum']
    assert anonymous['name']['enum'] == ['']


def test_no_capture_is_invented_without_a_matching_prior_observation():
    check = {'independent':True, 'steps':[{'action':'reload'},
        {'action':'sameText','target':TARGET_SPEC,'key':'title'}]}
    assert complete_text_captures({'checks':[check]}) == {'checks':[check]}


def test_existing_cross_check_capture_is_not_overwritten():
    first = {'steps':[{'action':'rememberText','target':TARGET_SPEC,'key':'title'}]}
    second = {'steps':[{'action':'visible','target':TARGET_SPEC},
                       {'action':'sameText','target':TARGET_SPEC,'key':'title'}]}
    plan = {'checks':[first,second]}
    assert complete_text_captures(plan) == plan


@pytest.mark.parametrize('changes_after_reload', [False, True])
def test_recovered_capture_runs_and_detects_real_reload_regression(changes_after_reload):
    plan = {'requirements':[{'id':'R1','name':'Record survives reload'}], 'checks':[
        {'name':'Reload record', 'covers':['R1'], 'independent':True, 'steps':[
            {'action':'visible','target':TARGET_SPEC}, {'action':'reload'},
            {'action':'sameText','target':TARGET_SPEC,'key':'title'}]}]}
    provider = SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps(plan)))
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            if self.path == '/': requests.append(True)
            title='Beta' if changes_after_reload and len(requests)>1 else 'Alpha'
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
            self.wfile.write(('<h1>Record '+title+'</h1>').encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            result=verify_functions(page,'The record title must survive reload',provider,attempt=1)
            if changes_after_reload:
                assert not result['testedInteractions']
                assert result['issues'] or result['unverifiedCore']
            else:
                assert result['testedInteractions']==['Reload record'], result
                assert not result['issues'] and not result['unverifiedCore']
                steps=result['_verifiedPlan']['checks'][0]['steps']
                assert [s['action'] for s in steps]==['visible','rememberText','reload','sameText']
        finally:
            browser.close()
            server.shutdown();server.server_close()
