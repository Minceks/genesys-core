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


def test_failed_verification_is_logged_without_dumping_prompt_or_generated_source(tmp_path,monkeypatch,caplog):
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'jobs.sqlite3'))
    monkeypatch.delenv('RAILWAY_ENVIRONMENT_ID',raising=False)
    manager=JobManager()
    job_id=manager.submit('project','request',prompt='PRIVATE REQUEST')
    with manager.connection() as db:
        db.execute("UPDATE jobs SET state='running',owner=? WHERE id=?",(manager.owner,job_id))
    manager.execute=lambda *_:{'status':'error','errorType':'verification_incomplete','buildPassed':True,
        'browserVerified':False,'text':'PRIVATE SOURCE','verification':{'failed':['r9-phone-touch: controls outside viewport'],
        'incomplete':['r9-phone-touch: not completed']}}
    try:
        manager.run(manager.get(job_id,'project'),[],None,0)
        assert manager.get(job_id,'project')['state']=='failed'
        assert 'background_agent_result' in caplog.text and 'r9-phone-touch' in caplog.text
        assert 'verification_incomplete' in caplog.text
        assert 'PRIVATE REQUEST' not in caplog.text and 'PRIVATE SOURCE' not in caplog.text
    finally:manager.executor.shutdown(wait=True)
