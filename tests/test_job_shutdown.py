from agent.jobs import JobManager


def test_shutdown_keeps_job_available_for_restart(tmp_path, monkeypatch):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'jobs.sqlite3'))
    monkeypatch.delenv('RAILWAY_ENVIRONMENT_ID', raising=False)
    manager = JobManager()
    job_id = manager.submit('project', 'request', prompt='Build a counter',
                            verification_retry='saved-fingerprint')
    with manager.connection() as db:
        db.execute("UPDATE jobs SET state='running',owner=?,attempts=1 WHERE id=?",
                   (manager.owner, job_id))
    job = manager.get(job_id, 'project')
    contexts = []

    def interrupted(prompt, project, history, reservation, recovery):
        contexts.append(recovery)
        raise RuntimeError('cannot schedule new futures after interpreter shutdown')

    manager.execute = interrupted
    manager.run(job, [], None, 0)
    assert manager.get(job_id, 'project')['state'] == 'running'
    assert 'result' not in manager.get(job_id, 'project')
    assert contexts == [{'verificationRetry': 'saved-fingerprint'}]

    manager.execute = lambda *args: {'status': 'success', 'browserVerified': True}
    manager.run(job, [], None, 1)
    assert manager.get(job_id, 'project')['state'] == 'completed'
    manager.executor.shutdown(wait=True)
