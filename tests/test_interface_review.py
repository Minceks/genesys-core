import json
from types import SimpleNamespace
import pytest
from agent.parallel_build import review_draft, normalize_owned_files


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


def test_bare_file_names_map_only_to_assigned_paths():
    assert normalize_owned_files({'App.jsx': 'UI', './src/styles.css': 'CSS'},
        ['src/App.jsx', 'src/styles.css']) == {'src/App.jsx': 'UI', 'src/styles.css': 'CSS'}
    with pytest.raises(ValueError):
        normalize_owned_files({'../App.jsx': 'UI'}, ['src/App.jsx'])


@pytest.mark.parametrize('verdict', [
    {'valid': False, 'issues': ['Broken action'], 'files': {}},
    {'valid': True, 'issues': ['Broken action'], 'files': {}},
    {'valid': True, 'issues': [], 'files': {'package.json': '{}'}},
])
def test_unresolved_or_unowned_corrections_are_rejected(verdict):
    with pytest.raises(ValueError):
        review_draft({'src/App.jsx': 'UI'}, {}, '', Provider(verdict))
