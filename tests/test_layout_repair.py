import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.layout_repair import layout_evidence, layout_source_context
from agent.visual_quality import SNAPSHOT_SCRIPT, assess_visual_quality
from agent.functional_verification import verify_functions
from agent.verification_input import input_duration, perform_input


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser,tmp_path):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_):pass
        def end_headers(self):
            self.send_header('Cache-Control','no-store')
            super().end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    def load(html):
        (tmp_path/'index.html').write_text(html,encoding='utf-8')
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        return page
    yield page,load
    context.close();server.shutdown();server.server_close()


@pytest.mark.parametrize('family',['Booking','Portfolio','Analytics'])
def test_inline_parent_tracks_identified_and_fix_preserves_desktop(page,family):
    p,load=page
    html=f'''<style>body{{margin:0}}main{{width:calc(100% - 32px);margin:16px}}
        .main-copy{{min-width:220px}}aside{{max-width:100%;min-width:0}}
        button{{min-height:44px}}</style><main><h1>{family}</h1>
        <div style="display:grid;grid-template-columns:1fr 320px;gap:12px">
        <article class="main-copy"><p>Primary content remains readable</p></article>
        <aside class="side-panel"><p>Important supporting content</p><button>Continue</button></aside></div></main>'''
    load(html)
    snapshot=p.evaluate(SNAPSHOT_SCRIPT)
    result=assess_visual_quality([snapshot])
    assert result['status']=='error'
    ancestors=snapshot['overflowElements'][0]['ancestors']
    assert any(a['inlineGridColumns']=='1fr 320px' and a['display']=='grid' for a in ancestors)
    assert any('controlling ancestor' in s and '1fr 320px' in s for s in result['suggestions'])
    assert layout_evidence(result)['viewports'][0]['overflowElements'][0]['ancestors']
    # Fix the actual parent, keeping the desktop tracks rather than hiding overflow.
    fixed=html.replace('style="display:grid;grid-template-columns:1fr 320px;gap:12px"','class="detail-layout"')
    fixed+='<style>.detail-layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:12px}@media(max-width:720px){.detail-layout{grid-template-columns:minmax(0,1fr)}}</style>'
    load(fixed)
    assert assess_visual_quality([p.evaluate(SNAPSHOT_SCRIPT)])['status']=='success'
    assert p.get_by_text('Important supporting content').is_visible()
    p.set_viewport_size({'width':1280,'height':800})
    assert not p.evaluate(SNAPSHOT_SCRIPT)['overflow']
    assert p.locator('.detail-layout').evaluate('e=>getComputedStyle(e).gridTemplateColumns').endswith('320px')


def quality():
    return {'status':'error','issues':['Phone overflow'],'snapshots':[{'width':390,'overflow':True,
        'overflowElements':[{'tag':'ASIDE','class':'side-panel','ancestors':[
            {'tag':'DIV','class':'','display':'grid','inlineGridColumns':'1fr 320px'}]}]}]}


def test_large_component_gets_exact_targeted_excerpt_without_rewrite_authority():
    source='// Unrelated source stays preserved\n'*400
    source+="<div style={{display:'grid',gridTemplateColumns:'1fr 320px',gap:12}}>\n"
    source+='<aside className="side-panel">Supporting content</aside>\n</div>\n'
    source+='// Hidden tail must remain unchanged\n'*400
    source+='// UNSHOWN_FINAL_SOURCE\n'
    calls=[]
    def read(name):
        calls.append(name)
        return {'status':'success','content':source,'truncated':False}
    context=layout_source_context(SimpleNamespace(read_file=read),quality(),
        ['.env','../private.jsx','src/../../private.jsx','src/App.jsx',None])
    assert calls==['src/App.jsx']
    assert 'gridTemplateColumns' in context and '1fr 320px' in context
    assert '"startLine": 398' in context
    assert 'Use edit_file' in context and 'Never reconstruct' in context
    assert 'UNSHOWN_FINAL_SOURCE' not in context
    assert context.count('Hidden tail')<10
    assert len(context)<8000 and len(source)>20000


def test_missing_or_unavailable_source_never_invents_an_excerpt():
    assert not layout_source_context(SimpleNamespace(read_file=lambda _:None),quality(),['src/App.jsx'])
    def offline(_):raise RuntimeError('Offline workspace')
    assert not layout_source_context(SimpleNamespace(read_file=offline),quality(),['src/App.jsx'])
    assert not layout_source_context(SimpleNamespace(read_file=lambda _: {'status':'success','content':'unrelated'}),quality(),['src/App.jsx'])


def test_utility_class_parent_beyond_initial_read_budget_is_located():
    data=quality()
    data['snapshots'][0]['overflowElements'][0]['ancestors']=[{
        'tag':'DIV','class':'md:grid-cols-[1fr_320px]','display':'grid','inlineGridColumns':''}]
    source='// preserved unrelated source\n'*500+'<div className="md:grid-cols-[1fr_320px]">Current layout</div>\n'
    context=layout_source_context(SimpleNamespace(read_file=lambda _: {'status':'success','content':source}),data,['src/App.tsx'])
    assert 'Current layout' in context and 'md:grid-cols-[1fr_320px]' in context
    assert '"startLine": 498' in context


def test_keyboard_navigation_preserves_focus_and_document_escape_after_start_unmounts(page):
    p,load=page
    load('''<style>button:focus{outline:2px solid blue}</style><button id="start" onclick="start()">Start</button>
        <div id="view"></div><script>
        function start(){document.querySelector('#start').remove();document.querySelector('#view').innerHTML='<h2>Playing</h2>'}
        addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelector('#view').innerHTML='<h2>Paused</h2>'})
        </script>''')
    plan={'requirements':[{'id':'keys','name':'Keyboard start and pause'}], 'checks':[
        {'name':'Real keyboard journey','covers':['keys'],'steps':[
            {'action':'tab'}, {'action':'focused','target':{'by':'role','role':'button','name':'Start'}},
            {'action':'key','key':'Enter'}, {'action':'visible','target':{'by':'role','role':'heading','name':'Playing'}},
            {'action':'key','key':'Escape'}, {'action':'visible','target':{'by':'role','role':'heading','name':'Paused'}}]}]}
    provider=SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps(plan)))
    result=verify_functions(p,'Keyboard start and pause',provider,attempt=1)
    assert result['coverage']['passedIds']==['keys'] and not result['unverifiedCore'],result
    assert p.get_by_role('button',name='Start').count()==0


@pytest.mark.parametrize('key',['Control+w','Alt+F4','Meta+r','F5',{},None])
def test_page_keyboard_rejects_modifiers_and_shortcuts(key):
    with pytest.raises(ValueError,match='unsupported focused-page key'):
        input_duration({'action':'key','key':key})


def test_page_key_does_not_refocus_a_locator():
    events=[]
    page=SimpleNamespace(keyboard=SimpleNamespace(press=lambda key:events.append(key)))
    perform_input(page,None,{'action':'key','key':'Escape'})
    assert events==['Escape']


def test_actual_coordinator_supplies_measured_parent_excerpt_on_layout_repair(monkeypatch,tmp_path):
    from agent import orchestrator
    from agent.ai_provider import AIResponse,AIToolCall
    from unittest.mock import Mock
    class RepairReached(BaseException):pass
    source='// preserved source\n'*500+"<div style={{gridTemplateColumns:'1fr 320px'}}>content</div>\n"+'// tail\n'*500
    workspace=SimpleNamespace(prepare=lambda:None,
        read_file=lambda _: {'status':'success','content':source,'truncated':False},
        get_diff=lambda:{'status':'success','diff':'diff --git a/src/App.jsx b/src/App.jsx\n-old\n+new'},
        run_build=Mock(return_value={'status':'success','success':True,'exitCode':0,'output':'Compiled'}),
        start_preview=lambda:{'status':'success','url':'https://fixture.invalid'},create_checkpoint=Mock())
    calls=[]
    class Editor:
        model='fixture'
        def generate(self,messages,tools):
            calls.append(messages)
            if len(calls)==1:
                return AIResponse(tool_calls=[AIToolCall(id='edit',name='edit_file',arguments={'filename':'src/App.jsx','old_text':'old','new_text':'new'})])
            if len(calls)==2:return AIResponse(text='Ready for mandatory checks')
            context='\n'.join(str(m.get('content','')) for m in messages)
            assert 'MEASURED LAYOUT REPAIR' in context and 'gridTemplateColumns' in context
            assert 'PARTIAL CURRENT SOURCE' in context and 'Never reconstruct' in context
            raise RepairReached()
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'jobs.sqlite3'))
    monkeypatch.setattr(orchestrator,'settings',SimpleNamespace(provider_name='openai',agent_timeout_seconds=240))
    monkeypatch.setattr(orchestrator,'get_provider',lambda:Editor())
    monkeypatch.setattr(orchestrator,'get_workspace',lambda _:workspace)
    monkeypatch.setattr(orchestrator,'BrowserSession',lambda **_:SimpleNamespace())
    monkeypatch.setattr(orchestrator,'get_browser',lambda _:SimpleNamespace(stop=lambda:None,visual_quality=lambda **_:quality()))
    monkeypatch.setattr(orchestrator,'stop_browser',lambda _:None)
    monkeypatch.setattr('agent.builder_controls.get_controls',lambda _: {})
    monkeypatch.setattr('agent.version_history.operate',lambda *_,**__: {'status':'success'})
    monkeypatch.setattr('agent.product_design.prepare_design',lambda *_: {'productType':'app','subtype':'app','presentationContract':{'mode':'workflow-app'}})
    monkeypatch.setattr('agent.build_spec.prepare_build_spec',lambda *_: {'requirements':[{'id':'A','name':'Action','scope':'browser','acceptance':'Use action and check outcome'}]})
    monkeypatch.setattr(orchestrator,'_compact_messages',lambda messages:messages)
    monkeypatch.setattr(orchestrator,'scan_project',lambda *_,**__: {'status':'success','sourceFiles':['src/App.jsx']})
    monkeypatch.setattr(orchestrator,'build_project_context',lambda _: 'Existing source')
    monkeypatch.setattr(orchestrator,'target_project_files',lambda *_:['src/App.jsx'])
    monkeypatch.setattr(orchestrator,'_validate_change_plan',lambda *_:{'valid':True})
    monkeypatch.setattr(orchestrator,'_validate_diff',lambda *_:{'valid':True})
    def execute(name,*_,**__):
        return {'status':'success','files':['src/App.jsx']} if name=='list_files' else {'status':'success','hasRuntimeErrors':False}
    monkeypatch.setattr(orchestrator,'execute_tool',execute)
    with pytest.raises(RepairReached):
        orchestrator.run_agent('Repair application layout','00000000-0000-4000-8000-000000000001')
    workspace.run_build.assert_called_once()
    workspace.create_checkpoint.assert_not_called()
