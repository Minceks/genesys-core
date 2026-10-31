from aiohttp.test_utils import TestClient, TestServer
from playwright.sync_api import sync_playwright
import asyncio
import gzip
import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('selection_bridge',Path(__file__).resolve().parents[1]/'preview_proxy/selection_bridge.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
inject=module.inject


def test_selection_bridge_preserves_headers_for_assets_and_injects_only_html():
    headers={'Content-Type':'text/html','Content-Length':'6','Content-Encoding':'gzip','ETag':'old'}
    page=inject(gzip.compress(b'<body>Hi</body>'),headers)
    assert page.startswith(b'<body>Hi<script data-genesys-selection>') and page.endswith(b'</body>')
    assert 'Content-Length' not in headers and 'Content-Encoding' not in headers
    assert inject(b'image',{'Content-Type':'image/png'})==b'image'


@pytest.mark.parametrize('body,encoding',[(b'\x1f\x8bbroken','gzip'),(gzip.compress(b'<body>Hi</body>')[:12],'gzip'),(b'compressed','br'),
                                          (gzip.compress(b' '*2_000_001),'gzip')])
def test_a_page_that_cannot_be_read_is_served_exactly_as_it_arrived(body,encoding):
    headers={'Content-Type':'text/html','Content-Encoding':encoding,'ETag':'old'}
    assert inject(body,headers)==body
    assert headers=={'Content-Type':'text/html','Content-Encoding':encoding,'ETag':'old'}


def test_compressed_saved_preview_reaches_the_browser_as_a_page(monkeypatch):
    spec=importlib.util.spec_from_file_location('preview_server',Path(__file__).resolve().parents[1]/'preview_proxy/server.py')
    proxy=importlib.util.module_from_spec(spec);spec.loader.exec_module(proxy)
    monkeypatch.setenv('GENESYS_PREVIEW_DOMAIN','previews.example.test')
    monkeypatch.setenv('GENESYS_PREVIEW_PROXY_KEY','k'*32)
    monkeypatch.setenv('GENESYS_PUBLISHED_BACKEND_URL','https://backend.example.test')
    monkeypatch.delenv('RAILWAY_ENVIRONMENT_ID',raising=False)
    requests=[]
    class Response:
        status=200
        @property
        def headers(self):return {'Content-Type':'text/html; charset=utf-8','Content-Encoding':'gzip','Last-Modified':'Sat, 31 Oct 2026 08:53:37 GMT'}
        async def __aenter__(self):return self
        async def __aexit__(self,*_):pass
        async def read(self):return gzip.compress(b'<!doctype html><html><body><main>Game</main></body></html>')
    class Backend:
        def request(self,method,url,**kw):
            requests.append(kw['headers']);return Response()
        async def close(self):pass
    async def run():
        client=TestClient(TestServer(proxy.create_app()))
        await client.start_server()
        await client.server.app['client'].close()
        client.server.app['client']=Backend()
        try:
            cached={'If-Modified-Since':'Sat, 31 Oct 2026 08:53:37 GMT','If-None-Match':'"old"'}
            response=await client.get('/',headers={'Host':'a'*32+'.previews.example.test','Accept':'text/html,*/*',**cached})
            page=await response.read()
            await client.get('/assets/app.js',headers={'Host':'a'*32+'.previews.example.test','Accept':'*/*',**cached})
            return response.status,response.headers,page
        finally:await client.close()
    status,headers,page=asyncio.run(run())
    assert status==200 and 'Content-Encoding' not in headers and 'Last-Modified' not in headers
    assert page.startswith(b'<!doctype html><html><body><main>Game</main><script data-genesys-selection>')
    assert requests[0]['Accept-Encoding']=='gzip'
    assert 'If-Modified-Since' not in requests[0] and 'If-None-Match' not in requests[0]
    assert 'If-Modified-Since' in requests[1] and 'If-None-Match' in requests[1]


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
