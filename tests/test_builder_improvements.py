from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from agent.build_metrics import BuildMetrics, current, record_repair
from agent.edit_scope import focused_edit
from agent.visual_evidence import save_review, latest_reviews, image_path
from tests.test_user_auth import authenticated_backend, PROJECT


@pytest.mark.parametrize('prompt', ['Change the header font size', 'Make button padding smaller', 'Update the headline text'])
def test_small_visual_edits_are_focused(prompt):
    assert focused_edit(prompt)


@pytest.mark.parametrize('prompt', ['Build a dashboard', 'Fix the header menu logic', 'Create a new footer component', 'Change checkout to use real payments', 'Redesign the website'])
def test_features_and_behavior_repairs_keep_full_tools(prompt):
    assert not focused_edit(prompt)


def test_metrics_include_parallel_responses_without_leaking_context():
    metrics = BuildMetrics()
    token = current.set(metrics)
    try:
        def record():
            current.get().record(SimpleNamespace(usage=SimpleNamespace(total_tokens=25)))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(copy_context().run, record) for _ in range(8)]
            for future in futures: future.result()
        assert metrics.summary({'modifiedFiles': ['a']})['reportedTokens'] == 200
        assert metrics.summary({})['modelResponses'] == 8
    finally:
        current.reset(token)
    assert current.get() is None


def test_repair_metrics_survive_incomplete_verification_without_self_healing_field():
    metrics = BuildMetrics()
    token = current.set(metrics)
    try:
        record_repair()
        assert metrics.summary({'status': 'error'})['repairAttempts'] == 1
        assert metrics.summary({'selfHealing': {'attempts': 1}})['repairAttempts'] == 1
    finally:
        current.reset(token)
    record_repair()  # Requests without metrics remain supported.


def test_reviews_retain_ten_versions_and_keep_project_files_isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'reviews.sqlite3'))
    monkeypatch.setenv('GENESYS_VISUAL_EVIDENCE_DIR', str(tmp_path / 'images'))
    quality = {'status': 'success', 'snapshots': [{'width': 390}], 'suggestions': ['Readable type']}
    first = save_review('project-a', quality, {'desktop': b'png', 'phone': b'png'})
    for _ in range(10): save_review('project-a', quality, {'desktop': b'png', 'phone': b'png'})
    assert len(latest_reviews('project-a')) == 10
    assert not latest_reviews('project-b')
    assert image_path('project-a', first['id'], 'phone') is None
    latest = latest_reviews('project-a')[0]
    assert image_path('project-a', latest['id'], 'phone').read_bytes() == b'png'
    assert image_path('project-b', latest['id'], 'phone') is None
    assert image_path('project-a', '../outside', 'phone') is None


def test_review_routes_require_the_project_owner(authenticated_backend, monkeypatch, tmp_path):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'reviews.sqlite3'))
    monkeypatch.setenv('GENESYS_VISUAL_EVIDENCE_DIR', str(tmp_path / 'images'))
    review = save_review(PROJECT, {'status': 'success', 'snapshots': []}, {'desktop': b'png', 'phone': b'png'})
    for path in ('/builder/reviews', '/builder/reviews/' + review['id'] + '/phone'):
        assert authenticated_backend.get(path + '?projectId=' + PROJECT, headers={'Authorization': 'Bearer other'}).status_code == 404
        assert authenticated_backend.get(path + '?projectId=' + PROJECT, headers={'Authorization': 'Bearer owner'}).status_code == 200
