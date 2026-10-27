import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions


def test_wrapped_textarea_keeps_a_stable_target_during_real_typing():
    plan = {'requirements': [{'id': 'contact', 'name': 'Write contact message'}], 'checks': [
        {'name': 'Type message', 'covers': ['contact'], 'steps': [
            {'action': 'type', 'target': {'by': 'label', 'name': 'Message'}, 'value': 'Test message'},
            {'action': 'value', 'target': {'by': 'label', 'name': 'Message'}, 'value': 'Test message'}]}]}
    provider = SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(plan)))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.route('http://verification.test/**', lambda route: route.fulfill(
                content_type='text/html', body='<label>Message<textarea oninput="this.textContent=this.value"></textarea></label>'))
            page.goto('http://verification.test/')
            result = verify_functions(page, 'Write contact message', provider, attempt=1)
            assert result['testedInteractions'] == ['Type message']
            assert not result['issues']
            assert not result['unverifiedCore']
        finally:
            browser.close()


@pytest.mark.parametrize('remount,action,passes', [(False, 'type', True), (True, 'type', False), (True, 'fill', True)])
def test_keyboard_check_detects_focus_loss_that_programmatic_fill_misses(tmp_path, remount, action, passes):
    handler = 'oninput="this.replaceWith(this.cloneNode(true))"' if remount else ''
    (tmp_path / 'index.html').write_text(f'<label>Full name<input {handler}></label>')

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    plan = {'requirements': [{'id': 'typing', 'name': 'Enter a full name'}],
        'checks': [{'name': 'Enter full name', 'covers': ['typing'], 'steps': [
            {'action': action, 'target': {'by': 'label', 'name': 'Full name'}, 'value': 'Synthetic Test'},
            {'action': 'value', 'target': {'by': 'label', 'name': 'Full name'}, 'value': 'Synthetic Test'}]}],
        'unverified': [], 'unverifiedCore': []}

    class Provider:
        def generate(self, messages, tools):
            value = plan if messages[0]['content'].startswith('You are a browser verification planner.') else {
                'kind': 'application_failure', 'evidence': 'The actual input was replaced during input, losing typing focus.'}
            return SimpleNamespace(text=json.dumps(value))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                result = verify_functions(page, 'Enter a full name', Provider(), attempt=1)
                assert ('typing' in result.get('coverage', {}).get('passedIds', [])) is passes
                if not passes:
                    assert result['issues']
            finally:
                browser.close()
    finally:
        server.shutdown()
