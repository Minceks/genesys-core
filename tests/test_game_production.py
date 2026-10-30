import json
import time
from types import SimpleNamespace
import pytest
from agent.parallel_build import draft_project, DraftReviewFailed
from agent.game_build import validate_game_plan, game_delivery_blockers


def plan():
    return dict(interface='createGame(canvas, callbacks) returns start/destroy',
                **{key:'Concrete genre-specific production decisions' for key in
                   ['scene','actors','cameraAndPhone','feedback','controls','stateTransitions','balance','verification']})


def test_complete_game_rebuilds_use_production_but_targeted_edits_keep_existing_source():
    from agent.game_build import needs_game_draft
    brief={'productType':'game'}
    assert needs_game_draft('Your project is ready','Build a zombie wave game',brief)
    assert needs_game_draft('Existing complete game','Rebuild this game as a zombie survival game',brief)
    assert not needs_game_draft('Existing complete game','Improve this game health bar spacing',brief)
    assert not needs_game_draft('Existing app','Rebuild this app',{'productType':'app'})


def test_game_ui_consumes_completed_renderer_and_keeps_styles_in_the_same_authoring_call():
    seen=[]
    engine='export function createGame(){return {start(){},destroy(){}}}'
    def generate(messages,*_):
        instruction=messages[0]['content'];payload=json.loads(messages[1]['content']);seen.append(instruction)
        if 'GAME PRODUCTION PLAN.' in instruction:return SimpleNamespace(text=json.dumps(plan()))
        if 'GAME ENGINE AND ART.' in instruction:
            assert 'cameraAndPhone' in payload['plan']
            return SimpleNamespace(text=json.dumps({'files':{'src/projectLogic.js':engine}}))
        if 'GAME UI AND STYLES.' in instruction:
            assert payload['engineFiles']['src/projectLogic.js']==engine
            return SimpleNamespace(text=json.dumps({'files':{'src/App.jsx':'export default function App(){return <main>Play</main>}', 'src/styles.css':'main{color:green}'}}))
        assert payload['files']['src/projectLogic.js']==engine
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    files=draft_project('Original puzzle',json.dumps({'designBrief':{'productType':'game'},'files':{}}),lambda _:SimpleNamespace(generate=generate),time.monotonic()+420)
    assert len(seen)==4 and files['src/projectLogic.js']==engine
    assert json.loads(files['.genesys-game-plan.json'])['pipeline']=='engine-art-then-integrated-ui'


def test_game_stage_failure_preserves_actual_renderer_and_plan_for_targeted_continuation():
    def generate(messages,*_):
        instruction=messages[0]['content']
        if 'GAME PRODUCTION PLAN.' in instruction:return SimpleNamespace(text=json.dumps(plan()))
        if 'GAME ENGINE AND ART.' in instruction:return SimpleNamespace(text='{"files":{"src/projectLogic.js":"export const originalScene=42"}}')
        raise TimeoutError('Synthetic UI stage timeout')
    with pytest.raises(DraftReviewFailed) as caught:
        draft_project('Synthetic game',json.dumps({'designBrief':{'productType':'game'},'files':{}}),lambda _:SimpleNamespace(generate=generate),time.monotonic()+420)
    assert caught.value.drafts['src/projectLogic.js']=='export const originalScene=42'
    assert json.loads(caught.value.drafts['.genesys-game-plan.json'])['plan']['interface']==plan()['interface']
    assert 'GAME PLAN:' in str(caught.value) and 'prototype' in str(caught.value)


def test_incomplete_plan_cannot_skip_the_scene_and_game_finish_cannot_pass_on_provider_failure():
    structured=plan();structured['interface']={'createGame':{'arguments':['canvas','callbacks'],'returns':['start','destroy']}}
    assert validate_game_plan(structured)==structured
    incomplete=plan();del incomplete['actors']
    with pytest.raises(ValueError,match='actors'):validate_game_plan(incomplete)
    assert game_delivery_blockers({'productType':'game'},{'status':'unavailable','summary':'No checked in-play evidence'})
    assert not game_delivery_blockers({'productType':'game'},{'status':'ready'})
    assert not game_delivery_blockers({'productType':'game'},{'status':'needs_polish','summary':'Phone HUD is busy'})
    assert not game_delivery_blockers({'productType':'app'},{'status':'unavailable'})


def test_accepted_game_screenshot_is_used_as_finish_reference_within_image_budget():
    from agent.visual_review import review_screenshots
    captured=[]
    def review(instruction,context,images,schema):
        captured.extend(images)
        assert len(images)==4 and images[-1][0]=='reference-accepted-action-game-workflow'
        assert images[-1][1].startswith(b'\x89PNG')
        assert 'gameProductionBenchmark' in context
        assert 'not exact layout' in instruction
        return SimpleNamespace(text='{"assessment":"ready","summary":"Observed scene finish","findings":[]}')
    images=[(f'generated-{i}',b'fixture') for i in range(4)]
    result=review_screenshots(SimpleNamespace(review_images=review),{'productType':'game','originalRequest':'Zombie survival'},images,capture_details={'generated-0':{'kind':'action-frame','workflow':'Real movement'}})
    assert result['status']=='ready' and captured[:2]==images[:2]


def test_opening_game_review_accepts_scroll_sample_lists_without_mistaking_them_for_action_frames():
    from agent.visual_review import review_screenshots
    def review(instruction,context,images,schema):
        assert len(images)==3 and images[-1][0]=='reference-accepted-action-game-entry'
        assert context['reviewPhase']=='entry'
        assert set(schema['properties']['findings']['items']['properties']['screenshot']['enum'])=={'generated-desktop','generated-phone'}
        return SimpleNamespace(text='{"assessment":"ready","summary":"Opening composition reviewed","findings":[]}')
    result=review_screenshots(SimpleNamespace(review_images=review),{'productType':'game','originalRequest':'Zombie survival'},
        [('generated-desktop',b'fixture'),('generated-phone',b'fixture')],
        capture_details={'generated-desktop':[{'scrollY':0,'width':1280,'height':800}],
                         'generated-phone':[{'scrollY':0,'width':390,'height':844}]})
    assert result['status']=='ready'


def test_game_plan_is_quick_without_reducing_engine_generation_capacity(monkeypatch):
    from unittest.mock import Mock
    from agent.ai_provider import OpenAIProvider
    from agent.progress import draft_stage_deadline
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_,**kwargs:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))]))
    provider=OpenAIProvider(model='gpt-5-mini',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    provider.generate([{'role':'system','content':'DEFAULT BUILD STANDARD: GAME PRODUCTION PLAN.'}],[])
    assert create.call_args.kwargs['model']=='gpt-5.4' and create.call_args.kwargs['reasoning_effort']=='low'
    assert create.call_args.kwargs['max_completion_tokens']==8000
    provider.generate([{'role':'system','content':'DEFAULT BUILD STANDARD: GAME ENGINE AND ART.'}],[])
    assert create.call_args.kwargs['max_completion_tokens']==24000
    monkeypatch.setattr('agent.progress.time.monotonic',lambda:100)
    assert draft_stage_deadline(1000,game=True)==640
    assert draft_stage_deadline(500,game=True)==380


def test_game_review_keeps_action_frames_when_later_workflows_end_on_settings(monkeypatch):
    from agent import browser as module
    from agent.workflow_quality import WorkflowEvidence
    from agent.visual_review import VisualPolishLoop
    evidence=WorkflowEvidence()
    evidence.images=[(f'generated-workflow-{i}',b'fixture') for i in range(6)]
    evidence.details={label:{'kind':'action-frame' if i<2 else 'workflow-outcome'} for i,(label,_) in enumerate(evidence.images)}
    session=object.__new__(module.BrowserSession);session._workflow_evidence=evidence;session.project_id='fixture'
    monkeypatch.setattr(module,'get_workspace',lambda _:SimpleNamespace(build_fingerprint=lambda:'source-1'))
    captured=[]
    def review(provider,brief,images,previous,capture_details):
        captured.extend(images);return {'status':'ready','summary':'Observed gameplay','findings':[]}
    monkeypatch.setattr('agent.visual_review.review_screenshots',review)
    monkeypatch.setattr('agent.ai_provider.OpenAIProvider',lambda **_:None)
    result,_=module.BrowserSession.review_workflow_design.__wrapped__(session,{'productType':'game'},VisualPolishLoop())
    assert result['status']=='ready' and captured==evidence.images[:2]+evidence.images[-2:]


def test_real_canvas_action_is_captured_before_a_workflow_returns_to_menu():
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    from agent.workflow_quality import WorkflowEvidence
    target={'by':'label','name':'Playfield','exact':True}
    check={'requirements':[{'id':'R1','name':'Move and return'}], 'checks':[{'name':'Movement and menu','covers':['R1'],'steps':[
        {'action':'rememberFrame','target':target,'key':'before'},
        {'action':'hold','target':target,'keys':['d'],'durationMs':100},
        {'action':'frameChanged','target':target,'key':'before'},
        {'action':'click','target':{'by':'role','role':'button','name':'Return to menu'}},
        {'action':'visible','target':{'by':'text','name':'Title screen','exact':True}}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='''
              <main><canvas aria-label="Playfield" width="400" height="300" tabindex="0"></canvas>
              <button onclick="document.querySelector('main').innerHTML='Title screen'">Return to menu</button></main>
              <script>const c=document.querySelector('canvas'),ctx=c.getContext('2d');ctx.fillStyle='black';ctx.fillRect(0,0,400,300);
              c.onkeydown=e=>{if(e.key==='d'){ctx.fillStyle='white';ctx.fillRect(50,50,120,100)}};</script>'''))
            page.goto('https://fixture.test/');evidence=WorkflowEvidence()
            result=verify_functions(page,'Move and return',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=check,_on_workflow=evidence.capture)
            assert result['coverage']['passedIds']==['R1'],result
            assert len(evidence.images)==4
            assert [item['kind'] for item in evidence.details.values()]==['action-frame','action-frame','workflow-outcome','workflow-outcome']
        finally:browser.close()


def test_game_polish_uses_focused_complete_source_and_applies_only_owned_unique_patches():
    from agent.game_build import polish_game
    files={'src/styles.css':'main {color:red; min-height:100vh; padding:24px;}','src/gameDesign.js':'export const GAME_DESIGN={title:"Ashline"};'}
    class Workspace:
        def read_file(self,path):return {'content':files[path]}
        def write_file(self,path,content):files[path]=content;return {'status':'success'}
    def generate(messages,*_):
        assert len(messages)==2 and messages[1]['_preserve_complete_source']
        payload=json.loads(messages[1]['content'])
        assert payload['files']==files
        return SimpleNamespace(text=json.dumps({'edits':[{'path':'src/styles.css','old':'color:red','new':'color:green'}]}))
    assert polish_game(Workspace(),'Improve visible contrast',SimpleNamespace(generate=generate))==['src/styles.css']
    assert 'color:green' in files['src/styles.css']
    override='@media(max-width:600px){main{padding:16px}}'
    assert polish_game(Workspace(),'Improve phone spacing',SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps({'edits':[{'path':'src/styles.css','old':'','new':override}]}))))==['src/styles.css']
    assert files['src/styles.css'].endswith(override+'\n')
    before=dict(files)
    with pytest.raises(ValueError,match='ownership'):
        polish_game(Workspace(),'Keep working mechanics',SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps({'edits':[{'path':'src/projectLogic.js','old':'real','new':'fake'}]}))))
    assert files==before


def test_visual_copy_repairs_preserve_saved_data_and_encounter_mechanics():
    from agent.game_build import polish_game
    from pathlib import Path
    import runpy
    design=runpy.run_path(str(Path(__file__).with_name('test_game_foundation.py')))['design']()
    files={'src/styles.css':'body {padding:24px; min-height:100vh;}',
           'src/gameDesign.js':'export const GAME_DESIGN = '+json.dumps(design)+';'}
    class Workspace:
        def read_file(self,path):return {'content':files[path]}
        def write_file(self,path,value):files[path]=value;return {'status':'success'}
    def provider(old,new):
        return SimpleNamespace(generate=lambda *_:SimpleNamespace(text=json.dumps({'edits':[{'path':'src/gameDesign.js','old':old,'new':new}]})))
    assert polish_game(Workspace(),'Correct the setting copy',provider('Move, build your edge and survive the outbreak.','Hold the quarantine perimeter.'))==['src/gameDesign.js']
    before=dict(files)
    with pytest.raises(ValueError,match='balance'):
        polish_game(Workspace(),'Only visual polish',provider('"dashCooldown": 4.5','"dashCooldown": 0'))
    assert files==before


def test_visual_renderer_repairs_can_fix_art_and_camera_but_not_simulation():
    from agent.game_build import validate_renderer_patch
    from pathlib import Path
    source=(Path(__file__).parents[1]/'agent/game_foundations/survival/projectLogic.js').read_text()
    validate_renderer_patch(source,source.replace('(rect.width < 680 ? 1.12 : 1)','(rect.width < 680 ? 1.3 : 1)'))
    validate_renderer_patch(source,source.replace('ctx.scale(size, size);','ctx.scale(size * 1.2, size * 1.2);'))
    with pytest.raises(ValueError,match='owned actor/render'):
        validate_renderer_patch(source,source.replace('player.hp--;','player.hp = 100;'))
    with pytest.raises(ValueError,match='simulation'):
        validate_renderer_patch(source,source.replace('ctx.scale(size, size);','player.hp = 100; ctx.scale(size, size);'))


def test_focused_polisher_can_apply_an_agent_authored_camera_repair():
    from agent.game_build import polish_game
    from pathlib import Path
    files={'src/styles.css':'main{min-height:100vh}', 'src/projectLogic.js':
        (Path(__file__).parents[1]/'agent/game_foundations/survival/projectLogic.js').read_text()}
    class Workspace:
        def read_file(self,path):return {'content':files.get(path,'')}
        def write_file(self,path,content):files[path]=content;return {'status':'success'}
    def generate(messages,*_):
        assert json.loads(messages[1]['content'])['files']['src/projectLogic.js']==files['src/projectLogic.js']
        return SimpleNamespace(text=json.dumps({'edits':[{'path':'src/projectLogic.js','old':'(rect.width < 680 ? 1.12 : 1)','new':'(rect.width < 680 ? 1.3 : 1)'}]}))
    assert polish_game(Workspace(),'Phone combat is too small',SimpleNamespace(generate=generate))==['src/projectLogic.js']
    assert '(rect.width < 680 ? 1.3 : 1)' in files['src/projectLogic.js']


def test_entry_can_be_rechecked_after_both_bounded_game_polish_phases():
    from agent.visual_review import VisualPolishLoop
    loop=VisualPolishLoop(max_reviews=3)
    assert loop.run('initial',lambda _:{'status':'needs_polish','findings':[]})[1]
    assert loop.run('menu-repaired',lambda _:{'status':'ready','findings':[]})[0]['status']=='ready'
    assert loop.run('gameplay-repaired',lambda _:{'status':'ready','findings':[]})[0]['status']=='ready'
    assert loop.run('fourth',lambda _:None)[0]['status']=='unavailable'


def test_game_polish_can_observe_actual_combat_with_complete_owned_source():
    from agent.game_build import polish_game
    files={'src/styles.css':'main{min-height:100vh}'}
    class Workspace:
        def read_file(self,path):return {'content':files.get(path,'')}
        def write_file(self,path,value):files[path]=value;return {'status':'success'}
    images=[('actual-desktop',b'frame'),('actual-phone',b'frame')]
    def review(instruction,context,received,schema):
        assert received==images and context['files']==files
        assert schema['properties']['edits']['items']['properties']['path']['enum']==['src/styles.css']
        return SimpleNamespace(text=json.dumps({'edits':[{'path':'src/styles.css','old':'','new':'main{padding:20px}'}]}))
    assert polish_game(Workspace(),'Read actual combat',SimpleNamespace(review_images=review),images)==['src/styles.css']


def test_game_visual_repairs_are_bounded_but_can_correct_a_remaining_major_finding():
    from agent.visual_review import VisualPolishLoop
    loop=VisualPolishLoop(max_reviews=4,max_repairs=2)
    callback=lambda _:{'status':'needs_polish','findings':[]}
    assert loop.run('first',callback)[1]
    assert loop.run('second',callback)[1]
    assert not loop.run('third',callback)[1]


def test_image_aware_game_polish_never_truncates_its_source_context(monkeypatch):
    from unittest.mock import Mock
    from agent.ai_provider import OpenAIProvider
    captured=[]
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,*_,**kwargs:captured.extend(messages) or messages)
    monkeypatch.setattr('agent.model_context.reserve_model_budget',lambda _:None)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(usage=None,choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{"edits":[]}'))]))
    provider=OpenAIProvider(model='gpt-5.4',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    provider.review_images('DEFAULT BUILD STANDARD: GAME TARGETED POLISH.',{'source':'x'*30000+'SOURCE-END'},
        [('desktop',b'\x89PNGfixture'),('phone',b'\x89PNGfixture')],{'type':'object','properties':{},'additionalProperties':False})
    assert captured[1]['_preserve_complete_source'] and 'SOURCE-END' in captured[1]['content']
    assert 'SOURCE-END' in create.call_args.kwargs['messages'][1]['content'][0]['text']
    assert create.call_args.kwargs['max_completion_tokens']==16000


@pytest.fixture(autouse=True)
def plain_design_responses(monkeypatch):
    # These fakes return whole responses. Streaming is covered in test_build_upgrades.py.
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '0')
