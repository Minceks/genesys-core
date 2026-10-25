import pytest
import hashlib
import json
from types import SimpleNamespace
from agent.build_spec import validate_spec
from agent.build_spec import same_build_requirements
from agent.build_spec import prepare_build_spec


@pytest.mark.parametrize('acceptance', ['observable outcome', 'TBD', 'Expected outcome.',
                                        'concrete user action and its visible expected result'])
def test_placeholder_acceptance_is_rejected(acceptance):
    with pytest.raises(ValueError, match='placeholder'):
        validate_spec({'pages': ['Shop'], 'requirements': [
            {'id': 'R1', 'name': 'Cart persistence', 'scope': 'browser', 'acceptance': acceptance}]})


def test_concrete_acceptance_is_preserved():
    spec = {'pages': ['Shop'], 'requirements': [
        {'id': 'R1', 'name': 'Cart persistence', 'scope': 'browser',
         'acceptance': 'Add an item, reload, reopen cart and verify its quantity and total remain.'}]}
    assert validate_spec(spec) == spec


def test_changed_requirements_cannot_reuse_implementation_proof():
    previous = {'requirements': [{'id': 'R1', 'acceptance': 'Add item'}]}
    assert same_build_requirements(previous, dict(previous, version=2))
    assert not same_build_requirements(previous, {'requirements': [{'id': 'R1', 'acceptance': 'Add and persist item'}]})
    assert not same_build_requirements(None, previous)


def test_legacy_scope_is_reconciled_once_then_concrete_contract_is_reused():
    prompt = 'Build a shop'
    spec = {'pages': ['Shop'], 'requirements': [
        {'id': 'R1', 'name': 'Cart', 'scope': 'browser', 'acceptance': 'Add an item and verify it survives reload.'}]}
    class Workspace:
        saved = dict(spec, version=1, requestHash=hashlib.sha256(prompt.encode()).hexdigest())
        def read_file(self, name):
            return {'content': 'Existing working application' if name == 'src/App.jsx' else json.dumps(self.saved)}
        def write_file(self, name, content):
            self.saved = json.loads(content)
            return {'status': 'success'}
    class Provider:
        calls = 0
        def generate(self, messages, tools):
            self.calls += 1
            context = json.loads(messages[-1]['content'])
            assert context['existingImplementation'] == 'Existing working application'
            assert context['designBrief'] == {'productType': 'store'}
            return SimpleNamespace(text=json.dumps(spec))
    workspace, provider = Workspace(), Provider()
    brief = {'productType': 'store', 'suggestedFeatures': ['Invented account screen']}
    first = prepare_build_spec(workspace, prompt, brief, provider)
    assert first['version'] == 2
    assert prepare_build_spec(workspace, prompt, brief, provider) == first
    assert provider.calls == 1


@pytest.mark.parametrize('intent', ['replace-product', 'new-product'])
def test_replacement_discards_old_product_contract_even_when_request_hash_matches(intent):
    prompt = 'create a website that can build websites'
    new_spec = {'pages':['Builder'], 'requirements':[
        {'id':'R1','name':'Create and preview a page','scope':'browser',
         'acceptance':'Create a page, edit its heading and verify the preview shows the saved heading after reload.'}]}
    class Workspace:
        saved = {'version':2,'requestHash':hashlib.sha256(prompt.encode()).hexdigest(),
                 'pages':['Shop'],'requirements':[{'id':'OLD','name':'Cart','scope':'browser',
                 'acceptance':'Add an item to the cart and confirm the total.'}]}
        def read_file(self, name):
            return {'content':'OLD SHOP SOURCE' if name == 'src/App.jsx' else json.dumps(self.saved)}
        def write_file(self, name, content):
            self.saved=json.loads(content)
            return {'status':'success'}
    class Provider:
        calls=0
        def generate(self,messages,tools):
            self.calls+=1
            context=json.loads(messages[-1]['content'])
            assert context['existingImplementation']==''
            assert context['previousSpecification']=={}
            assert context['designBrief']['buildIntent']==intent
            assert context['designBrief']['originalRequest']==prompt
            return SimpleNamespace(text=json.dumps(new_spec))
    workspace,provider=Workspace(),Provider()
    brief={'buildIntent':intent,'originalRequest':prompt,'designPolicy':'Replace this product'}
    result=prepare_build_spec(workspace,prompt,brief,provider)
    assert result['requirements']==new_spec['requirements']
    assert result['replacementContractVersion']==1
    assert prepare_build_spec(workspace,prompt,brief,provider)==result
    assert provider.calls==1
