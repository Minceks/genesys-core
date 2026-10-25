from dataclasses import replace
import json

import pytest

from agent import release_review as release
from agent.promotion import sign_verified_checkpoint
from tests.test_user_auth import authenticated_backend, PROJECT

CHECKPOINT = 'genesys-checkpoint-123'
COMMIT = 'a' * 40
KEY = 'fixture-only-release-signing-key'


def evidence(visual='ready', **changes):
    value = {'buildPassed': True, 'browserVerified': True, 'buildFingerprint': 'build-one',
        'checkpoint': {'status': 'success', 'checkpointId': CHECKPOINT, 'commit': COMMIT},
        'verification': {'passed': ['Booking, reload and cancellation'], 'failed': [], 'incomplete': [],
            'manualReview': ['Review supplied imagery'], 'deferred': ['External email delivery'],
            'limitations': ['Real multi-user behavior was not tested.'],
            'visualReview': {'status': visual, 'sourceFingerprint': 'build-one', 'summary': 'Captured views reviewed.', 'findings': []}}}
    value.update(changes)
    return value


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'reviews.sqlite3'))


@pytest.fixture
def api(database, authenticated_backend, monkeypatch):
    import cloud_agent
    monkeypatch.setattr(cloud_agent, 'settings', replace(cloud_agent.settings, promotion_signing_key=KEY))
    monkeypatch.setattr(cloud_agent.jobs, 'is_running', lambda _: False)
    monkeypatch.setattr(cloud_agent, 'get_workspace', lambda _: pytest.fail('No workspace access before release review passes'))
    monkeypatch.setenv('GENESYS_PUBLISH_ENABLED', 'true')
    return authenticated_backend


def candidate():
    return {'projectId': PROJECT, 'checkpointId': CHECKPOINT,
            'promotionToken': sign_verified_checkpoint(signing_key=KEY, project_id=PROJECT,
                checkpoint_id=CHECKPOINT, checkpoint_commit=COMMIT)}


def test_review_is_bound_to_project_checkpoint_and_commit(database):
    assert release.save_evidence(PROJECT, evidence())
    current = release.review(PROJECT, CHECKPOINT, COMMIT)
    assert current['status'] == 'needs_review'
    assert [item['id'] for item in current['acknowledgements']] == ['visual-content', 'deferred-integrations', 'verification-scope']
    assert release.review('other-project', CHECKPOINT, COMMIT)['status'] == 'blocked'
    assert release.review(PROJECT, 'other-checkpoint', COMMIT)['status'] == 'blocked'
    assert release.review(PROJECT, CHECKPOINT, 'b' * 40)['status'] == 'blocked'


@pytest.mark.parametrize('kind', ['failed', 'incomplete', 'major', 'needs_polish'])
def test_unresolved_checks_block_publication_without_checkbox_override(database, kind):
    value = evidence()
    if kind in {'failed', 'incomplete'}: value['verification'][kind] = ['Booking flow needs repair']
    elif kind == 'needs_polish': value['verification']['visualReview']['status'] = 'needs_polish'
    else: value['verification']['visualReview']['findings'] = [
        {'severity': 'major', 'area': 'Phone layout', 'evidence': 'Primary action overlaps the form.'}]
    release.save_evidence(PROJECT, value)
    review = release.review(PROJECT, CHECKPOINT, COMMIT)
    assert review['status'] == 'blocked' and review['blockers']
    assert not release.acknowledged(review, review['reviewHash'], [item['id'] for item in review['acknowledgements']])


def test_unavailable_vision_is_not_silently_approved_and_deferred_items_need_acknowledgement(database):
    release.save_evidence(PROJECT, evidence('unavailable'))
    review = release.review(PROJECT, CHECKPOINT, COMMIT)
    assert review['status'] == 'needs_review'
    assert 'no automatic visual approval' in review['acknowledgements'][0]['items'][0]
    assert not release.acknowledged(review, review['reviewHash'], ['visual-content'])
    assert release.acknowledged(review, review['reviewHash'], [item['id'] for item in review['acknowledgements']])


def test_changed_evidence_invalidates_previous_review_and_fingerprint_mismatch_needs_manual_review(database):
    release.save_evidence(PROJECT, evidence())
    before = release.review(PROJECT, CHECKPOINT, COMMIT)
    changed = evidence(); changed['verification']['deferred'].append('Live payments')
    changed['verification']['visualReview']['sourceFingerprint'] = 'older-source'
    release.save_evidence(PROJECT, changed)
    after = release.review(PROJECT, CHECKPOINT, COMMIT)
    assert after['visualAssessment'] == 'unreviewed'
    assert not release.acknowledged(after, before['reviewHash'], [item['id'] for item in before['acknowledgements']])


def test_unverified_results_cannot_create_release_evidence(database):
    assert not release.save_evidence(PROJECT, evidence(browserVerified=False))
    assert release.load_evidence(PROJECT, CHECKPOINT, COMMIT) is None


@pytest.mark.parametrize('report', [None, [], {}, {'failed': [], 'incomplete': 'unknown'}])
def test_missing_report_fields_never_imply_release_approval(database, report):
    release.save_evidence(PROJECT, evidence(verification=report))
    assert release.review(PROJECT, CHECKPOINT, COMMIT)['status'] == 'blocked'


def test_review_and_publish_enforce_owner_and_saved_evidence(api):
    release.save_evidence(PROJECT, evidence())
    owner = {'Authorization': 'Bearer owner'}
    for path in ('/publish/review', '/publish'):
        assert api.post(path, headers={'Authorization': 'Bearer other'}, json=candidate()).status_code == 404
    response = api.post('/publish/review', headers=owner, json=candidate())
    assert response.status_code == 200 and response.json['visualAssessment'] == 'ready'
    response = api.post('/publish', headers=owner, json={**candidate(), 'reviewed': True,
        'verification': {'visualReview': {'status': 'ready'}}})
    assert response.status_code == 428 and response.json['review']['status'] == 'needs_review'


def test_publish_accepts_only_exact_current_review_acknowledgements(api, monkeypatch):
    import cloud_agent
    release.save_evidence(PROJECT, evidence())
    review = release.review(PROJECT, CHECKPOINT, COMMIT)
    body = {**candidate(), 'reviewHash': review['reviewHash'],
            'acknowledgements': [item['id'] for item in review['acknowledgements']]}
    assert api.post('/publish', headers={'Authorization': 'Bearer owner'}, json={**body, 'reviewHash': 'stale'}).status_code == 428
    calls = []
    monkeypatch.setattr(cloud_agent, 'get_workspace', lambda _: 'workspace-fixture')
    monkeypatch.setattr('agent.publishing.publish', lambda *args: calls.append(args) or 'f' * 32)
    response = api.post('/publish', headers={'Authorization': 'Bearer owner'}, json=body)
    assert response.status_code == 200 and len(calls) == 1
    assert calls[0] == ('workspace-fixture', PROJECT, CHECKPOINT, COMMIT)


def test_review_rejects_expired_or_tampered_approval_before_loading_workspace(api):
    response = api.post('/publish/review', headers={'Authorization': 'Bearer owner'},
                        json={**candidate(), 'promotionToken': 'tampered'})
    assert response.status_code == 403
    assert 'saved preview is unchanged' in response.json['message']


def test_release_evidence_is_retained_independently_of_job_cleanup(database, monkeypatch):
    release.save_evidence(PROJECT, evidence())
    before = release.review(PROJECT, CHECKPOINT, COMMIT)
    monkeypatch.setattr(release.time, 'time', lambda: 9999999999)
    assert release.review(PROJECT, CHECKPOINT, COMMIT)['reviewHash'] == before['reviewHash']
    assert 'promotionToken' not in json.dumps(release.load_evidence(PROJECT, CHECKPOINT, COMMIT))


def test_snapshot_changing_during_export_cannot_replace_an_existing_publication(database, tmp_path, monkeypatch):
    from agent.publishing import publish, root
    from tests.test_preview_hosting import Workspace
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH', str(tmp_path))
    workspace = Workspace()
    first = dict(workspace.proof)
    publication = publish(workspace, PROJECT, first['checkpointId'], first['commit'])
    active = root() / publication / '.active'
    before = active.read_text()
    def changed_archive(_):
        workspace.proof = {'checkpointId': 'newer-checkpoint', 'commit': 'newer-commit'}
        return workspace.blob
    workspace.sandbox.fs.download_file = changed_archive
    with pytest.raises(ValueError, match='changed during export'):
        publish(workspace, PROJECT, first['checkpointId'], first['commit'])
    assert active.read_text() == before
