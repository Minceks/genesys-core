import json
from types import SimpleNamespace

import pytest

from agent.functional_verification import target, verify_functions


class Locator:
    def inner_text(self):
        return 'Counter 0 Increase Reset'

    def evaluate_all(self, script):
        return []


class Page:
    def __init__(self):
        self.mutations = 0
        self.names = []

    def locator(self, selector):
        return Locator()

    def evaluate(self, script, *args):
        return {'local': {}, 'session': {}}

    def get_by_role(self, role, **kwargs):
        self.names.append(kwargs['name'])
        return Locator()

    def route(self, *args):
        self.mutations += 1


class Provider:
    def __init__(self, plan):
        self.plan = plan
        self.calls = 0

    def generate(self, *args):
        self.calls += 1
        return SimpleNamespace(text=json.dumps(self.plan))


def test_empty_selector_is_a_plan_error():
    with pytest.raises(ValueError, match='Invalid verification plan'):
        target(Page(), {'by': 'text', 'name': '   '})


def test_accessible_name_whitespace_is_normalized():
    page = Page()
    target(page, {'by': 'role', 'role': 'button', 'name': 'Sample\n  content'})
    assert page.names == ['Sample content']


def test_missing_requirement_coverage_never_mutates_app():
    page = Page()
    provider = Provider({'checks': [], 'unverified': [], 'unverifiedCore': []})
    result = verify_functions(page, 'Build a counter', provider)
    assert result['unverifiedCore']
    assert not result['issues']
    assert page.mutations == 0
    assert provider.calls == 2


def test_invalid_assertion_plan_never_mutates_app():
    page = Page()
    provider = Provider({'requirements': [{'id': 'counter', 'name': 'Increase count'}],
        'checks': [{'name': 'Increase', 'covers': ['counter'], 'steps': [
            {'action': 'absent', 'target': {'by': 'text', 'name': '   '}}]}]})
    result = verify_functions(page, 'Build a counter', provider)
    assert result['unverifiedCore']
    assert not result['issues']
    assert page.mutations == 0


def test_malformed_coverage_is_a_verifier_error():
    page = Page()
    provider = Provider({'requirements': [{'id': 'counter', 'name': 'Increase count'}],
        'checks': [{'name': 'Increase', 'covers': [{}], 'steps': [
            {'action': 'visible', 'target': {'by': 'text', 'name': '1'}}]}]})
    result = verify_functions(page, 'Build a counter', provider)
    assert result['unverifiedCore']
    assert not result['issues']
    assert page.mutations == 0


def test_duplicate_requirement_ids_cannot_claim_complete_coverage():
    page = Page()
    provider = Provider({'requirements': [
        {'id': 'counter', 'name': 'Increase count'},
        {'id': 'counter', 'name': 'Reset count'}], 'checks': []})
    result = verify_functions(page, 'Build a counter with reset', provider)
    assert result['unverifiedCore']
    assert page.mutations == 0
