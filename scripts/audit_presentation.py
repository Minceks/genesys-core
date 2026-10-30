"""Capture the real frontend release at phone, tablet and desktop widths."""
from pathlib import Path
import sys,threading,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from frontend_host import create_app

root=Path(__file__).resolve().parents[1]
out=root/'.verification-evidence/genesys-presentation-oct19'
out.mkdir(exist_ok=True)
server=make_server('127.0.0.1',0,create_app(root.parent/'railway-frontend-deploy/dist'))
threading.Thread(target=server.serve_forever,daemon=True).start()
rows=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (320,390,768,1440):
   context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
   context.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
   page=context.new_page();errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')
   expect(page.get_by_role('heading',level=1)).to_contain_text('bring to life?')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
   expect(page.get_by_role('button',name='Start building your idea')).to_be_disabled()
   for name in ['A beautiful storefront','My creative portfolio','An appointment app','A team dashboard']:
    page.get_by_role('button',name=name,exact=True).click()
    assert page.get_by_role('textbox',name='Describe your project').input_value()
   page.get_by_role('textbox',name='Describe your project').fill('')
   page.locator('body').click(position={'x':5,'y':5})
   page.screenshot(path=str(out/f'home-{width}.png'),full_page=True,animations='disabled')
   assert not errors,errors
   rows.append({'width':width,'overflow':False,'runtimeErrors':errors,'suggestionsWork':True})
   context.close()
  browser.close()
finally:server.shutdown()
(out/'results.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
