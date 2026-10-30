from types import SimpleNamespace
from unittest.mock import Mock
from playwright.sync_api import sync_playwright
from agent.workflow_quality import WorkflowEvidence, REACHABILITY_SCRIPT
from agent.functional_verification import verify_functions
from agent.delivery_playbook import delivery_playbook
from agent.design_execution import design_execution
from agent.design_quality import BUILD_STANDARD


def test_unresolved_major_design_findings_become_owner_notes_and_outages_add_nothing():
    from agent.workflow_quality import remaining_design_notes
    findings=[{'severity':'major','evidence':'Phone result text is clipped.', 'correction':'Reflow result content.'},
              {'severity':'minor','evidence':'Accent preference.', 'correction':'Consider another accent.'}]
    assert remaining_design_notes({'status':'needs_polish','findings':findings})==[
        'Design review: Phone result text is clipped. Suggested change: Reflow result content.']
    assert remaining_design_notes({'status':'unavailable','findings':findings})==[]
    assert remaining_design_notes({'status':'ready','findings':[]})==[]


def test_default_playbook_is_shared_without_imposing_the_example_game_on_other_products():
    for kind in ['website','app','store','game','portfolio','dashboard']:
        brief={'productType':kind}
        assert design_execution(brief)['deliveryPlaybook']==delivery_playbook(brief)
    assert 'DELIVERY CRAFT STANDARD' in BUILD_STANDARD
    assert 'Do not reuse the same' in BUILD_STANDARD
    assert 'Respect abstract puzzles and minimal requests' in BUILD_STANDARD


def test_phone_occlusion_is_detected_and_clears_with_reserved_content_space():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':390,'height':844})
            page.set_content('''<button style="position:absolute;bottom:12px;height:44px;width:120px">Book</button>
                <nav style="position:fixed;bottom:0;left:0;width:100%;height:80px;background:white">Navigation</nav>''')
            blocked=page.evaluate(REACHABILITY_SCRIPT)['blockedControls']
            assert len(blocked)==1 and blocked[0]['label']=='Book'
            page.get_by_role('button',name='Book').evaluate("e=>e.style.bottom='100px'")
            assert not page.evaluate(REACHABILITY_SCRIPT)['blockedControls']
            page.set_content('''<button>Behind</button><div role="dialog" aria-modal="true" style="position:fixed;inset:0;background:white"><button>Confirm</button></div>''')
            assert not page.evaluate(REACHABILITY_SCRIPT)['blockedControls']
        finally:browser.close()


def test_workflow_capture_uses_real_checked_state_before_storage_restoration_and_is_bounded():
    plan={'requirements':[{'id':'R1','name':'Save result'}], 'checks':[{'name':'Save and show result','covers':['R1'],'steps':[
        {'action':'click','target':{'by':'role','role':'button','name':'Save'}},
        {'action':'visible','target':{'by':'text','name':'Saved result','exact':True}}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':1000,'height':900})
            page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='''<button onclick="localStorage.setItem('saved','yes');document.querySelector('output').textContent='Saved result'">Save</button><output></output>'''))
            page.goto('https://fixture.test/')
            evidence=WorkflowEvidence();states=[]
            def capture(page,name):
                states.append(page.locator('output').inner_text())
                evidence.capture(page,name)
            result=verify_functions(page,'Save result',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=plan,_on_workflow=capture)
            assert result['coverage']['passedIds']==['R1'],result
            assert states==['Saved result']
            assert page.evaluate("localStorage.getItem('saved')")=='yes'
            assert page.viewport_size=={'width':1000,'height':900}
            assert len(evidence.images)==2 and not evidence.issues
            for _ in range(5):evidence.capture(page,'Another checked state')
            assert len(evidence.images)==6 and evidence.states==3
            assert all('not separate phone functional execution' in v['scope'] for v in evidence.details.values())
        finally:browser.close()


def test_failed_capture_does_not_invent_an_application_defect_or_pass():
    page=Mock();page.viewport_size={'width':1000,'height':900}
    page.evaluate.return_value={'x':0,'y':0,'blockedControls':[]}
    page.screenshot.side_effect=RuntimeError('Unavailable browser screenshot')
    evidence=WorkflowEvidence();evidence.capture(page,'Saved result')
    assert not evidence.images and evidence.unavailable
    assert page.set_viewport_size.call_args.args[0]==page.viewport_size
    page.evaluate.side_effect=RuntimeError('Browser unavailable')
    evidence=WorkflowEvidence();evidence.capture(page,'Result')
    assert not evidence.images and not evidence.issues and evidence.unavailable


def test_later_real_combat_replaces_early_action_within_the_image_budget():
    page=Mock();page.viewport_size={'width':1000,'height':900}
    page.evaluate.side_effect=lambda script:False if 'scrollWidth' in script else {'x':0,'y':0,'blockedControls':[]}
    page.screenshot.return_value=b'actual-capture'
    evidence=WorkflowEvidence()
    for name in ['Menu','Rendered action frame: Early movement','Paused outcome','Rendered action frame: Real dual-touch combat']:
        evidence.capture(page,name)
    assert len(evidence.images)==6
    action=[v for v in evidence.details.values() if v['kind']=='action-frame']
    assert len(action)==2 and all(v['workflow'].endswith('Real dual-touch combat') for v in action)


def test_workflow_review_stays_within_provider_image_budget_and_preserves_metadata(monkeypatch):
    from agent import browser as module
    from agent.visual_review import VisualPolishLoop
    session=object.__new__(module.BrowserSession)
    evidence=WorkflowEvidence()
    evidence.images=[(f'generated-workflow-{i}',b'fixture') for i in range(6)]
    evidence.details={label:{'workflow':str(i)} for i,(label,_) in enumerate(evidence.images)}
    session._workflow_evidence=evidence;session.project_id='fixture'
    monkeypatch.setattr(module,'get_workspace',lambda _:SimpleNamespace(build_fingerprint=lambda:'source-1'))
    captured=[]
    def review(provider,brief,images,previous,capture_details):
        captured.extend(images)
        assert len(images)==4 and set(capture_details)=={label for label,_ in images}
        return {'status':'ready','summary':'Reviewed actual states','findings':[]}
    monkeypatch.setattr('agent.visual_review.review_screenshots',review)
    monkeypatch.setattr('agent.ai_provider.OpenAIProvider',lambda **_:None)
    result,repair=module.BrowserSession.review_workflow_design.__wrapped__(session,{},VisualPolishLoop())
    assert result['status']=='ready' and not repair
    assert captured==evidence.images[-4:]
