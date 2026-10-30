import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions


@pytest.mark.parametrize('action,expected,passes', [
    ('newTabText', 'Cart (1)', True),
    ('newTabText', 'Cart (99)', False),
    ('newTabValue', 'Cart (1)', False),
])
def test_new_tab_checks_real_persisted_text_and_never_treats_button_as_input(tmp_path, action, expected, passes):
    (tmp_path / 'index.html').write_text('''<button aria-label="Add synthetic item"
      onclick="localStorage.setItem('count','1');location.reload()">Add</button>
      <button aria-label="Open cart" id="cart"></button><script>
      cart.textContent='Cart ('+(localStorage.getItem('count')||'0')+')';</script>''')

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    plan = {'requirements': [{'id': 'persist', 'name': 'Cart persists in a new tab'}],
            'checks': [{'name': 'Real new tab persistence', 'covers': ['persist'], 'steps': [
                {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Add synthetic item'}},
                {'action': action, 'target': {'by': 'role', 'role': 'button', 'name': 'Open cart'}, 'value': expected}]}],
            'unverified': [], 'unverifiedCore': []}

    class Provider:
        def generate(self, messages, tools):
            value = plan if messages[0]['content'].startswith('You are a browser verification planner.') else {
                'kind': 'verification_failure', 'evidence': 'Persistence assertion failed'}
            return SimpleNamespace(text=json.dumps(value))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                result = verify_functions(page, 'Verify local cart persistence', Provider(), attempt=1)
                assert ('persist' in result.get('coverage', {}).get('passedIds', [])) is passes
                assert len(context.pages) == 1  # Temporary tab closes on success and failure.
                assert page.evaluate('localStorage.getItem("count")') == ('1' if action == 'newTabText' else None)
                if not passes:
                    assert result.get('unverifiedCore') or result.get('unverified') or result.get('issues')
            finally:
                browser.close()
    finally:
        server.shutdown()
