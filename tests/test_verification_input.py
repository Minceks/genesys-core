import json
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions
from agent.verification_input import input_duration, perform_input, validate_input_budget


@pytest.mark.parametrize('step', [
    {'action':'hold','keys':['w'],'durationMs':3001},
    {'action':'hold','keys':['Control','w'],'durationMs':100},
    {'action':'press','key':'Control+w'},
    {'action':'hold','keys':['w','w'],'durationMs':100},
    {'action':'wait','durationMs':True},
    {'action':'pointer','mode':'click','x':float('nan'),'y':0.5},
    {'action':'pointer','mode':'click','x':1.1,'y':0.5},
    {'action':'pointer','mode':'drag','x':0.5,'y':0.5,'endX':-1,'endY':0.5},
    {'action':'pointer','mode':'hold','x':0.5,'y':0.5,'durationMs':99999},
    {'action':'pointer','mode':'click','x':0.5,'y':0.5,'durationMs':500},
])
def test_unsafe_or_unbounded_input_is_rejected(step):
    with pytest.raises(ValueError, match='Invalid verification plan'): input_duration(step)


def test_wait_budget_applies_to_each_workflow_and_whole_plan():
    wait = {'action':'wait','durationMs':2000}
    with pytest.raises(ValueError, match='per workflow'):
        validate_input_budget([{'steps':[wait] * 8}])
    with pytest.raises(ValueError, match='total input'):
        validate_input_budget([{'steps':[wait] * 7}] * 4)


def test_held_keys_are_released_when_a_browser_step_fails():
    events = []
    keyboard = SimpleNamespace(down=lambda key: events.append(('down',key)), up=lambda key: events.append(('up',key)))
    def unavailable(_): raise RuntimeError('Browser closed')
    page = SimpleNamespace(keyboard=keyboard, wait_for_timeout=unavailable)
    control = SimpleNamespace(count=lambda:1, is_visible=lambda:True, focus=lambda **_:None, evaluate=lambda _:True)
    with pytest.raises(RuntimeError, match='Browser closed'):
        perform_input(page, control, {'action':'hold','keys':['w','Space'],'durationMs':100})
    assert events == [('down','w'),('down',' '),('up',' '),('up','w')]


@pytest.mark.parametrize('responsive',[True,False])
def test_real_canvas_inputs_execute_with_actual_outcome_assertions(responsive):
    surface = {'by':'label','name':'Drawing canvas'}
    plan = {'requirements':[{'id':'input','name':'Keyboard movement, canvas aiming and drag'}], 'checks':[
        {'name':'Actual canvas interaction','covers':['input'],'steps':[
            {'action':'hold','target':surface,'keys':['ArrowRight'],'durationMs':200},
            {'action':'visible','target':{'by':'text','name':'Moved with keyboard','exact':True}},
            {'action':'pointer','target':surface,'mode':'click','x':0.8,'y':0.25},
            {'action':'visible','target':{'by':'text','name':'Aimed at right side','exact':True}},
            {'action':'pointer','target':surface,'mode':'drag','x':0.1,'y':0.5,'endX':0.3,'endY':0.5},
            {'action':'visible','target':{'by':'text','name':'Dragged across canvas','exact':True}},
            {'action':'number','target':{'by':'label','name':'Drawn shapes'},'comparison':'gt','value':0},
        ]}]}
    class Provider:
        def generate(self, *_): return SimpleNamespace(text=json.dumps(plan))
    html = '''<canvas aria-label="Drawing canvas" tabindex="0" width="320" height="180" style="width:640px;height:360px"></canvas>
    <p id="moved">Waiting for keyboard</p><p id="aim">Waiting for aim</p><p id="drag">Waiting for drag</p>
    <output aria-label="Drawn shapes" id="count">Shapes: 0</output>
    <script>
    const canvas=document.querySelector('canvas'); let held=false,elapsed=0,last=performance.now();
    canvas.addEventListener('keydown',e=>{if(e.key==='ArrowRight')held=true});
    canvas.addEventListener('keyup',()=>held=false);
    function frame(now){if(held)elapsed+=now-last;last=now;if(elapsed>80)document.querySelector('#moved').textContent='Moved with keyboard'; requestAnimationFrame(frame)}
    requestAnimationFrame(frame);
    let startX=null;
    canvas.addEventListener('click',e=>{document.querySelector('#count').textContent='Shapes: 1';const r=canvas.getBoundingClientRect(); if((e.clientX-r.x)/r.width>0.7)document.querySelector('#aim').textContent='Aimed at right side'});
    canvas.addEventListener('pointerdown',e=>startX=e.clientX);
    canvas.addEventListener('pointerup',e=>{if(startX!==null&&e.clientX-startX>50)document.querySelector('#drag').textContent='Dragged across canvas';startX=null});
    </script>'''
    if not responsive: html=html.replace("if(e.key==='ArrowRight')held=true", "if(e.key==='ArrowRight')held=false")
    with sync_playwright() as p:
        browser=p.chromium.launch(); context=browser.new_context(viewport={'width':900,'height':600})
        context.route('https://input.example.test/**',lambda route:route.fulfill(content_type='text/html',body=html))
        page=context.new_page(); page.goto('https://input.example.test/')
        result=verify_functions(page,'Create a canvas editor with keyboard movement and pointer drawing',Provider())
        if responsive:
            assert result['status']=='success' and not result['issues'] and not result['unverifiedCore'],result
            assert result['testedInteractions']==['Actual canvas interaction']
        else:
            assert result['issues'] or result['unverifiedCore'],result
            assert not result['testedInteractions']
        browser.close()
