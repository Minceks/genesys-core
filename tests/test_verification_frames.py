import json
from types import SimpleNamespace
import pytest
from playwright.sync_api import sync_playwright
from agent.verification_frames import perform_frame,validate_frame
from agent.functional_verification import verify_functions


def test_canvas_frames_prove_real_render_changes_and_stability():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.set_content('<canvas width="128" height="128" aria-label="Arena"></canvas><button onclick="const c=document.querySelector(\'canvas\').getContext(\'2d\');c.fillStyle=\'red\';c.fillRect(10,10,50,50)">Move</button>')
            canvas=page.get_by_label('Arena');frames={}
            assert not perform_frame(canvas,{'action':'rememberFrame','key':'start'},frames)
            assert perform_frame(canvas,{'action':'frameStable','key':'start','threshold':0},frames)
            page.get_by_role('button',name='Move').click()
            assert perform_frame(canvas,{'action':'frameChanged','key':'start','threshold':.01},frames)
            with pytest.raises(AssertionError):perform_frame(canvas,{'action':'frameStable','key':'start','threshold':.001},frames)
            with pytest.raises(ValueError,match='same canvas target and region'):perform_frame(canvas,{'action':'frameChanged','key':'start','region':{'x':0,'y':0,'width':.5,'height':.5}},frames)
        finally:browser.close()


def test_frame_assertions_work_in_verification_and_cannot_compare_without_capture():
    plan={'requirements':[{'id':'R1','name':'Move painted player'}],'checks':[{'name':'Painted change','covers':['R1'],'steps':[
        {'action':'rememberFrame','target':{'by':'label','name':'Arena'},'key':'before'},
        {'action':'click','target':{'by':'role','role':'button','name':'Move'}},
        {'action':'frameChanged','target':{'by':'label','name':'Arena'},'key':'before','threshold':.01}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='<canvas width="128" height="128" aria-label="Arena"></canvas><button onclick="document.querySelector(\'canvas\').getContext(\'2d\').fillRect(10,10,60,60)">Move</button>'));page.goto('https://fixture.test/')
            result=verify_functions(page,'Move the player',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=plan)
            assert result['coverage']['passedIds']==['R1'] and not result['unverifiedCore'],result
            plan['checks'][0]['steps']=plan['checks'][0]['steps'][1:]
            result=verify_functions(page,'Move the player',SimpleNamespace(generate=lambda *_:None),attempt=1,validation_retry=2,_plan_override=plan)
            assert not result.get('coverage',{}).get('passedIds')
            assert 'capture frame before' in str(result['unverifiedCore'])
        finally:browser.close()

@pytest.mark.parametrize('step',[{'key':''},{'key':'k','threshold':2},{'key':'k','region':{'x':.8,'y':0,'width':.4,'height':1}},{'key':'k','region':{'x':0,'y':0,'width':0,'height':1}}])
def test_bad_frame_parameters_are_rejected(step):
    with pytest.raises(ValueError):validate_frame(step)


def test_frame_schema_fits_real_contract_limits():
    from agent.verification_planning import contract_plan_schema
    from agent.structured_schema import validate_schema_limits
    validate_schema_limits(contract_plan_schema({'requirements':[{'id':f'R{i}','scope':'browser'} for i in range(12)]}))


def test_canvas_workflow_budget_is_bounded_without_weakening_other_flows():
    from agent.verification_input import validate_input_budget
    wait={'action':'wait','durationMs':2000}
    with pytest.raises(ValueError,match='15 seconds'):validate_input_budget([{'steps':[wait]*9}])
    frames=[{'action':'rememberFrame'},{'action':'frameChanged'}]
    validate_input_budget([{'steps':frames+[wait]*15}])
    with pytest.raises(ValueError):validate_input_budget([{'steps':frames+[wait]*16}])
    with pytest.raises(ValueError):validate_input_budget([{'steps':frames+[wait]*15}]*3)


def test_bounded_hold_stops_at_real_outcome_and_releases_keys():
    from agent.verification_input import perform_input
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.set_content('<canvas tabindex="0" aria-label="Arena"></canvas><div role="dialog" aria-label="Done" hidden>Done</div><output>0</output><script>let once=false;onkeydown=e=>{if(e.key===" "&&!once){once=true;document.querySelector("output").textContent="1";setTimeout(()=>{document.querySelector("div").hidden=false;document.querySelector("canvas").inert=true},100)}};onkeyup=e=>{if(e.key===" ")document.querySelector("output").textContent="0"}</script>')
            step={'action':'hold','keys':['Space'],'durationMs':1000,'untilVisible':{'by':'role','role':'dialog','name':'Done'}}
            perform_input(page,page.get_by_label('Arena'),step)
            assert page.get_by_role('dialog',name='Done').is_visible()
            assert page.locator('output').inner_text()=='0'
            perform_input(page,page.get_by_label('Arena'),step)
            assert page.locator('output').inner_text()=='0'
        finally:browser.close()


def test_stability_tolerance_cannot_mask_a_changed_scene():
    with pytest.raises(ValueError):validate_frame({'action':'frameStable','key':'k','threshold':1})
