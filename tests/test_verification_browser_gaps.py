import json
from types import SimpleNamespace
from playwright.sync_api import sync_playwright
from agent.functional_verification import declared_browser_gaps, verify_functions

CONTRACT={'requirements':[
    {'id':'B1','name':'Working input modes','scope':'browser','acceptance':'Selecting Touch saves the preference and shows a working movement joystick and Fire button.'},
    {'id':'V1','name':'Art quality','scope':'visual','acceptance':'Inspect the art quality on desktop and mobile.'}]}
GAP='B1: Touch preference persists but the required joystick and fire controls are missing.'


def test_admitted_partial_outcome_is_bound_to_browser_acceptance():
    plan={'unverifiedCore':[GAP,'V1: Art needs review','UNKNOWN: Additional feature'],
          'coreRequestEvidence':[{'requirement':GAP,'requestQuote':CONTRACT['requirements'][0]['acceptance']},
              {'requirement':'V1: Art needs review','requestQuote':CONTRACT['requirements'][1]['acceptance']}]}
    assert declared_browser_gaps(plan,CONTRACT)=={'B1':GAP}
    plan['coreRequestEvidence'][0]['requirement']='B1'
    assert declared_browser_gaps(plan,CONTRACT)=={'B1':GAP}
    plan['coreRequestEvidence'][0]['requestQuote']='Invented multi-user backend infrastructure'
    assert not declared_browser_gaps(plan,CONTRACT)


def test_missing_control_cannot_pass_as_a_saved_preference_and_enters_app_repair():
    plan={'requirements':[{'id':'B1','name':'Working input modes'}],
          'unverifiedCore':[GAP],'coreRequestEvidence':[{'requirement':GAP,'requestQuote':CONTRACT['requirements'][0]['acceptance']}],
          'checks':[{'name':'Preference saved only','covers':['B1'],'steps':[
              {'action':'click','target':{'by':'role','role':'button','name':'Touch','exact':True}},
              {'action':'visible','target':{'by':'text','name':'Preference saved','exact':True}}]}]}
    class Provider:
        def generate(self,messages,*_):
            if messages[0]['content'].startswith('Diagnose browser'):
                return SimpleNamespace(text=json.dumps({'kind':'application_failure',
                    'evidence':'The handler only saves a preference; the page and implementation contain no joystick or Fire control.'}))
            return SimpleNamespace(text=json.dumps(plan))
    with sync_playwright() as p:
        browser=p.chromium.launch(); context=browser.new_context()
        context.route('https://fixture.example.test/**',lambda route:route.fulfill(content_type='text/html',
            body='<button onclick="document.querySelector(\'p\').textContent=\'Preference saved\'">Touch</button><p>Ready</p>'))
        page=context.new_page();page.goto('https://fixture.example.test/')
        result=verify_functions(page,'Create an interactive app',Provider(),attempt=1,contract=CONTRACT,
            sources={'App.jsx':'function touch(){localStorage.setItem("mode","touch")} // no joystick or fire handler'})
        assert result['status']=='error' and result['issues'],result
        assert 'B1' not in result['coverage']['passedIds']
        assert GAP in result['unverifiedCore']
        browser.close()
