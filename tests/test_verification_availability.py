from types import SimpleNamespace
import pytest
from playwright.sync_api import sync_playwright
from agent.verification_dates import calendar_value
from agent.verification_availability import choose_available
from agent.functional_verification import target, verify_functions
from agent.build_spec import verification_scopes


def test_local_dates_roll_over_in_browser_timezone_without_mutating_cached_target():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page(timezone_id='Europe/Riga')
            page.clock.install(time=1793399400000)  # Oct 31, before midnight in Riga.
            today=calendar_value(page,'{{date+0}}');tomorrow=calendar_value(page,'{{date+1}}')
            page.set_content(f'<button aria-label="Choose date {tomorrow}">Tomorrow</button>')
            spec={'by':'role','role':'button','name':'Choose date {{date+1}}'}
            assert target(page,spec).count()==1
            assert spec['name']=='Choose date {{date+1}}'
            assert tomorrow!=today
            assert calendar_value(page,'{{date+30}}')>tomorrow
            for value in ['{{date+31}}','{{date+-1}}','{{date+1}} {{date+bad}}']:
                with pytest.raises(ValueError):calendar_value(page,value)
        finally:browser.close()


def test_available_option_is_scoped_visible_enabled_and_requires_named_group():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.set_content('''<button onclick="throw Error('outside')">Outside</button>
                <div role="group" aria-label="Available times">
                <button hidden>Hidden</button><button disabled>Unavailable</button>
                <button onclick="document.querySelector('output').textContent='10:30'">10:30</button></div>
                <output></output>''')
            choose_available(page.get_by_role('group',name='Available times'))
            assert page.locator('output').inner_text()=='10:30'
            with pytest.raises(ValueError,match='named option group'):choose_available(page.locator('body'))
            page.get_by_role('button',name='10:30').evaluate('e=>e.disabled=true')
            with pytest.raises(ValueError,match='no enabled visible option'):choose_available(page.get_by_role('group',name='Available times'))
        finally:browser.close()


def test_availability_action_requires_a_real_outcome_in_full_verifier():
    plan={'requirements':[{'id':'R1','name':'Choose available time'}], 'checks':[{'name':'Select time','covers':['R1'],'steps':[
        {'action':'chooseAvailable','target':{'by':'role','role':'group','name':'Available times'}},
        {'action':'visible','target':{'by':'text','name':'Selected 10:30','exact':True}}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page();page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='''<div role="group" aria-label="Available times"><button disabled>09:00</button><button onclick="document.querySelector('output').textContent='Selected 10:30'">10:30</button></div><output></output>'''));page.goto('https://fixture.test/')
            result=verify_functions(page,'Choose available time',SimpleNamespace(generate=lambda *_:None),attempt=1,_plan_override=plan)
            assert result['coverage']['passedIds']==['R1'] and not result['issues'],result
            plan['checks'][0]['steps'].pop()
            result=verify_functions(page,'Choose available time',SimpleNamespace(generate=lambda *_:None),attempt=1,validation_retry=2,_plan_override=plan)
            assert not result.get('coverage',{}).get('passedIds')
        finally:browser.close()


def test_local_reservation_creation_is_browser_scope_but_payment_docs_remain_external():
    spec={'requirements':[
        {'id':'R1','scope':'external','acceptance':'The app creates a local reservation record that persists after reload.'},
        {'id':'R2','scope':'external','acceptance':'Show local demo notice and document real payment integrations.'},
        {'id':'R3','scope':'external','acceptance':'Creates a local order, redirects to external provider and persists after reload.'}]}
    normalized=verification_scopes(spec)
    assert [x['scope'] for x in normalized['requirements']]==['browser','external','external']
    assert spec['requirements'][0]['scope']=='external'
