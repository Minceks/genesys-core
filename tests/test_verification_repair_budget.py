import copy
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

from agent.functional_verification import verify_functions


def test_lost_detail_route_on_reload_reaches_application_diagnosis_without_query_tokens(tmp_path):
    (tmp_path/'index.html').write_text('''<h2>Home</h2><button onclick="location.hash='/detail/item';document.querySelector('h2').textContent='Item detail'">Open item</button>
    <script>if(location.hash){history.replaceState(null,'',location.pathname+location.search)}</script>''')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    contract={'requirements':[{'id':'detail','name':'Addressable detail reload','scope':'browser','acceptance':'Open detail and reload; the detail remains visible.'}]}
    class Provider:
        diagnosis = None
        def generate(self,messages,*_):
            if messages[0]['content'].startswith('Diagnose browser'):
                self.diagnosis=json.loads(messages[1]['content'])
                return SimpleNamespace(text=json.dumps({'kind':'application_failure','evidence':'The source replaces the detail hash on reload and DOM returns Home.'}))
            return SimpleNamespace(text=json.dumps({'requirements':[{'id':'detail','name':'Addressable detail reload'}], 'checks':[
                {'name':'Open detail and reload it','covers':['detail'],'independent':True,'steps':[
                    {'action':'click','target':{'by':'role','role':'button','name':'Open item'}},
                    {'action':'visible','target':{'by':'role','role':'heading','name':'Item detail'}},
                    {'action':'reload'},
                    {'action':'visible','target':{'by':'role','role':'heading','name':'Item detail'}}]}], 'unverified':[], 'unverifiedCore':[]}))
    provider=Provider()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/?preview_token=synthetic-secret')
                result=verify_functions(page,'Detail must survive reload',provider,attempt=1,contract=contract,sources={'index.html':(tmp_path/'index.html').read_text()})
                assert result['status']=='error' and result['issues'] and '_verifiedPlan' not in result
                failure=provider.diagnosis['failedSteps'][0]
                transition=failure['reloadTransitions'][0]
                assert transition['before']['url'].endswith('#/detail/item')
                assert transition['before']['headings']==['Item detail']
                assert transition['after']['headings']==['Home']
                assert not transition['after']['url'].endswith('#/detail/item')
                assert 'synthetic-secret' not in json.dumps(failure)
            finally: browser.close()
    finally: server.shutdown()


def test_automatic_recovery_can_correct_a_second_bad_plan_but_remains_bounded(tmp_path):
    (tmp_path/'index.html').write_text('<button onclick="this.textContent=\'Saved\'">Confirm actual</button>')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    contract={'requirements':[{'id':'R1','name':'Confirm selection','scope':'browser','acceptance':'Confirm and see Saved'}]}
    class Provider:
        def __init__(self, recover): self.plans=0;self.diagnoses=0;self.recover=recover
        def generate(self,messages,*_):
            if messages[0]['content'].startswith('Diagnose browser'):
                self.diagnoses+=1
                return SimpleNamespace(text='{"kind":"verification_failure"}')
            assert messages[0]['content'].startswith('You are a browser verification planner.')
            self.plans+=1
            assert self.plans<=3,'Two repair rounds must be the hard limit'
            name='Confirm actual' if self.recover and self.plans==3 else 'Invented control '+str(self.plans)
            return SimpleNamespace(text=json.dumps({'requirements':[{'id':'R1','name':'Confirm selection'}],
                'checks':[{'name':'Confirm selection','covers':['R1'],'independent':True,'steps':[
                    {'action':'click','target':{'by':'role','role':'button','name':name}},
                    {'action':'visible','target':{'by':'text','name':'Saved'}}]}], 'unverified':[],'unverifiedCore':[]}))
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                for recover in (True,False):
                    page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
                    provider=Provider(recover)
                    result=verify_functions(page,'Confirm selection',provider,contract=contract)
                    assert provider.plans==3
                    assert [r['round'] for r in result['verificationRecovery']]==[1,2]
                    if recover:
                        assert not result['issues'] and not result['unverifiedCore']
                        assert result['coverage']['passedIds']==['R1'] and provider.diagnoses==0
                    else:
                        assert result['unverifiedCore'] and '_verifiedPlan' not in result
                        assert provider.diagnoses==0  # A guessed control cannot justify application repair.
                    page.close()
            finally: browser.close()
    finally: server.shutdown()


def test_invalid_plan_does_not_consume_runtime_repair_and_failure_snapshot_survives_reset(tmp_path):
    (tmp_path/'index.html').write_text('''<button onclick="start()">Start</button><script>
    function start(){document.body.innerHTML='<h2>Confirm selection</h2><button aria-label="Confirm Consult" onclick="save()">Confirm booking</button>'}
    function save(){document.body.innerHTML='<p>Saved</p>'}
    </script>''')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    contract={'requirements':[{'id':'R1','name':'Confirm a selection','scope':'browser','acceptance':'Start, confirm, see Saved'}]}
    correct={'requirements':[{'id':'R1','name':'Confirm a selection'}],'checks':[
        {'name':'Confirm synthetic selection','covers':['R1'],'independent':True,'steps':[
            {'action':'click','target':{'by':'role','role':'button','name':'Start'}},
            {'action':'click','target':{'by':'role','role':'button','name':'Confirm Consult'}},
            {'action':'visible','target':{'by':'text','name':'Saved'}}]}], 'unverified':[],'unverifiedCore':[]}
    wrong=copy.deepcopy(correct)
    wrong['checks'][0]['steps'][1]['target']['name']='Confirm Consultation'
    later=copy.deepcopy(correct['checks'][0])
    later['name']='Later independent failure'
    later['steps'].insert(2,{'action':'click','target':{'by':'role','role':'button','name':'Missing action after save'}})
    wrong['checks'].append(later)
    class Provider:
        def __init__(self): self.calls=[]
        def generate(self,messages,*_):
            self.calls.append(messages)
            assert messages[0]['content'].startswith('You are a browser verification planner.'), 'No diagnosis or app repair is needed'
            plans=[dict(correct,checks=[]),wrong,correct]
            return SimpleNamespace(text=json.dumps(plans[len(self.calls)-1]))
    provider=Provider()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                page=browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}')
                result=verify_functions(page,'Confirm a selection',provider,contract=contract)
                assert not result['issues'] and not result['unverifiedCore'], result
                assert result['coverage']['passedIds']==['R1']
                assert len(provider.calls)==3
                feedback=json.dumps(provider.calls[2])
                assert 'failedSteps' in feedback and 'Confirm Consult' in feedback
                assert 'Confirm selection' in feedback
                evidence=json.loads(provider.calls[2][0]['content'].split('Untrusted observation before restoration: ',1)[1])
                assert len(evidence['failedSteps'])==2
                assert 'Confirm selection' in evidence['failedSteps'][0]['accessibilitySnapshot']
                assert 'Saved' in evidence['failedSteps'][1]['accessibilitySnapshot']
                assert evidence['renderedText']=='Saved'
            finally: browser.close()
    finally: server.shutdown()


def test_runtime_retry_keeps_a_passed_item_scope_when_fixing_a_hidden_form_label(tmp_path):
    (tmp_path/'index.html').write_text('''<article><h2>Item A</h2>
    <button onclick="document.querySelector('output').textContent='Added A'">Add</button></article>
    <article><h2>Item B</h2><button>Add</button></article><output></output>
    <button onclick="document.querySelector('form').hidden=false">Checkout</button>
    <form hidden onsubmit="event.preventDefault();document.querySelector('output').textContent='Saved order'">
    <label>Name<input></label><button>Save</button></form>''')
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    add = {'name': 'Add selected item', 'covers': ['R1'], 'independent': True, 'steps': [
        {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Add', 'withinText': 'Item A'}},
        {'action': 'visible', 'target': {'by': 'text', 'name': 'Added A'}}]}
    checkout = {'name': 'Save local order', 'covers': ['R2'], 'independent': True, 'steps': [
        {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Checkout'}},
        {'action': 'type', 'target': {'by': 'label', 'name': 'Name'}, 'value': 'Test person'},
        {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Save'}},
        {'action': 'visible', 'target': {'by': 'text', 'name': 'Saved order'}}]}
    requirements = [{'id': 'R1', 'name': 'Add selected item'}, {'id': 'R2', 'name': 'Save local order'}]
    correct = {'checks': [add, checkout], 'requirements': requirements, 'unverified': [], 'unverifiedCore': []}
    wrong = copy.deepcopy(correct)
    wrong['checks'][1]['steps'][1]['target']['name'] = 'Full name'
    regressed = copy.deepcopy(correct)
    del regressed['checks'][0]['steps'][0]['target']['withinText']
    class Provider:
        def __init__(self): self.calls = []
        def generate(self, messages, *_):
            self.calls.append(messages)
            assert messages[0]['content'].startswith('You are a browser verification planner.')
            assert len(self.calls) <= 2, 'Successful scope must survive the form-label repair'
            return SimpleNamespace(text=json.dumps([wrong, regressed][len(self.calls)-1]))
    provider = Provider()
    contract = {'requirements': [dict(item, scope='browser', acceptance=item['name']) for item in requirements]}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}')
                result = verify_functions(page, 'Add selected item and save local order', provider, contract=contract)
                assert not result['issues'] and not result['unverifiedCore'], result
                assert result['coverage']['passedIds'] == ['R1', 'R2']
                assert result['_verifiedPlan']['checks'][0]['steps'][0]['target']['withinText'] == 'Item A'
                assert 'Previous executable plan' in provider.calls[1][0]['content']
                assert 'Item A' in provider.calls[1][0]['content']
            finally: browser.close()
    finally: server.shutdown()
