from agent.observed_targets import diagnosable_failure

def test_hallucinated_target_cannot_authorize_application_repair():
    failed={'step':{'action':'visible','target':{'name':'Particles'}},'executedActions':2,'error':'not found','targetResolved':False}
    assert not diagnosable_failure(failed,{'src/App.jsx':'<canvas aria-label="Game canvas" />'},'Settings')
    failed['step']['target']['name']='Game canvas'
    assert diagnosable_failure(failed,{'src/App.jsx':'<canvas aria-label="Game canvas" />'},'Settings')
    failed['executedActions']=0
    assert not diagnosable_failure(failed,{},'Game canvas')

def test_capture_or_ambiguous_selector_cannot_authorize_application_repair():
    failed={'step':{'action':'rememberText','target':{'name':'HP'}},'executedActions':2,'error':'strict mode violation','targetResolved':True}
    assert not diagnosable_failure(failed,{},'HP')
    failed['step']['action']='visible'
    assert not diagnosable_failure(failed,{},'HP')

def test_exact_surface_method_correction_preserves_name_and_uniqueness():
    from playwright.sync_api import sync_playwright
    from agent.observed_targets import exact_label_target,surface_targets
    from agent.functional_verification import target
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.set_content('<canvas aria-label="Game canvas" tabindex="0"></canvas><div aria-label="Touch controls">Fire</div>')
            result=exact_label_target(page,{'by':'role','role':'textbox','name':'Game canvas'},'tabTo',target)
            assert result is not None and result[1]=={'by':'label','name':'Game canvas'}
            assert exact_label_target(page,{'by':'text','name':'Touch controls'},'visible',target)
            assert exact_label_target(page,{'by':'text','name':'Touch controls'},'click',target) is None
            assert exact_label_target(page,{'by':'role','role':'img','name':'on-screen joystick'},'visible',target) is None
            assert any(x['name']=='Game canvas' for x in surface_targets(page))
            page.set_content('<canvas aria-label="Game canvas"></canvas><canvas aria-label="Game canvas"></canvas>')
            assert exact_label_target(page,{'by':'text','name':'Game canvas'},'visible',target) is None
        finally:browser.close()

def test_spec_reads_nested_local_sources_without_escaping_src():
    from agent.build_spec import implementation_sources,PLANNING_POLICY_VERSION
    files={'src/App.jsx':"import PlayScene from './PlayScene'; import secret from '../../private';",'src/PlayScene.jsx':"import {step} from './engine';",'src/engine.js':'export const step=()=>42;'}
    class Workspace:
        def read_file(self,path):
            assert path.startswith('src/') and '..' not in path.split('/')
            return {'content':files.get(path,'')}
    assert implementation_sources(Workspace())==files
    assert PLANNING_POLICY_VERSION==4

def test_unobserved_selector_does_not_invoke_application_diagnosis():
    import json
    from types import SimpleNamespace
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    plan={'requirements':[{'id':'R1','name':'Start game'}],'checks':[{'name':'Start game','covers':['R1'],'steps':[
        {'action':'click','target':{'by':'role','role':'button','name':'Start'}},
        {'action':'visible','target':{'by':'text','name':'Invented controls'}}]}]}
    class Provider:
        def generate(self,messages,*_):
            assert not messages[0]['content'].startswith('Diagnose browser')
            return SimpleNamespace(text=json.dumps(plan))
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='<button>Start</button>'))
            page.goto('https://fixture.test/')
            result=verify_functions(page,'Start game',Provider(),attempt=1)
            assert result['issues']==[] and result['unverifiedCore']
            assert not result['coverage']['passedIds']
        finally:browser.close()
