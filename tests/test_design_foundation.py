import copy
import pytest
from agent.design_foundation import PATH, PLACEHOLDER, prepare_foundation, stylesheet
from agent.project_starter import STARTER_FILES
from agent.visual_system import visual_system


class Workspace:
    project_id='foundation-test'
    def __init__(self): self.files=copy.deepcopy(STARTER_FILES); self.writes=[]
    def read_file(self,path): return {'content':self.files[path]}
    def write_file(self,path,content):
        self.files[path]=content;self.writes.append(path)
        return {'status':'success'}


def test_generated_theme_preserves_overrides_and_existing_projects(monkeypatch):
    monkeypatch.setattr('agent.builder_controls.assert_writable',lambda *_:None)
    w=Workspace()
    system=visual_system('a','store','warm',{'direction':'premium'})
    record=prepare_foundation(w,system)
    assert '--background: '+system['palette']['tokens']['background'] in w.files[PATH]
    assert w.writes==[PATH] and '--font-display:' in w.files[PATH]
    assert prepare_foundation(w,system,{'designFoundation':record})==record
    assert w.writes==[PATH]  # Unchanged functional edits cause no theme write.
    w.files[PATH]+='\n:root{--accent:#123456}'
    custom=w.files[PATH]
    assert prepare_foundation(w,system,{'designFoundation':record})['status']=='user-managed'
    assert w.files[PATH]==custom
    w.files['src/main.jsx']="import './styles.css'"
    assert prepare_foundation(w,system) is None
    assert w.files[PATH]==custom


def test_frozen_theme_is_never_written(monkeypatch):
    def locked(*_): raise ValueError('Frozen file')
    monkeypatch.setattr('agent.builder_controls.assert_writable',locked)
    w=Workspace()
    result=prepare_foundation(w,visual_system('a','app','',{}))
    assert result['status']=='frozen' and not w.writes and w.files[PATH]==PLACEHOLDER


@pytest.mark.parametrize('product',['website','portfolio','store','dashboard','app','game'])
def test_each_product_gets_its_own_actual_tokens(product):
    system=visual_system('a',product,'cream and cobalt',{'direction':'editorial'})
    css=stylesheet(system)
    assert '--accent: #3057d5;' in css
    assert '--type-display: '+system['type']['hero'] in css
    assert '--page-width: '+system['layout']['maxWidth'] in css
    assert 'input[type=checkbox]' in css and 'focus-visible' in css


def test_css_fragments_are_not_inserted_as_token_values():
    system=visual_system('a','website','',{})
    system['type']['displayFamily']='serif; } body{display:none} /*'
    system['palette']['tokens']['accent']='#12345'
    css=stylesheet(system)
    assert 'display:none' not in css and '#12345' not in css
