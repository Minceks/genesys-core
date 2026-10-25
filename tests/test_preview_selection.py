from playwright.sync_api import sync_playwright
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('selection_bridge',Path(__file__).resolve().parents[1]/'preview_proxy/selection_bridge.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
inject=module.inject


def test_selection_bridge_preserves_headers_for_assets_and_injects_only_html():
    headers={'Content-Type':'text/html','Content-Length':'6','Content-Encoding':'gzip','ETag':'old'}
    assert b'data-genesys-selection' in inject(b'<body>Hi</body>',headers)
    assert 'Content-Length' not in headers and 'Content-Encoding' not in headers
    assert inject(b'image',{'Content-Type':'image/png'})==b'image'


def test_real_cross_origin_selection_requires_editor_activation_and_suppresses_action():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context()
        child=inject(b'<body><button id="save" onclick="document.title=\'clicked\'">Save</button></body>',{'Content-Type':'text/html'})
        context.route('https://gene-sys.life/**',lambda route:route.fulfill(body='<iframe src="https://preview.test/"></iframe><script>window.selected=[];addEventListener("message",e=>selected.push(e.data))</script>',content_type='text/html'))
        context.route('https://preview.test/**',lambda route:route.fulfill(body=child,content_type='text/html'))
        page=context.new_page();page.goto('https://gene-sys.life/')
        frame=page.frames[1]
        frame.get_by_role('button',name='Save').click()
        assert frame.title()=='clicked'
        assert page.evaluate('selected.length')==0
        page.evaluate("document.querySelector('iframe').contentWindow.postMessage({type:'genesys-selection-mode',enabled:true,nonce:'test-nonce'},'https://preview.test')")
        page.wait_for_timeout(80)
        frame.evaluate("document.title='ready'")
        frame.get_by_role('button',name='Save').click()
        page.wait_for_timeout(80)
        selected=page.evaluate('selected')
        assert selected[0]['nonce']=='test-nonce'
        assert selected[0]['element']['id']=='save'
        assert frame.title()=='ready'
        browser.close()
