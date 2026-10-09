import threading

import pytest

from agent.jobs import JobManager
from agent.progress import report_progress


def test_projects_have_separate_progress_and_results_and_capacity_is_bounded():
    manager = JobManager(workers=2)
    release = threading.Event()
    ready_a, ready_b = threading.Event(), threading.Event()

    def execute(project, ready):
        report_progress(f"Building {project}")
        ready.set()
        assert release.wait(5)
        return {"status": "success", "projectId": project}

    try:
        a = manager.submit("a", "request-a", lambda: execute("a", ready_a))
        b = manager.submit("b", "request-b", lambda: execute("b", ready_b))
        assert ready_a.wait(5) and ready_b.wait(5)
        assert manager.get(a, "b") is None
        assert manager.get(a, "a")["stage"] == "Building a"
        assert manager.get(b, "b")["stage"] == "Building b"
        with pytest.raises(ValueError, match="already running"):
            manager.submit("a", "other", lambda: {})
        with pytest.raises(ValueError, match="busy"):
            manager.submit("c", "request-c", lambda: {})
    finally:
        release.set()
        manager.executor.shutdown(wait=True)
    assert manager.get(a, "a")["result"]["projectId"] == "a"
    assert manager.get(b, "b")["requestId"] == "request-b"


def test_background_failure_is_reported_and_releases_project():
    manager = JobManager(workers=1)
    def fail():
        raise RuntimeError("private backend detail")
    job = manager.submit("project", "request", fail)
    manager.executor.shutdown(wait=True)
    result = manager.get(job, "project")
    assert result["state"] == "failed"
    assert "private backend detail" not in result["result"]["message"]
    assert not manager.is_running("project")


def test_beta_routes_require_auth_and_return_request_references(monkeypatch):
    import cloud_agent
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
