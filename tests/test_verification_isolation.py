import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions


def test_failed_check_cannot_contaminate_independent_check_or_erase_failure():
    html = '''<button onclick="localStorage.setItem('item','created'); document.querySelector('aside').hidden=false">Open</button>
    <aside role="dialog" aria-label="Cart" hidden>Temporary cart</aside><p>Ready</p>'''
    plan = {'requirements': [{'id': 'first', 'name': 'First workflow'}, {'id': 'second', 'name': 'Second workflow'}],
            'checks': [
                {'name': 'Failed workflow', 'covers': ['first'], 'steps': [
                    {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Open'}},
                    {'action': 'visible', 'target': {'by': 'text', 'name': 'Missing outcome'}}]},
                {'name': 'Independent workflow', 'covers': ['second'], 'independent': True, 'steps': [
                    {'action': 'absent', 'target': {'by': 'role', 'role': 'dialog', 'name': 'Cart'}},
                    {'action': 'visible', 'target': {'by': 'text', 'name': 'Ready'}}]}]}

    class Provider:
        def generate(self, messages, tools):
            result = plan if messages[0]['content'].startswith('You are a browser verification planner.') else {
                'kind': 'verification_failure', 'evidence': 'Missing test outcome'}
            return SimpleNamespace(text=json.dumps(result))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = html.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.evaluate("localStorage.setItem('baseline', 'preserved'); sessionStorage.setItem('baseline', 'preserved')")
            result = verify_functions(page, 'Verify two workflows', Provider(), attempt=1)
            assert result['testedInteractions'] == ['Independent workflow']
            assert result['coverage']['passedIds'] == ['second']
            assert result['unverifiedCore']  # The original failure still blocks completion.
            assert '_verifiedPlan' not in result
            assert page.evaluate('localStorage.getItem("item")') is None
            assert page.evaluate('localStorage.getItem("baseline")') == 'preserved'
            assert page.evaluate('sessionStorage.getItem("baseline")') == 'preserved'
            assert not page.get_by_role('dialog', name='Cart').is_visible()
        finally:
            browser.close()
            server.shutdown()
