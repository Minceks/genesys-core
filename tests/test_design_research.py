import json

from agent import design_research, product_design


def test_gaming_website_uses_editorial_references():
    assert design_research.reference_family('Website for best games of the year', 'website') == 'gaming-editorial'
    assert design_research.reference_family('Create a playable game', 'game') == 'product'
    assert design_research.reference_family('Appointment booking app', 'app') == 'booking'


def test_page_signals_are_bounded():
    parser = design_research.PageSignals()
    parser.feed('<title>Studio</title><meta name="description" content="Photography"><h1>Selected work</h1>')
    assert parser.title == 'Studio'
    assert parser.description == 'Photography'
    assert parser.headings == ['Selected work']


def test_reference_failures_do_not_stop_build(monkeypatch):
    def unavailable(*args, **kwargs):
        raise design_research.httpx.ConnectError('Unavailable')
    monkeypatch.setattr(design_research.httpx, 'stream', unavailable)
    monkeypatch.setattr(design_research, '_cache', {})
    result = design_research.research_design('Photography portfolio', 'portfolio')
    assert all(item['status'] == 'unavailable' for item in result['references'])


def test_retries_reuse_saved_research_and_redesign_refreshes_it(monkeypatch):
    calls = []
    def research(prompt, product):
        calls.append(prompt)
        return {'family': 'gaming-editorial', 'references': []}
    monkeypatch.setattr(design_research, 'research_design', research)

    class Workspace:
        content = ''
        def read_file(self, path):
            return {'status': 'success', 'content': self.content}
        def write_file(self, path, content):
            self.content = content
            return {'status': 'success'}

    workspace = Workspace()
    prompt = 'Create a website for the best games of the year'
    first = product_design.prepare_design(workspace, prompt)
    product_design.prepare_design(workspace, prompt)
    assert len(calls) == 1
    assert 'gaming editorial' in first['visual']
    product_design.prepare_design(workspace, 'Redesign the website with a modern look')
    assert len(calls) == 2
    assert json.loads(workspace.content)['designResearch']
