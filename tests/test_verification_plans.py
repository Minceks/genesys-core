import json
from types import SimpleNamespace

import pytest

from agent.functional_verification import target, verify_functions
from agent import functional_verification


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


def test_invalid_planning_json_is_retried_without_app_mutation():
    class MalformedProvider:
        calls = 0
        def generate(self, *args):
            self.calls += 1
            return SimpleNamespace(text='{"checks": [' if self.calls == 1 else
                                   '{"checks":[],"requirements":[]}')
    page = Page()
    provider = MalformedProvider()
    result = verify_functions(page, 'Build a counter', provider)
    assert provider.calls == 3
    assert page.mutations == 0
    assert result['unverifiedCore']


def test_accessible_name_whitespace_is_normalized():
    page = Page()
    target(page, {'by': 'role', 'role': 'button', 'name': 'Sample\n  content'})
    assert page.names == ['Sample content']


def test_visual_evidence_never_substitutes_for_function_checks():
    evidence = ['Visible header logo and configured favicon.',
                'Desktop and phone: measured layout.']
    assert functional_verification.independently_checked('Provide a favicon', evidence)
    assert functional_verification.independently_checked('Responsive phone layout', evidence)
    assert not functional_verification.independently_checked('Save an uploaded logo', evidence)
    assert not functional_verification.independently_checked('Mobile booking validation', evidence)


def test_repeated_buttons_can_be_scoped_to_navigation():
    result = object()
    class Navigation:
        def is_visible(self):
            return True
        def get_by_role(self, role, **kwargs):
            assert role == 'button' and kwargs['name'] == 'Book'
            return result
    class Candidates:
        def count(self):
            return 1
        def nth(self, index):
            return Navigation()
    class ScopedPage:
        def get_by_role(self, role, **kwargs):
            assert role == 'navigation' and kwargs['name'] == 'Primary'
            return Candidates()
    assert target(ScopedPage(), {'by': 'role', 'role': 'button', 'name': 'Book',
        'withinRole': {'role': 'navigation', 'name': 'Primary'}}) is result


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


def test_diagnosis_cannot_clear_an_unexecuted_check(monkeypatch):
    class TestPage(Page):
        def unroute(self, *args):
            pass

        def get_by_role(self, *args, **kwargs):
            return SimpleNamespace(count=lambda: 0)

    class CheckLocator:
        first = None

        def count(self):
            return 1

        def nth(self, index):
            return self

        def is_visible(self):
            return True

    def locate(page, spec):
        if spec['name'] == 'Delete':
            raise ValueError('Invalid verification plan: ambiguous target')
        locator = CheckLocator()
        locator.first = locator
        return locator

    plan = {'requirements': [{'id': 'games', 'name': 'Manage games'}],
            'checks': [
                {'name': 'Show games', 'covers': ['games'], 'steps': [
                    {'action': 'visible', 'target': {'by': 'text', 'name': 'Games'}}]},
                {'name': 'Delete game', 'covers': ['games'], 'steps': [
                    {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Delete'}},
                    {'action': 'absent', 'target': {'by': 'text', 'name': 'Game'}}]}]}

    class DiagnosingProvider(Provider):
        def generate(self, *args):
            self.calls += 1
            value = plan if self.calls == 1 else {
                'kind': 'application_failure', 'evidence': 'Speculative source diagnosis',
                'requiredUnverified': []}
            return SimpleNamespace(text=json.dumps(value))

    monkeypatch.setattr(functional_verification, 'target', locate)
    monkeypatch.setattr('playwright.sync_api.expect', lambda locator:
                        SimpleNamespace(to_be_attached=lambda **kwargs: None))
    result = verify_functions(TestPage(), 'Show and delete games', DiagnosingProvider(plan), attempt=1)
    assert result['testedInteractions'] == ['Show games']
    assert result['unverifiedCore']
    assert result['coverage']['passedIds'] == []
    assert result['coverage']['unverified'] == ['Manage games']
    assert not result['issues']  # Planner failure must not trigger app edits.
