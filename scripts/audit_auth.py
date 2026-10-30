import base64,json,time,threading
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlsplit,parse_qs
from dotenv import dotenv_values
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from frontend_host import create_app
root=Path(__file__).resolve().parents[1];conf=dotenv_values(root/'.env');host=urlsplit(conf['VITE_SUPABASE_URL']).hostname
(root/'.verification-evidence').mkdir(exist_ok=True)
user={'id':'10000000-0000-4000-8000-000000000001','email':'fixture@example.test','aud':'authenticated','role':'authenticated','created_at':'2026-01-01T00:00:00Z'}
enc=lambda x:base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=')
token=enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'sub':user['id'],'aud':'authenticated','role':'authenticated','exp':int(time.time())+3600})+'.fixture'
session={'access_token':token,'refresh_token':'fixture','expires_in':3600,'token_type':'bearer','user':user}
server=make_server('127.0.0.1',0,create_app(root.parent/'railway-frontend-deploy'/'dist'));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in [390,1440]:
   context=browser.new_context(viewport={'width':width,'height':1000});page=context.new_page();errors=[];calls=[];success=[False]
   page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    u=urlsplit(r.request.url)
    if u.hostname=='127.0.0.1':r.continue_();return
    assert u.hostname==host,'Unexpected external request'
    calls.append((u.path,r.request.post_data or ''))
    headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}
    if r.request.method=='OPTIONS':r.fulfill(status=200,headers=headers);return
    if u.path.endswith('/token'):
     if success[0]:r.fulfill(status=200,json=session,headers=headers)
     else:r.fulfill(status=400,json={'code':'invalid_credentials','msg':'Invalid login credentials'},headers=headers)
    elif u.path.endswith('/signup'):r.fulfill(status=200,json=user,headers=headers)
    elif u.path.endswith('/recover'):r.fulfill(status=200,json={},headers=headers)
    elif u.path.endswith('/user'):r.fulfill(status=200,json=user,headers=headers)
    elif u.path.endswith('/authorize'):
     assert parse_qs(u.query)['provider']==['google']
     assert parse_qs(u.query)['redirect_to']==[base+'/auth']
     r.fulfill(status=200,content_type='text/html',body='<h1>Mock Google authorization</h1>',headers=headers)
    else:r.fulfill(status=200,json=[],headers=headers)
   context.route('**/*',route)
   page.goto(base+'/auth',wait_until='networkidle')
   expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
   page.screenshot(path=f'.verification-evidence/auth-page-{width}.png',full_page=True)
   page.get_by_label('Email',exact=True).fill('fixture@example.test');page.get_by_label('Password',exact=True).fill('short6')
   page.get_by_role('button',name='Sign in',exact=True).click();expect(page.get_by_role('status')).to_contain_text('Invalid login credentials')
   assert any(path.endswith('/token') for path,_ in calls),'Existing short password was blocked by browser validation'
   page.get_by_role('button',name='Create account',exact=True).click();expect(page.get_by_label('Password',exact=True)).to_have_attribute('minlength','8')
   expect(page.get_by_role('status')).to_have_count(0)
   page.get_by_label('Password',exact=True).fill('fixture-password');page.get_by_role('button',name='Create account',exact=True).click();expect(page.get_by_role('status')).to_contain_text('Check your email')
   page.get_by_role('button',name='Back to sign in').click();page.get_by_role('button',name='Forgot password?').click()
   expect(page.get_by_label('Password',exact=True)).to_have_count(0)
   page.get_by_role('button',name='Send reset email').click();expect(page.get_by_role('status')).to_contain_text('If that address has an account')
   page.get_by_role('button',name='Back to sign in').click();page.get_by_role('button',name='Continue with Google').click();expect(page.get_by_role('heading',name='Mock Google authorization')).to_be_visible()
   page.goto(base+'/auth#error=access_denied&error_description=Authorization%20cancelled');expect(page.get_by_role('status')).to_contain_text('Authorization cancelled')
   page.get_by_label('Email',exact=True).fill('fixture@example.test');page.get_by_label('Password',exact=True).fill('short6');success[0]=True
   page.get_by_role('button',name='Sign in',exact=True).click();expect(page.get_by_role('heading',name='Your workspace',exact=True)).to_be_visible(timeout=15000)
   page.goto(base+'/reset-password#error=access_denied&error_description=Expired')
   expect(page.get_by_label('Email address',exact=True)).to_be_visible()
   page.goto(base+'/reset-password#access_token='+token+'&refresh_token=fixture&expires_in=3600&token_type=bearer&type=recovery')
   page.reload(wait_until='networkidle')  # Reset links open a new document from email.
   expect(page.get_by_role('heading',name='Choose a new password',exact=True)).to_be_visible()
   page.get_by_label('New password',exact=True).fill('new-fixture-password')
   page.get_by_label('Confirm new password',exact=True).fill('different-fixture-password')
   page.get_by_role('button',name='Update password',exact=True).click()
   expect(page.get_by_role('status')).to_contain_text('Passwords do not match')
   page.get_by_label('Confirm new password',exact=True).fill('new-fixture-password')
   page.get_by_role('button',name='Update password',exact=True).click()
   expect(page.get_by_role('heading',name='Password updated',exact=True)).to_be_visible()
   page.goto(base+'/',wait_until='networkidle')
   expect(page).to_have_url(base+'/')  # Ordinary cached sign-in is not recovery.
   page.goto(base+'/#access_token='+token+'&refresh_token=fixture&expires_in=3600&token_type=bearer&type=recovery')
   page.reload(wait_until='networkidle')
   expect(page).to_have_url(base+'/reset-password')
   expect(page.get_by_role('heading',name='Choose a new password',exact=True)).to_be_visible()
   assert not errors,errors
   print('PASS auth',width,'px: errors, existing short password, signup, reset, OAuth redirect/callback, successful workspace navigation; all network responses mocked')
   context.close()
  browser.close()
finally:server.shutdown()
