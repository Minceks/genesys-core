import json
from types import SimpleNamespace
import pytest
from agent.parallel_build import review_draft


class Provider:
    def __init__(self, verdict):
        self.verdict = verdict
    def generate(self, *args):
        return SimpleNamespace(text=json.dumps(self.verdict))


def test_review_can_correct_only_owned_files():
    files = {'src/App.jsx': 'old UI', 'src/projectLogic.js': 'working logic'}
    result = review_draft(files, {}, '', Provider({'valid': True,
        'issues': ['Wrong payload key'], 'files': {'src/App.jsx': 'corrected UI'}}))
    assert result['src/App.jsx'] == 'corrected UI'
    assert result['src/projectLogic.js'] == 'working logic'


@pytest.mark.parametrize('verdict', [
    {'valid': False, 'issues': ['Broken action'], 'files': {}},
    {'valid': True, 'issues': ['Broken action'], 'files': {}},
    {'valid': True, 'issues': [], 'files': {'package.json': '{}'}},
])
def test_unresolved_or_unowned_corrections_are_rejected(verdict):
    with pytest.raises(ValueError):
        review_draft({'src/App.jsx': 'UI'}, {}, '', Provider(verdict))
