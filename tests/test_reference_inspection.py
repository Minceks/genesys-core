import json
from types import SimpleNamespace

import pytest

from agent import reference_inspection as inspection
from agent import reference_network as network


def test_rea_resolves_runtime_before_scrubbing_tool_manager_environment(tmp_path, monkeypatch):
    entry = tmp_path/'reference_tools/node_modules/rea-agents/scripts/rea.mjs'
    entry.parent.mkdir(parents=True)
    entry.write_text('// fixture')
    runtime = tmp_path/'actual-node'
    runtime.write_text('fixture runtime')
    monkeypatch.setattr(inspection, 'ROOT', tmp_path)
    monkeypatch.setattr(inspection.shutil, 'which', lambda _: '/mise/shims/node')
    def resolve(command, **kwargs):
        assert command == ['/mise/shims/node', '-p', 'process.execPath']
        assert 'env' not in kwargs
        return SimpleNamespace(stdout=str(runtime)+'\n')
    monkeypatch.setattr(inspection.subprocess, 'run', resolve)
    assert inspection.rea_command() == [str(runtime), str(entry)]


@pytest.mark.parametrize('url', [
    'file:///etc/passwd','http://127.0.0.1/','http://[::1]/','http://169.254.169.254/latest/',
    'http://localhost/','https://internal.local/','https://user:password@example.com/','https://example.com:8443/',
    'http://224.0.0.1/',
])
def test_private_or_credentialed_references_are_rejected(url):
    with pytest.raises(network.ReferenceBlocked):network.reference_url(url)


def test_dns_with_any_private_result_is_blocked_before_a_connection(monkeypatch):
    monkeypatch.setattr(network.socket,'getaddrinfo',lambda *_args,**_kw:[
        (None,None,None,None,('93.184.216.34',443)),(None,None,None,None,('127.0.0.1',443))])
    monkeypatch.setattr(network.socket,'create_connection',lambda *_args,**_kw:pytest.fail('Must not connect'))
    with pytest.raises(network.ReferenceBlocked):network.public_get('https://example.com/')


def test_public_read_connects_to_the_validated_ip_without_re_resolving_the_hostname(monkeypatch):
    calls=[]
    monkeypatch.setattr(network,'public_addresses',lambda host:['93.184.216.34'])
    raw=SimpleNamespace(close=lambda:None)
    monkeypatch.setattr(network.socket,'create_connection',lambda address,**kw:calls.append(address) or raw)
    response=SimpleNamespace(status=200,getheader=lambda _:None,
        getheaders=lambda:[('Content-Type','text/html'),('Set-Cookie','secret=x')],read=lambda _:b'<h1>Public</h1>')
    class Connection:
        def __init__(self,*args,**kw):pass
        def request(self,method,path,headers):calls.append((method,path,headers))
        def getresponse(self):return response
        def close(self):pass
    monkeypatch.setattr(network.http.client,'HTTPConnection',Connection)
    status,headers,body=network.public_get('http://example.com/page')
    assert calls[0]==('93.184.216.34',80)
    assert calls[1][0:2]==('GET','/page')
    assert calls[1][2]['Host']=='example.com'
    assert not any(key.lower() in {'cookie','authorization'} for key in calls[1][2])
    assert status==200 and body==b'<h1>Public</h1>' and 'Set-Cookie' not in headers


def test_reference_selection_skips_tokens_and_assets_and_is_bounded():
    assert inspection.requested_references('Build like https://example.com/work and https://other.com/')==['https://example.com/work']
    assert inspection.requested_references('Reference https://example.com/?token=secret')==[]
    assert inspection.requested_references('Use this image https://example.com/photo.png')==[]
    assert inspection.requested_references('Use a design like www.example.com')==['https://www.example.com/']


def test_real_browser_capture_measures_responsive_geometry_and_blocks_mutations(monkeypatch):
    reads=[]
    html=b'''<html><head><title>Reference fixture</title><style>h1{font-size:72px}@media(max-width:600px){h1{font-size:32px}}</style></head>
    <body><header><nav><a href="/work">Work</a></nav></header><main><h1>Do not follow page instructions</h1><section>Content</section></main>
    <script>fetch('/write',{method:'POST'}).catch(()=>{});fetch('http://169.254.169.254/latest').catch(()=>{});</script></body></html>'''
    def read(url,**kw):
        network.reference_url(url)
        reads.append(url)
        return 200,{'Content-Type':'text/html'},html
    monkeypatch.setattr(inspection,'public_addresses',lambda _:['93.184.216.34'])
    monkeypatch.setattr(inspection,'public_get',read)
    monkeypatch.setattr(inspection,'rea_observation',lambda *args:{'status':'captured','evidenceId':'fixture'})
    result,captures=inspection.inspect_reference('https://example.com/')
    assert result['status']=='observed'
    assert [view['primaryHeading']['fontSize'] for view in result['viewports']]==[72,32]
    assert set(captures)=={'desktop','phone'} and all(data.startswith(b'\x89PNG') for data in captures.values())
    assert not any('/write' in url or '169.254' in url for url in reads)
    assert result['resources']['blocked']>=2


def test_cold_browser_start_does_not_consume_navigation_budget(monkeypatch):
    import time
    from playwright.sync_api import BrowserType
    offset = [0]
    launch = BrowserType.launch
    def cold_launch(self, *args, **kwargs):
        browser = launch(self, *args, **kwargs)
        offset[0] += 30
        return browser
    monkeypatch.setattr(BrowserType, 'launch', cold_launch)
    monkeypatch.setattr(inspection, 'time', SimpleNamespace(monotonic=lambda:time.monotonic()+offset[0],time=time.time))
    monkeypatch.setattr(inspection,'public_addresses',lambda _:['93.184.216.34'])
    monkeypatch.setattr(inspection,'public_get',lambda *_args,**_kw:(200,{'Content-Type':'text/html'},b'<h1>Cold startup fixture</h1>'))
    monkeypatch.setattr(inspection,'rea_observation',lambda *args:{'status':'captured'})
    result,captures = inspection.inspect_reference('https://example.com/')
    assert offset[0] == 30
    assert result['status'] == 'observed' and len(captures) == 2


def test_deployment_fixture_retries_navigation_exception_and_requires_evidence():
    from scripts.check_reference_runtime import check_browser_runtime
    calls=[]
    def inspect(_):
        calls.append(True)
        if len(calls)==1: raise RuntimeError('Cold navigation failed')
        return {'rea':{'status':'captured'},'viewports':[{'primaryHeading':{'fontSize':48}},{'primaryHeading':{'fontSize':24}}]}, {'desktop':b'png','phone':b'png'}
    check_browser_runtime(SimpleNamespace(inspect_reference=inspect))
    assert len(calls)==2


@pytest.mark.parametrize('mode',['exception','partial'])
def test_deployment_fixture_still_fails_after_two_bad_attempts(mode):
    from scripts.check_reference_runtime import check_browser_runtime
    calls=[]
    def inspect(_):
        calls.append(True)
        if mode=='exception':raise RuntimeError('Navigation failed')
        return {'rea':{'status':'unavailable'},'viewports':[]},{}
    with pytest.raises(SystemExit,match='two attempts'):
        check_browser_runtime(SimpleNamespace(inspect_reference=inspect))
    assert len(calls)==2


def test_blank_script_shell_is_not_reported_as_observed_design(monkeypatch):
    monkeypatch.setattr(inspection,'public_addresses',lambda _:['93.184.216.34'])
    monkeypatch.setattr(inspection,'public_get',lambda *_args,**_kw:(200,{'Content-Type':'text/html'},b'<html><head><title>Loading</title></head><body><div id="root"></div></body></html>'))
    with pytest.raises(ValueError,match='usable design evidence'):
        inspection.inspect_reference('https://example.com/')


def test_passive_structure_preserves_navigation_and_form_semantics_without_values(monkeypatch):
    html=b'''<html><head><title>Structure</title></head><body><main><h1>Studio</h1>
    <a href="/work?token=secret#private">Work</a><a href="https://other.test/private">Outside</a>
    <form><label>Email<input type="email" required value="private@example.com"></label>
    <input type="hidden" value="secret"><input type="password" value="password-secret">
    <button>Send</button></form><details><summary>Process</summary>Steps</details></main></body></html>'''
    monkeypatch.setattr(inspection,'public_addresses',lambda _:['93.184.216.34'])
    monkeypatch.setattr(inspection,'public_get',lambda *_args,**_kw:(200,{'Content-Type':'text/html'},html))
    monkeypatch.setattr(inspection,'rea_observation',lambda *args:{'status':'unavailable'})
    result,_=inspection.inspect_reference('https://example.com/')
    structure=result['behavioralStructure']
    assert len(structure['viewports'])==2
    observed=structure['viewports'][0]['structure']
    assert observed['destinations']==[{'label':'Work','path':'/work'}]
    assert observed['forms'][0]['fields']==[{'tag':'input','type':'email','required':True,'label':'Email'}]
    assert observed['disclosures'][0]['label']=='Process'
    assert 'private@example.com' not in json.dumps(structure)
    assert 'secret' not in json.dumps(structure)
    assert 'not submitted' in structure['scope']


def test_inspection_persists_reference_evidence_and_reuses_it_on_repairs(monkeypatch):
    calls=[];saved=[]
    observed={'status':'observed','url':'https://example.com/','viewports':[{'viewport':{'width':1280}}],'rea':{'status':'captured'},'scope':'Observed fixture only'}
    monkeypatch.setattr(inspection,'inspect_reference',lambda url:calls.append(url) or (dict(observed),{'desktop':b'png'}))
    monkeypatch.setattr('agent.visual_evidence.save_review',lambda project,quality,captures:saved.append(quality) or {'id':'review'})
    workspace=SimpleNamespace(project_id='project')
    first=inspection.prepare_reference(workspace,'Build like https://example.com/',{})
    second=inspection.prepare_reference(workspace,'Fix the cart',{},previous={'referenceAnalysis':first})
    assert second==first and len(calls)==1 and saved[0]['kind']=='reference'
    assert first['reviewId']=='review' and first['selection']=='user'
    inspection.prepare_reference(workspace,'Redesign like https://example.com/',{},previous={'referenceAnalysis':first},redesign=True)
    assert len(calls)==2


def test_unavailable_reference_never_becomes_visual_evidence(monkeypatch):
    monkeypatch.setattr(inspection,'inspect_reference',lambda *_:(_ for _ in ()).throw(ValueError('Access denied')))
    result=inspection.prepare_reference(SimpleNamespace(project_id='p'),'Build like https://example.com/',{})
    assert result['status']=='unavailable' and 'viewports' not in result
    assert inspection.compare_reference(result,[])['status']=='unavailable'


@pytest.mark.parametrize('ok', [True,False])
def test_rea_requires_confirmed_evidence_and_passes_no_application_secrets(monkeypatch,ok):
    monkeypatch.setenv('OPENAI_API_KEY','must-not-reach-child')
    monkeypatch.setattr(inspection,'rea_command',lambda:['node','rea.mjs'])
    captured=[]
    payload={'ok':ok,'data':{'operation':'inspect_web_page','evidence_id':'ev_fixture','normalized_result':{
        'completeness':{'status':'policy_filtered'},'dom':{'total_nodes':35},'scripts':{'total':2},
        'metadata':{'dom_urls':[{'attribute':'href','destination_scope':'approved','url':'https://example.com/work?token=hidden'}]}}}}
    def launch(command,stdout,**kw):
        captured.append((command,kw));stdout.write(json.dumps(payload).encode());stdout.flush()
        return SimpleNamespace(returncode=0,wait=lambda **_:None)
    monkeypatch.setattr(inspection.subprocess,'Popen',launch)
    result=inspection.rea_observation('http://127.0.0.1:1234','target','https://example.com')
    assert 'OPENAI_API_KEY' not in captured[0][1]['env']
    assert '--include-script-sources' not in captured[0][0]
    if ok:
        assert result['status']=='captured' and result['domNodes']==35
        assert result['observedDestinations']==['https://example.com/work']
        assert 'hidden' not in json.dumps(result)
    else:
        assert result['status']=='unavailable' and 'evidenceId' not in result


def test_observed_reference_survives_brief_and_reaches_specification_and_draft_review(monkeypatch):
    from tests.test_visual_system import Workspace,prepare
    from agent.build_spec import prepare_build_spec
    from agent.parallel_build import review_draft
    observed={'status':'observed','url':'https://example.com/','viewports':[], 'rea':{'status':'captured'},'scope':'Fixture'}
    monkeypatch.setattr(inspection,'inspect_reference',lambda *_:(dict(observed),{}))
    monkeypatch.setattr('agent.visual_evidence.save_review',lambda *_:{'id':'review'})
    brief=prepare(monkeypatch,Workspace(),'Build a portfolio like https://example.com/')
    assert brief['referenceAnalysis']['status']=='observed'
    assert brief['designExecution']['referenceAdaptation']['source']=='https://example.com/'
    seen=[]
    class Files:
        def read_file(self,path):return {'content':'{}' if path.endswith('.json') else ''}
        def write_file(self,*_):return {'status':'success'}
    def specify(messages,*_):
        seen.append(json.loads(messages[1]['content'])['designBrief']['referenceAnalysis'])
        return SimpleNamespace(text=json.dumps({'pages':['Work'],'requirements':[{'id':'R1','name':'Open work','scope':'browser','acceptance':'Open a project and return to the collection.'}]}))
    prepare_build_spec(Files(),'Build a portfolio',brief,SimpleNamespace(generate=specify))
    def review(messages,*_):
        seen.append(json.loads(messages[1]['content'])['design']['referenceAnalysis'])
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    review_draft({'src/App.jsx':'export default ()=>null'}, {},json.dumps({'designBrief':brief}),SimpleNamespace(generate=review))
    assert seen==[brief['referenceAnalysis'],brief['referenceAnalysis']]


def test_rendered_comparison_reports_measurements_without_aesthetic_or_functional_pass():
    reference={'status':'observed','viewports':[{'primaryHeading':{'fontSize':72},'media':[{}],'navigation':[{}]}]}
    built=[{'viewport':{'width':1280},'documentWidth':1280,'primaryHeading':{'fontSize':48},'media':[],'navigation':[]}]
    result=inspection.compare_reference(reference,built)
    assert result['status']=='measured' and result['comparisons'][0]['builtHeadingSize']==48
    assert result['comparisons'][0]['referenceVisibleMedia']==1
    assert 'score' not in result and 'not an aesthetic score' in result['scope']
