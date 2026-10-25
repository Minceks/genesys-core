import json
from types import SimpleNamespace

import pytest

from agent.experience_blueprint import experience_blueprint
from agent.build_spec import prepare_build_spec
from agent.parallel_build import review_draft
from tests.test_visual_system import Workspace, prepare


@pytest.mark.parametrize('product,prompt,family', [
    ('store','Build a shop','commerce'),
    ('portfolio','A photographer portfolio','portfolio'),
    ('website','A salon appointment booking website','booking'),
    ('app','A reservation application','booking'),
    ('dashboard','An analytics dashboard','dashboard'),
    ('website','A magazine with articles','editorial'),
    ('website','A documentation knowledge base','documentation'),
    ('website','A local architecture company website','business'),
    ('app','A personal task tracker application','application'),
    ('game','A playable platformer game','game'),
])
def test_every_product_gets_a_complete_purpose_specific_journey(product, prompt, family):
    blueprint = experience_blueprint({'productType':product,'originalRequest':prompt})
    assert blueprint['family'] == family
    assert len(blueprint['journey']) == 4
    assert len(blueprint['capabilities']) == 4
    assert blueprint['visual'] and blueprint['visualReview']
    architecture = blueprint['productArchitecture']
    assert len(architecture['destinations']) == 4
    assert 'single page' in architecture['planning']
    assert 'Targeted repairs preserve existing scope' in architecture['planning']
    assert 'reload correctly' in architecture['navigation']
    assert 'Targeted repairs keep their scope' in blueprint['selectionPolicy']
    assert 'not remote synchronization' in blueprint['integrationPolicy']


def test_portfolio_identity_is_preserved_when_latest_repair_mentions_booking():
    blueprint = experience_blueprint({'productType':'portfolio','originalRequest':'Photographer portfolio','latestRequest':'Fix the booking link'})
    assert blueprint['family'] == 'portfolio'
    assert not any('cart' in item.lower() for item in blueprint['capabilities'])
    editorial = experience_blueprint({'productType':'website','originalRequest':'The best games this year','designResearch':{'family':'gaming-editorial'}})
    assert editorial['family'] == 'editorial'


def test_destination_map_preserves_product_purpose_without_forcing_a_marketing_template():
    def destinations(product, prompt):
        return experience_blueprint({'productType': product, 'originalRequest': prompt})['productArchitecture']['destinations']
    assert 'Complete project case study' in destinations('portfolio', 'Photographer portfolio')
    assert 'Substantial product detail' in destinations('store', 'A store')
    assert 'Complete article' in destinations('website', 'A magazine')
    assert 'Playable scene' in destinations('game', 'A platformer')
    assert 'Record exploration' in destinations('dashboard', 'Analytics')
    assert not any('checkout' in view.lower() for view in destinations('website', 'Architecture studio'))


def test_product_architecture_is_independent_between_builds():
    first = experience_blueprint({'productType': 'store'})
    first['productArchitecture']['destinations'].clear()
    assert len(experience_blueprint({'productType': 'store'})['productArchitecture']['destinations']) == 4


@pytest.mark.parametrize('prompt, geographic', [
    ('A hiking app with maps and trail points', True),
    ('A map of nearby businesses', True),
    ('Show a map at the user working location', True),
    ('Build a mind map editor', False),
    ('A website with a sitemap', False),
    ('Create a game map editor', False),
    ('Build a portfolio', False),
])
def test_geographic_maps_get_real_location_rules_without_affecting_abstract_maps(prompt, geographic):
    blueprint=experience_blueprint({'productType':'app','originalRequest':prompt})
    assert ('geographicMapPolicy' in blueprint) is geographic
    if geographic:
        assert 'actual latitude/longitude' in blueprint['geographicMapPolicy']['rendering']
        assert 'manual' in blueprint['geographicMapPolicy']['location']
        assert 'fabricated geographic routes' in blueprint['geographicMapPolicy']['data']


def test_credential_apps_do_not_inherit_ordinary_local_storage_as_a_security_claim():
    blueprint=experience_blueprint({'productType':'app','originalRequest':'Create application where users can save their passwords'})
    assert 'actual encrypted storage' in blueprint['sensitiveDataPolicy']
    assert 'not a security audit' in blueprint['sensitiveDataPolicy']


def test_saved_brief_frontloads_the_blueprint_and_preserves_it_on_a_repair(monkeypatch):
    workspace = Workspace()
    first = prepare(monkeypatch, workspace, 'Create a business website for an architecture studio')
    assert list(json.loads(workspace.content))[:2] == ['visualSystem','experienceBlueprint']
    second = prepare(monkeypatch, workspace, 'Fix the navigation focus state')
    assert first['experienceBlueprint'] == second['experienceBlueprint']
    assert second['experienceBlueprint']['family'] == 'business'


def test_specification_and_draft_review_receive_the_same_experience_blueprint():
    brief = {'productType':'portfolio','experienceBlueprint':experience_blueprint({'productType':'portfolio'})}
    observed = []
    class Files:
        def read_file(self, name): return {'content':'{}' if name.endswith('.json') else ''}
        def write_file(self, *_): return {'status':'success'}
    def specify(messages, _):
        assert 'direct entry/reload' in messages[0]['content']
        observed.append(json.loads(messages[1]['content'])['designBrief'])
        return SimpleNamespace(text=json.dumps({'pages':['Work'], 'requirements':[{'id':'R1','name':'Explore work','scope':'browser','acceptance':'Open an actual project and return to the work collection.'}]}))
    prepare_build_spec(Files(), 'Build a portfolio', brief, SimpleNamespace(generate=specify))
    def review(messages, _):
        assert 'productArchitecture.review' in messages[0]['content']
        observed.append(json.loads(messages[1]['content'])['design'])
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    review_draft({'src/App.jsx':'export default () => null'}, {}, json.dumps({'designBrief':brief}), SimpleNamespace(generate=review))
    assert all(item['experienceBlueprint'] == brief['experienceBlueprint'] for item in observed)
