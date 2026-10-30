import json
from types import SimpleNamespace

import pytest

from agent.parallel_build import review_draft


def test_reviewer_sees_existing_helpers_but_cannot_modify_them():
    files = {'src/App.jsx': 'UI'}
    helper = {'src/usePersistentState.js': 'export function usePersistentState() {}'}
    source = json.dumps({'files': {**helper, 'src/App.jsx': 'stale UI'}})

    class Provider:
        def generate(self, messages, tools):
            context = json.loads(messages[-1]['content'])
            assert context['existingFiles'] == helper
            assert context['files'] == files
            return SimpleNamespace(text=json.dumps({'valid': True, 'issues': [], 'files': helper}))

    with pytest.raises(ValueError, match='ownership'):
        review_draft(files, {}, source, Provider())
