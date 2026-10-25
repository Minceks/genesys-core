import copy
import json
from types import SimpleNamespace

from agent import product_design
from agent.parallel_build import review_draft
from agent.visual_system import visual_system


class Workspace:
    project_id = 'design-test'
    content = ''

    def read_file(self, _):
        return {'status': 'success', 'content': self.content}

    def write_file(self, _, content):
        self.content = content
        return {'status': 'success'}


def prepare(monkeypatch, workspace, prompt):
    monkeypatch.setattr('agent.design_research.research_design',
                        lambda _, product: {'family': product, 'references': []})
    return product_design.prepare_design(workspace, prompt)


def test_selling_products_selects_store_and_preserves_art_direction_on_functional_edits(monkeypatch):
    workspace = Workspace()
    first = prepare(monkeypatch, workspace, 'Create a website that sells products for emergencies')
    assert first['productType'] == 'store'
    first['visualSystem']['palette']['tokens']['accent'] = '#123456'
    workspace.content = json.dumps(first)
    second = prepare(monkeypatch, workspace, 'Fix the cart quantity update')
    assert second['productType'] == 'store'
    assert second['visualSystem']['palette']['tokens']['accent'] == '#123456'
    assert list(json.loads(workspace.content))[0] == 'visualSystem'
    assert second['designExecution']['direction']==first['designExecution']['direction']
    assert second['designExecution']['desktopComposition']
    assert second['designExecution']['handoffEvidence']
    commerce = second['designExecution']['commerceExperience']
    assert 'sorting' in commerce['discovery']
    assert 'order history' in commerce['purchaseContinuity']
    assert 'targeted repair' in commerce['scope']


def test_redesign_updates_composition_without_losing_product_purpose(monkeypatch):
    workspace = Workspace()
    first = prepare(monkeypatch, workspace, 'Build an online shop')
    previous = copy.deepcopy(first)
    second = prepare(monkeypatch, workspace, 'Redesign with a dark modern look')
    assert second['productType'] == 'store'
    assert second['visualSystem']['palette']['name'] == 'dark'
    assert second['visualSystem']['layout']['geometry'] != previous['visualSystem']['layout']['geometry']


def test_workspaces_do_not_get_marketing_hero_scale():
    strategy = {'direction': 'workspace', 'composition': 'Task canvas'}
    public = visual_system('a', 'website', '', strategy)
    app = visual_system('a', 'dashboard', '', strategy)
    assert public['type']['hero'] != app['type']['hero']
    assert visual_system('a', 'dashboard', '', strategy) == app


def test_latest_redesign_preference_overrides_previous_dark_theme(monkeypatch):
    workspace = Workspace()
    prepare(monkeypatch, workspace, 'Build a dark ecommerce store')
    redesigned = prepare(monkeypatch, workspace, 'Redesign with a light monochrome look')
    assert redesigned['visualSystem']['palette']['name'] == 'monochrome'


def test_review_receives_visual_system_even_when_source_tail_is_large():
    design = {'visualSystem': {'palette': 'existing user brand'}, 'integrationPolicy': {'payments': 'deferred'}}
    source = json.dumps({'designBrief': design, 'files': {'src/App.jsx': 'x' * 10000}})
    requests = []
    def generate(messages, _):
        requests.append(json.loads(messages[1]['content']))
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    assert review_draft({'src/App.jsx': 'export default () => null'}, {}, source,
                        SimpleNamespace(generate=generate))
    assert requests[0]['design'] == design
