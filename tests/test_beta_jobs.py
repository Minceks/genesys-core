import threading

import pytest

from agent.jobs import JobManager
from agent.progress import report_progress


@pytest.fixture(autouse=True)
def isolated_job_store(tmp_path, monkeypatch):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'jobs.sqlite3'))
    monkeypatch.delenv('RAILWAY_ENVIRONMENT_ID', raising=False)


def claim(manager, job_id, project):
    # Run a queued durable job without starting an immortal dispatcher thread.
    with manager.connection() as db:
        db.execute("UPDATE jobs SET state='running',owner=?,attempts=1 WHERE id=?", (manager.owner, job_id))
    return manager.get(job_id, project)


def test_failed_application_retry_delivers_diagnostics_to_implementation():
    manager=JobManager(workers=1)
    received=[]
    try:
        manager.execute=lambda prompt,project,history,reservation,recovery:received.append(recovery) or {'status':'success'}
        job_id=manager.submit('project','retry',prompt='Build an app',implementation_retry='Repair missing Create New Site control')
        manager.run(claim(manager,job_id,'project'),[],None,0)
        assert received==['Repair missing Create New Site control']
        assert manager.get(job_id,'project')['state']=='completed'
    finally:
        manager.executor.shutdown(wait=True)


def test_legacy_queued_retry_does_not_skip_implementation():
    manager=JobManager(workers=1)
    received=[]
    try:
        manager.execute=lambda prompt,project,history,reservation,recovery:received.append(recovery) or {'status':'success'}
        job_id=manager.submit('project','legacy',prompt='Build an app',verification_retry='compiled-only')
        job=claim(manager,job_id,'project');job.pop('verificationRetryVerified')
        manager.run(job,[],None,0)
        assert isinstance(received[0],str) and 'no evidence' in received[0]
    finally:
        manager.executor.shutdown(wait=True)


def test_projects_have_separate_progress_and_results_and_duplicate_requests_are_blocked():
    manager = JobManager(workers=2)
    release = threading.Event()
    ready_a, ready_b = threading.Event(), threading.Event()

    def execute(project, ready):
        report_progress(f"Building {project}")
        ready.set()
        assert release.wait(5)
        return {"status": "success", "projectId": project}

    try:
        manager.execute = lambda prompt,project,*_:execute(project,ready_a if project=='a' else ready_b)
        a = manager.submit("a", "request-a", prompt='Build A')
        b = manager.submit("b", "request-b", prompt='Build B')
        manager.executor.submit(manager.run,claim(manager,a,'a'),[],None,0)
        manager.executor.submit(manager.run,claim(manager,b,'b'),[],None,0)
        assert ready_a.wait(5) and ready_b.wait(5)
        assert manager.get(a, "b") is None
        assert manager.get(a, "a")["stage"] == "Building a"
        assert manager.get(b, "b")["stage"] == "Building b"
        with pytest.raises(ValueError, match="already running"):
            manager.submit("a", "other", prompt='Duplicate')
    finally:
        release.set()
        manager.executor.shutdown(wait=True)
    assert manager.get(a, "a")["result"]["projectId"] == "a"
    assert manager.get(b, "b")["requestId"] == "request-b"


def test_durable_waiting_queue_has_bounded_capacity():
    manager=JobManager(workers=1)
    try:
        for index in range(100):
            manager.submit(str(index),str(index),prompt='Queued work')
        with pytest.raises(ValueError,match='busy'):
            manager.submit('overflow','overflow',prompt='No worker or provider should execute this')
    finally: manager.executor.shutdown(wait=True)


def test_background_failure_is_reported_and_releases_project():
    manager = JobManager(workers=1)
    def fail(*_):
        raise RuntimeError("private backend detail")
    manager.execute=fail
    job = manager.submit("project", "request", prompt='Synthetic failing job')
    manager.executor.submit(manager.run,claim(manager,job,'project'),[],None,0)
    manager.executor.shutdown(wait=True)
    result = manager.get(job, "project")
    assert result["state"] == "failed"
    assert "private backend detail" not in result["result"]["message"]
    assert not manager.is_running("project")


def test_beta_routes_require_auth_and_return_request_references(monkeypatch):
    import cloud_agent
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    from types import SimpleNamespace
    manager = JobManager()
    monkeypatch.setattr(cloud_agent, "jobs", manager)
    monkeypatch.setattr(cloud_agent, "settings", SimpleNamespace(api_key="test-key"))
    monkeypatch.setattr(cloud_agent, "execute_agent_request", lambda *args: {"status": "success", "requestType": "chat", "text": "Answer"})
    client = cloud_agent.app.test_client()
    assert client.post("/agent/jobs", json={"projectId": "test", "prompt": "hello"}).status_code == 401
    response = client.post("/agent/jobs", json={"projectId": "test", "prompt": "hello"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 202
    job = response.get_json()
    manager.execute=cloud_agent.execute_agent_request
    manager.executor.submit(manager.run,claim(manager,job['jobId'],'test'),[],None,0)
    manager.executor.shutdown(wait=True)
    assert job["requestId"] == response.headers["X-Request-ID"]
    assert client.get(f"/agent/jobs/{job['jobId']}?projectId=other", headers={"X-API-Key": "test-key"}).status_code == 404
    status = client.get(f"/agent/jobs/{job['jobId']}?projectId=test", headers={"X-API-Key": "test-key"}).get_json()
    assert status["result"]["requestType"] == "chat"
    feedback = client.post("/beta/feedback", json={"message": "Preview blocked", "projectId": "test", "requestId": job["requestId"]}, headers={"X-API-Key": "test-key"})
    assert feedback.status_code == 200
    assert feedback.get_json()["reportId"]


@pytest.mark.parametrize("verified", [True, False])
def test_job_execution_only_signs_successful_verified_checkpoints(monkeypatch, verified):
    import cloud_agent
    from types import SimpleNamespace
    from agent.promotion import verify_checkpoint_promotion_token
    result = {"status": "success", "buildPassed": True, "browserVerified": verified,
              "checkpoint": {"status": "success", "checkpointId": "genesys-checkpoint-123", "commit": "a" * 40}}
    monkeypatch.setattr(cloud_agent, "run_agent", lambda **kwargs: dict(result))
    monkeypatch.setattr(cloud_agent, "settings", SimpleNamespace(promotion_signing_key="test-key"))
    executed = cloud_agent.execute_agent_request("Build", "beta-project", [])
    if verified:
        assert verify_checkpoint_promotion_token(executed["promotionToken"], signing_key="test-key",
            project_id="beta-project", checkpoint_id="genesys-checkpoint-123") == "a" * 40
    else:
        assert "promotionToken" not in executed
