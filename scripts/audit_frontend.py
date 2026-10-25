"""Isolated desktop/mobile route and function audit; all external services are mocked."""
import base64,json,time,threading,logging
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlsplit
from dotenv import dotenv_values
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from frontend_host import create_app
logging.getLogger('werkzeug').setLevel(logging.ERROR)
root=Path.cwd();conf=dotenv_values('.env');host=urlsplit(conf['VITE_SUPABASE_URL']).hostname
project='30000000-0000-4000-8000-000000000003';user={'id':'10000000-0000-4000-8000-000000000001','email':'fixture@example.test','aud':'authenticated','role':'authenticated','created_at':'2026-01-01T00:00:00Z'}
enc=lambda x:base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=')
token=enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'sub':user['id'],'aud':'authenticated','role':'authenticated','exp':int(time.time())+3600})+'.fixture'
session={'access_token':token,'refresh_token':'fixture','expires_at':int(time.time())+3600,'expires_in':3600,'token_type':'bearer','user':user}
record={'id':project,'name':'Audit project','created_at':'2026-01-01T00:00:00Z'}
server=make_server('127.0.0.1',0,create_app(root.parent/'railway-frontend-deploy'/'dist'));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}';results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in [390,1440]:
   for signed in [False,True]:
    context=browser.new_context(viewport={'width':width,'height':1000})
    if signed:context.add_init_script('localStorage.setItem('+json.dumps('sb-'+host.split('.')[0]+'-auth-token')+','+json.dumps(json.dumps(session))+')')
    state={'requests':[],'jobs':{},'controls':{'instructions':'Preserve working behavior','lockedPaths':[],'revision':1},'deny':False,'createError':False,'previewError':False,'publishError':True,'verificationFail':False,'reviewBlocked':False}
    errors=[];page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
     u=urlsplit(r.request.url)
     if u.hostname=='127.0.0.1':r.continue_();return
     state['requests'].append((r.request.method,u.path,r.request.post_data or ''))
     headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}
     def send(body,status=200):r.fulfill(status=status,json=body,headers=headers)
     if r.request.method=='OPTIONS':send({});return
     if u.hostname==host:
      if '/auth/v1/' in u.path:send(user if u.path.endswith('/user') else {});return
      if u.path.endswith('/projects'):
       if r.request.method=='POST':send({'message':'Fixture creation denied'},403) if state['createError'] else send(record);return
       if state['deny'] and 'id=eq.' in u.query:send({'message':'Not found'},406);return
       send(record if 'object+json' in r.request.headers.get('accept','') else [record]);return
     if u.hostname=='fixture-preview.example.test':r.fulfill(status=200,body='<h1>Audit preview</h1>',content_type='text/html');return
     if u.path=='/builder/controls':
      if r.request.method=='PUT':state['controls']={**json.loads(r.request.post_data),'revision':state['controls']['revision']+1}
      send(state['controls']);return
     if u.path=='/builder/reviews':send({'reviews':[]});return
     if u.path=='/list-files':send({'tree':{'routes':['src/App.jsx'],'components':[]}});return
     if u.path=='/preview':send({'message':'Fixture preview unavailable'},503) if state['previewError'] else send({'url':'https://fixture-preview.example.test/','running':True});return
     if u.path=='/publish/review':
      send({'status':'blocked' if state['reviewBlocked'] else 'needs_review','reviewHash':'fixture-release-review',
       'visualAssessment':'needs_polish' if state['reviewBlocked'] else 'unavailable',
       'blockers':['Phone form overlaps the primary action.'] if state['reviewBlocked'] else [],
       'acknowledgements':[
        {'id':'visual-content','label':'I reviewed this version’s desktop and phone layouts, content and imagery.','items':['Screenshot review is unavailable; inspect both layouts.']},
        {'id':'deferred-integrations','label':'I understand these integrations remain deferred and are not completed by publishing.','items':['External email delivery is deferred.']},
        {'id':'verification-scope','label':'I understand the limits of the checks performed on this version.','items':['Real multi-user behavior was not tested.']}]});return
     if u.path=='/publish':
      payload=json.loads(r.request.post_data)
      assert payload=={'projectId':project,'checkpointId':'genesys-checkpoint-fixture','promotionToken':'fixture-promotion-proof',
        'reviewHash':'fixture-release-review','acknowledgements':['visual-content','deferred-integrations','verification-scope']}
      send({'message':'Publishing is in testing for this account.'},503) if state['publishError'] else send({'url':'https://published.example.test/'})
      return
     if u.path=='/agent/jobs' and r.request.method=='POST':
      data=json.loads(r.request.post_data);job=f'{len(state["jobs"])+1:032x}';state['jobs'][job]=data;send({'jobId':job});return
     if u.path.startswith('/agent/jobs/'):
      job=state['jobs'][u.path.rsplit('/',1)[1]];mode=job.get('mode','build')
      response={'status':'success','mode':mode,'text':f'Audit {mode} complete.','buildPassed':mode=='build','browserVerified':mode=='build','previewUrl':'https://fixture-preview.example.test/','modifiedFiles':[]}
      if mode=='plan':response['proposedBuildPrompt']='Implement the reviewed audit plan'
      if mode=='build':
       response.update(checkpoint={'status':'success','checkpointId':'genesys-checkpoint-fixture'},promotionToken='fixture-promotion-proof')
       if state['verificationFail']:response.update(status='error',text='Audit build needs fixes.',browserVerified=False)
      send({'state':'completed','stage':'Complete','result':response});return
     raise AssertionError('Unhandled external request '+u.hostname+u.path)
    context.route('**/*',route)
    page.goto(base,wait_until='networkidle')
    page.get_by_role('button',name='A beautiful storefront',exact=True).click()
    idea=page.get_by_role('textbox',name='Describe your project').input_value()
    assert 'stationery store' in idea
    page.get_by_role('button',name='Start building your idea').click()
    if signed:
     expect(page.get_by_role('heading',name='Your workspace',exact=True)).to_be_visible()
     page.get_by_role('button',name='New project',exact=True).click()
     expect(page.get_by_role('textbox',name='Message Genesys')).to_have_value(idea)
     assert not state['jobs'],'Homepage handoff must not start a paid build automatically'
    else:
     expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
     assert page.evaluate('sessionStorage.getItem("genesys_starter_prompt")')==idea
     page.evaluate('sessionStorage.removeItem("genesys_starter_prompt")')
    for url in ['/','/pricing','/reset-password','/missing-route']:
     page.goto(base+url,wait_until='networkidle');expect(page.get_by_role('heading',level=1)).to_be_visible();assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2'),url
    for url in ['/account','/build','/dashboard','/lab','/store']:
     page.goto(base+url,wait_until='networkidle');expect(page.get_by_role('heading',name='Your workspace' if signed else 'Sign in',exact=True)).to_be_visible()
    if signed:
     page.get_by_role('button',name='New project',exact=True).click();expect(page.get_by_role('status')).to_contain_text('Project created')
     state['createError']=True;page.get_by_role('button',name='New project',exact=True).click();expect(page.get_by_role('status')).to_contain_text('Fixture creation denied');state['createError']=False
     page.get_by_role('button',name='Send password reset email').click();expect(page.get_by_role('status')).to_contain_text('Password reset email requested')
    page.goto(base+'/p/'+project,wait_until='networkidle')
    if not signed:expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
    else:
     expect(page.get_by_role('combobox',name='Builder mode')).to_be_visible();assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
     expect(page.locator('iframe')).to_have_attribute('src','https://fixture-preview.example.test/')
     assert any(path=='/preview' for _,path,_ in state['requests']), 'Saved preview must load automatically on project entry'
     if width<768:
      page.get_by_role('button',name='Open navigation',exact=True).click()
      expect(page.locator('#mobile-navigation').get_by_role('link',name='Pricing',exact=True)).to_be_visible()
      page.get_by_role('button',name='Close navigation',exact=True).click()
      expect(page.locator('#mobile-navigation')).to_have_count(0)
     page.get_by_text('AI instructions & frozen files',exact=True).click();page.get_by_label('Project AI instructions').fill('Keep the brand and cart');page.get_by_label('Frozen files or folders').fill('src/brand/')
     page.get_by_role('button',name='Save controls',exact=True).click();expect(page.get_by_role('status')).to_contain_text('AI controls saved')
     page.get_by_role('button',name='Reload controls').click();expect(page.get_by_label('Project AI instructions')).to_have_value('Keep the brand and cart')
     for mode in ['plan','discuss']:
      page.get_by_role('combobox',name='Builder mode').select_option(mode);page.locator('textarea').last.fill('Audit '+mode);page.get_by_role('button',name='Send request').click();expect(page.get_by_text('Audit '+mode+' complete.',exact=True)).to_be_visible()
     page.get_by_role('button',name='Build this plan').click();expect(page.get_by_text('Audit build complete.',exact=True)).to_be_visible()
     assert [j.get('mode') for j in state['jobs'].values()]==['plan','discuss','build']
     page.get_by_text('Publish website',exact=True).click()
     expect(page.get_by_role('dialog',name='Review and publish')).to_be_visible()
     page.keyboard.press('Escape')
     expect(page.get_by_role('dialog',name='Review and publish')).not_to_be_visible()
     page.get_by_text('Publish website',exact=True).click()
     expect(page.get_by_role('button',name='Publish verified version',exact=True)).to_be_disabled()
     assert not any(path=='/publish' for _,path,_ in state['requests'])
     expect(page.get_by_text('External email delivery is deferred.',exact=True)).to_be_visible()
     page.screenshot(path=str(root/'.verification-evidence'/'release-review-20261025'/f'review-{width}.png'),full_page=True)
     page.get_by_role('checkbox',name='I reviewed this version’s desktop and phone layouts, content and imagery.').check()
     expect(page.get_by_role('button',name='Publish verified version',exact=True)).to_be_disabled()
     page.get_by_role('checkbox',name='I understand these integrations remain deferred and are not completed by publishing.').check()
     page.get_by_role('checkbox',name='I understand the limits of the checks performed on this version.').check()
     page.get_by_role('button',name='Publish verified version',exact=True).click()
     expect(page.get_by_text('Publishing is in testing for this account.',exact=True)).to_be_visible()
     state['publishError']=False
     page.get_by_role('button',name='Publish verified version',exact=True).click()
     expect(page.get_by_role('link',name='Open published website',exact=True)).to_have_attribute('href','https://published.example.test/')
     state['reviewBlocked']=True
     page.get_by_role('button',name='Refresh release checks',exact=True).click()
     expect(page.get_by_text('Phone form overlaps the primary action.',exact=True)).to_be_visible()
     expect(page.get_by_role('button',name='Publish this version again',exact=True)).to_be_disabled()
     assert not page.get_by_role('checkbox').first.is_checked()
     page.get_by_role('button',name='Close publishing review').click()
     assert 'fixture-promotion-proof' not in page.evaluate('JSON.stringify(sessionStorage)+JSON.stringify(localStorage)')
     state['verificationFail']=True
     page.locator('textarea').last.fill('Audit failed verification')
     page.get_by_role('button',name='Send request').click()
     expect(page.get_by_text('Audit build needs fixes.',exact=True)).to_be_visible()
     page.get_by_text('Publish website',exact=True).click()
     expect(page.get_by_role('button',name='Publish verified version',exact=True)).to_have_count(0)
     page.get_by_role('button',name='Close publishing review').click()
     input_box=page.get_by_role('textbox',name='Message Genesys').bounding_box()
     assert input_box and input_box['y']>=0 and input_box['y']+input_box['height']<=1000,'Composer must remain visible with settings expanded'
     if width<1024:page.get_by_role('button',name='Preview',exact=True).click()
     else:
      page.get_by_role('button',name='Phone',exact=True).click()
      page.wait_for_function('document.querySelector("iframe")?.getBoundingClientRect().width<=391')
      expect(page.get_by_role('button',name='Phone',exact=True)).to_have_attribute('aria-pressed','true')
      page.get_by_role('button',name='Desktop',exact=True).click()
      page.wait_for_function('document.querySelector("iframe")?.getBoundingClientRect().width>390')
      expect(page.get_by_role('button',name='Desktop',exact=True)).to_have_attribute('aria-pressed','true')
     page.get_by_role('button',name='Reconnect preview',exact=True).click();expect(page.frame_locator('iframe').get_by_role('heading',name='Audit preview')).to_be_visible()
     page.screenshot(path=str(root/'.verification-evidence'/f'builder-polished-{width}.png'),full_page=True)
     state['previewError']=True;page.get_by_role('button',name='Reconnect preview',exact=True).click();expect(page.get_by_role('status')).to_contain_text('Fixture preview unavailable');state['previewError']=False
     completed_jobs=len(state['jobs'])
     page.reload(wait_until='networkidle');expect(page.locator('iframe')).to_have_attribute('src','https://fixture-preview.example.test/')
     assert len(state['jobs'])==completed_jobs, 'Reopening a project must not run a paid build'
     state['deny']=True;page.goto(base+'/build?projectId='+project,wait_until='networkidle');expect(page.get_by_role('status')).to_contain_text('Project not found or access denied');state['deny']=False
     page.goto(base+'/account',wait_until='networkidle');page.get_by_role('button',name='Sign out',exact=True).first.click();expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
    assert not errors,errors
    results.append({'width':width,'signedIn':signed,'passed':True});print('PASS route/function audit',width,'signed-in:',signed)
    context.close()
  browser.close()
 (root/'.verification-evidence').mkdir(exist_ok=True)
 (root/'.verification-evidence/functions-audit.json').write_text(json.dumps(results,indent=2))
finally:server.shutdown()
