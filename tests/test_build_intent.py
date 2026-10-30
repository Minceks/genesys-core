import pytest
from agent.build_intent import replaces_product
from tests.test_visual_system import Workspace, prepare


@pytest.mark.parametrize('prompt', [
    'create a website that can build websites', 'Please build a new photography website',
    'Can you make an appointment app', 'Replace this website with a portfolio',
    'Rebuild the entire website',
])
def test_whole_product_requests(prompt):
    assert replaces_product(prompt)


@pytest.mark.parametrize('prompt', [
    'Fix the cart', 'Make the website faster', 'Create a contact form',
    'Build a website header', 'Redesign with a dark look',
    'How do I create a website?', 'Add a dashboard to this app',
])
def test_edits_preserve_existing_product(prompt):
    assert not replaces_product(prompt)


def test_same_type_rebuild_replaces_old_brief_but_edits_retain_it(monkeypatch):
    workspace = Workspace()
    original = prepare(monkeypatch, workspace, 'Create a website for emergency preparedness')
    replacement = prepare(monkeypatch, workspace, 'Create a website that can build websites')
    assert replacement['buildIntent'] == 'replace-product'
    assert replacement['originalRequest'] == 'Create a website that can build websites'
    assert 'preparedness' not in replacement['originalRequest']
    assert 'THIS project' in replacement['designPolicy']
    edited = prepare(monkeypatch, workspace, 'Fix the preview button')
    assert edited['buildIntent'] == 'edit-product'
    assert edited['originalRequest'] == replacement['originalRequest']
    assert edited['visualSystem'] == replacement['visualSystem']


def test_large_saved_brief_is_not_mistaken_for_a_new_project(monkeypatch):
    import json
    from types import SimpleNamespace
    workspace=Workspace()
    original=prepare(monkeypatch,workspace,'Create a website for an architecture studio')
    original['largeEvidence']='x'*51000
    workspace.content=json.dumps(original)
    workspace.read_file=lambda _: {'status':'success','content':workspace.content[:50000],'truncated':True}
    workspace.sandbox=SimpleNamespace(fs=SimpleNamespace(download_file=lambda _:workspace.content.encode()))
    edited=prepare(monkeypatch,workspace,'Fix the footer spacing')
    assert edited['buildIntent']=='edit-product'
    assert edited['originalRequest']==original['originalRequest']
