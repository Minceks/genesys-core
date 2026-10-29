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
    assert PLANNING_POLICY_VERSION==7

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


def test_edit_contract_rejects_invented_labels_but_allows_requested_new_controls():
    import pytest
    from agent.build_spec import validate_edit_labels
    source={'src/App.jsx':'<button>Quit to menu</button><span>HP</span>'}
    spec={'requirements':[{'id':'R1','scope':'browser','acceptance':"Click 'Exit to Title' and toggle 'Save Progression'."}]}
    with pytest.raises(ValueError,match='invented control/label'):
        validate_edit_labels(spec,source,'Improve the UI')
    assert validate_edit_labels(spec,source,'Add Exit to Title and Save Progression controls')==spec
    spec['requirements'][0]['acceptance']="Click 'Quit to menu' and read 'HP'."
    assert validate_edit_labels(spec,source,'Improve the UI')==spec

def test_planner_reserves_time_for_browser_execution_and_restores_deadline():
    import json,time
    from types import SimpleNamespace
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    from agent.progress import model_deadline,model_request_scope
    plan={'requirements':[{'id':'R1','name':'Ready state'}],'checks':[{'name':'Ready state','covers':['R1'],'steps':[{'action':'visible','target':{'by':'text','name':'Ready','exact':True}}]}]}
    class Provider:
        def generate(self,*_):
            assert 0 < model_deadline.get()-time.monotonic() <= 90
            return SimpleNamespace(text=json.dumps(plan))
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='<p>Ready</p>'))
            page.goto('https://fixture.test/')
            outer=time.monotonic()+240
            with model_request_scope(outer):
                result=verify_functions(page,'Show Ready',Provider(),attempt=1)
                assert model_deadline.get()==outer
            assert result['coverage']['passedIds']==['R1']
        finally:browser.close()


def test_missing_style_target_is_a_selector_failure_even_if_named_in_source():
    failure={'step':{'action':'style','target':{'name':'Start run'}},'executedActions':2,'error':'element(s) not found','targetResolved':False}
    assert not diagnosable_failure(failure,{'src/App.jsx':'<button>Start run</button>'},'Start run')


def test_stale_contract_is_not_fed_back_as_authority_on_visual_retry():
    import hashlib,json
    from types import SimpleNamespace
    from agent.build_spec import prepare_build_spec
    prompt='Improve game UI'
    stale={'version':2,'planningPolicyVersion':4,'requestHash':hashlib.sha256(prompt.encode()).hexdigest(),'requirements':[{'id':'R1','name':'Invented save','scope':'browser','acceptance':"Toggle 'Save Progression'."}]}
    good={'pages':['Home'],'requirements':[{'id':'R1','name':'Quit','scope':'browser','acceptance':"Click 'Quit' and return home."}],'assetRules':[],'designIntent':'Readable game UI'}
    class Workspace:
        def read_file(self,path):return {'content':json.dumps(stale) if path=='.genesys-build-spec.json' else '<button>Quit</button>'}
        def write_file(self,*_):return {'status':'success'}
    class Provider:
        def generate(self,messages,*_):
            context=json.loads(messages[-1]['content'])
            assert context['previousSpecification']=={}
            assert context['implementationSources']['src/App.jsx']=='<button>Quit</button>'
            return SimpleNamespace(text=json.dumps(good))
    assert prepare_build_spec(Workspace(),prompt,{'buildIntent':'edit-product'},Provider())['planningPolicyVersion']==7
