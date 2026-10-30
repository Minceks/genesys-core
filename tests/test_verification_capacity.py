import pytest
from types import SimpleNamespace
from unittest.mock import Mock
import time
from agent.ai_provider import OpenAIProvider
from agent.progress import model_request_scope, model_deadline


def test_browser_planner_has_its_own_latency_profile_without_reducing_build_reasoning(monkeypatch):
    for name in ['GENESYS_VERIFICATION_REASONING_EFFORT','GENESYS_VERIFICATION_OUTPUT_TOKEN_LIMIT','GENESYS_REASONING_EFFORT']:
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))]))
    provider=OpenAIProvider(model='gpt-5-mini',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    provider.generate_structured([{'role':'system','content':'You are a browser verification planner. Return a compact plan.'}],schema)
    assert create.call_args.kwargs['model']=='gpt-5.4'
    assert create.call_args.kwargs['reasoning_effort']=='low'
    assert create.call_args.kwargs['max_completion_tokens']==8000
    provider.generate([{'role':'system','content':'DEFAULT BUILD STANDARD: Design a complete app.'}],[])
    assert create.call_args.kwargs['reasoning_effort']=='medium'
    assert create.call_args.kwargs['max_completion_tokens']==24000


def test_planner_retry_gets_a_larger_bounded_window_and_keeps_source_on_failure():
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    windows=[]
    class Provider:
        def generate(self,*_):
            windows.append(model_deadline.get()-time.monotonic())
            raise TimeoutError('Synthetic network timeout')
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='<button>Play</button>'));page.goto('https://fixture.test/')
            with model_request_scope(time.monotonic()+300):
                result=verify_functions(page,'Play game',Provider(),attempt=1)
            assert len(windows)==2
            assert 85<windows[0]<=90 and 115<windows[1]<=120
            assert not result['issues'] and result['unverifiedCore']
            assert page.get_by_role('button',name='Play').is_visible()
        finally:browser.close()


def test_independent_workflow_restores_original_hash_route_not_only_storage():
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    plan={'requirements':[{'id':'R1','name':'Enter play'},{'id':'R2','name':'Fresh title workflow'}], 'checks':[
        {'name':'Enter game','covers':['R1'],'steps':[{'action':'click','target':{'by':'role','role':'button','name':'Start'}},
            {'action':'visible','target':{'by':'text','name':'Playing','exact':True}},
            {'action':'back'}, {'action':'visible','target':{'by':'role','role':'button','name':'Start'}},
            {'action':'click','target':{'by':'role','role':'button','name':'Start'}},
            {'action':'visible','target':{'by':'text','name':'Playing','exact':True}}]},
        {'name':'Independent title','covers':['R2'],'independent':True,'steps':[
            {'action':'visible','target':{'by':'role','role':'button','name':'Start'}}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='''<div id="app"></div><script>
              function render(){app.innerHTML=location.hash==='#play'?'Playing':'<button onclick="location.hash=String.fromCharCode(112,108,97,121)">Start</button>'}
              window.addEventListener('hashchange',render);render();</script>'''));page.goto('https://fixture.test/')
            result=verify_functions(page,'Start game and check title',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=plan)
            assert result['coverage']['passedIds']==['R1','R2'] and not result['unverifiedCore'],result
        finally:browser.close()


def test_native_preference_is_asserted_after_reload_not_inferred_from_visibility():
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    plan={'requirements':[{'id':'R1','name':'Remember sound preference'}],'checks':[{'name':'Save sound','covers':['R1'],'steps':[
        {'action':'click','target':{'by':'role','role':'checkbox','name':'Sound'}},
        {'action':'checked','target':{'by':'role','role':'checkbox','name':'Sound'}},
        {'action':'reload'},
        {'action':'checked','target':{'by':'role','role':'checkbox','name':'Sound'}}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='''<input type="checkbox" aria-label="Sound" onclick="localStorage.setItem('sound',this.checked)"><script>document.querySelector('input').checked=localStorage.getItem('sound')==='true'</script>'''));page.goto('https://fixture.test/')
            result=verify_functions(page,'Remember sound preference',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=plan)
            assert result['coverage']['passedIds']==['R1'] and not result['issues'],result
        finally:browser.close()


@pytest.fixture(autouse=True)
def plain_design_responses(monkeypatch):
    # These fakes return whole responses. Streaming is covered in test_build_upgrades.py.
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '0')
