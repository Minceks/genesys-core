import json

from agent.build_context import InspectionCache,initial_source_context
from agent import project_memory as memory


class Workspace:
    def __init__(self,files):self.files=dict(files);self.reads=[];self.fingerprint='source-one'
    def read_file(self,path):
        self.reads.append(path)
        if path not in self.files:raise FileNotFoundError(path)
        return {'status':'success','content':self.files[path]}
    def write_file(self,path,content):self.files[path]=content;return {'status':'success'}
    def build_fingerprint(self):return self.fingerprint


FILES={
    'src/App.jsx':"import Checkout from './Checkout'; export default function App(){return <Checkout/>}",
    'src/Checkout.jsx':"import {useCart} from './cart'; import './checkout.css'; export default function Checkout(){const [orders,setOrders]=usePersistentState('orders-v1',[]);return <h1>Checkout</h1>}",
    'src/cart.js':"export function useCart(){return {quantity:2}}",
    'src/checkout.css':'h1 {font-size:40px}',
    'src/About.jsx':'export default function About(){return <p>About</p>}',
    '.env':'SECRET=must-not-be-read',
    'node_modules/lib/index.js':'must not be indexed',
}


def test_identifiers_stay_stable_when_source_and_inventory_order_change():
    w=Workspace(FILES);first=memory.refresh(InspectionCache(w),list(FILES),'Improve checkout',{})
    w.files['src/cart.js']='export function useCart(){return {quantity:3}}'
    second=memory.refresh(InspectionCache(w),list(reversed(FILES)),'Improve checkout',{})
    a={n['path']:n for n in first['nodes']};b={n['path']:n for n in second['nodes']}
    assert a['src/cart.js']['id']==b['src/cart.js']['id']
    assert a['src/cart.js']['digest']!=b['src/cart.js']['digest']
    assert a.keys()==b.keys()


def test_retrieval_finds_checkout_and_related_data_and_styles_without_claiming_runtime():
    w=Workspace(FILES);index=memory.refresh(InspectionCache(w),list(FILES),'Fix checkout',{})
    found=memory.retrieve(index,'Fix checkout',limit=4)
    assert found[0]['path']=='src/Checkout.jsx'
    assert {'src/cart.js','src/checkout.css'} <= {n['path'] for n in found}
    checkout=next(n for n in index['nodes'] if n['path']=='src/Checkout.jsx')
    assert checkout['storageKeys']==['orders-v1']
    assert len(index['links'])==3
    assert 'runtime proof' in memory.context(index,'checkout')


def test_secrets_and_generated_files_are_not_read_or_copied_into_memory():
    w=Workspace(FILES);index=memory.refresh(InspectionCache(w),list(FILES),'Read all files',{})
    assert '.env' not in w.reads and 'node_modules/lib/index.js' not in w.reads
    assert 'must-not-be-read' not in json.dumps(index)
    for path in ['../outside.py','/etc/passwords.md','src/../credentials.py','src/private.key','recovered/App.jsx']:
        assert not memory.eligible(path)


def test_memory_does_not_reuse_stale_source_or_deleted_files():
    w=Workspace(FILES);memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    del w.files['src/cart.js'];w.files['src/Checkout.jsx']='export default function Checkout(){return null}'
    index=memory.refresh(InspectionCache(w),list(w.files),'checkout',{})
    assert 'src/cart.js' not in {n['path'] for n in index['nodes']}
    assert not any(n.get('storageKeys') for n in index['nodes'])


def test_reads_are_bounded_and_cache_is_reused():
    w=Workspace({f'src/file{i}.js':f'export const item{i}=1' for i in range(80)})
    cache=InspectionCache(w);cache.read_file('src/file0.js');before=len(w.reads)
    index=memory.refresh(cache,list(w.files),'item',{})
    assert len(w.reads)-before<=13  # Twelve source reads plus the memory metadata read.
    assert w.reads.count('src/file0.js')==1
    assert len(index['nodes'])==80 and any(not n['indexed'] for n in index['nodes'])


def test_verified_receipt_is_source_bound_and_retains_limitations():
    w=Workspace(FILES);memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    memory.remember_verified(w,{'passed':['Save local order'],'deferred':['Real payments'],'manualReview':['Review imagery']})
    current=memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    assert current['lastVerification']['passed']==['Save local order']
    assert current['lastVerification']['deferred']==['Real payments']
    w.fingerprint='source-two'
    changed=memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    assert 'lastVerification' not in changed and 'historical' in changed['verificationStatus']


def test_targeted_source_precedes_generic_starter_files():
    files={f'src/other{i}.jsx':'export const x=1' for i in range(5)}
    files.update({'src/App.jsx':'export default function App(){}','src/styles.css':'body{}'})
    w=Workspace(files)
    value=initial_source_context(InspectionCache(w),['.genesys-user-project']+list(files),['src/other4.jsx'])
    assert value.index('FILE: src/other4.jsx')<value.index('FILE: src/App.jsx')


def test_discussion_uses_memory_to_select_current_source_without_reading_credentials(monkeypatch):
    from agent import builder_modes,daytona_workspace
    from types import SimpleNamespace
    w=Workspace(FILES);index=memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    index['nodes'].append({'id':memory.identity('.env'),'path':'.env','indexed':True})
    index['lastVerification']={'passed':['Stale payment claim']}
    files={memory.PATH:json.dumps(index),**FILES};files['src/Checkout.jsx']='export const currentCheckoutVersion=2'
    reads=[]
    def download(path):
        relative=path.removeprefix(daytona_workspace.REMOTE_PROJECT_ROOT+'/');reads.append(relative)
        if relative not in files:raise FileNotFoundError(relative)
        return files[relative].encode()
    monkeypatch.setattr(daytona_workspace,'get_daytona',lambda:SimpleNamespace(get=lambda _:SimpleNamespace(fs=SimpleNamespace(download_file=download))))
    result=builder_modes.read_project_context('project','How does checkout work?')
    assert 'currentCheckoutVersion=2' in result['src/Checkout.jsx']
    assert '.env' not in reads and 'Stale payment claim' not in json.dumps(result)
    assert 'not revalidated' in result[memory.PATH]


def test_incomplete_verification_cannot_be_remembered_as_passed():
    import pytest
    w=Workspace(FILES);memory.refresh(InspectionCache(w),list(FILES),'checkout',{})
    with pytest.raises(ValueError):memory.remember_verified(w,{'passed':['Layout'],'incomplete':['Checkout']})
    assert 'lastVerification' not in json.loads(w.files[memory.PATH])
