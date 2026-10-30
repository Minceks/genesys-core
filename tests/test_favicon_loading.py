import functools,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import pytest
from playwright.sync_api import sync_playwright
from agent.visual_quality import SNAPSHOT_SCRIPT,assess_visual_quality

@pytest.mark.parametrize('exists',[True,False])
def test_rendered_favicon_must_exist_not_just_have_a_link_tag(tmp_path,exists):
    (tmp_path/'index.html').write_text('<link rel="icon" href="/favicon.svg"><header><svg></svg></header><main><h1 style="font-size:48px">Original studio</h1><p>A useful introduction to this studio and its work.</p></main>')
    if exists:(tmp_path/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="navy"/></svg>')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
                snapshot=page.evaluate(SNAPSHOT_SCRIPT)
                assert snapshot['favicon'] and snapshot['faviconLoaded'] is exists
                result=assess_visual_quality([snapshot],public_website=True)
                assert any('configured favicon could not load' in issue for issue in result['issues']) is (not exists)
            finally:browser.close()
    finally:server.shutdown()
