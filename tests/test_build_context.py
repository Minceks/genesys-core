from agent.build_context import InspectionCache, initial_source_context
from agent.project_intelligence import scan_project


class Workspace:
    def __init__(self):
        self.reads = []
        self.listings = 0

    def read_file(self, path):
        self.reads.append(path)
        return {'status': 'success', 'content': 'export default function App() {}', 'truncated': False}

    def list_files(self):
        self.listings += 1
        return {'status': 'success', 'files': []}


def test_scan_reuses_existing_file_listing():
    workspace = Workspace()
    scan_project(InspectionCache(workspace), files=[])
    assert workspace.listings == 0


def test_cache_reuses_reads_and_provides_complete_source():
    workspace = Workspace()
    cache = InspectionCache(workspace)
    cache.read_file('src/App.jsx')
    context = initial_source_context(cache, ['.genesys-user-project', 'src/App.jsx'], ['src/App.jsx'])
    assert workspace.reads == ['src/App.jsx']
    assert 'export default function App() {}' in context
    assert 'Do not read them again' in context


def test_partial_source_is_not_presented_as_complete():
    workspace = Workspace()
    cache = InspectionCache(workspace)
    cache.reads['src/App.jsx'] = {'status': 'success', 'content': 'partial', 'truncated': True}
    assert not initial_source_context(cache, ['src/App.jsx'], ['src/App.jsx'])


def test_large_files_are_not_added_to_prompt():
    cache = InspectionCache(Workspace())
    cache.reads['src/App.jsx'] = {'status': 'success', 'content': 'x' * 7000, 'truncated': False}
    assert not initial_source_context(cache, ['src/App.jsx'], ['src/App.jsx'])
