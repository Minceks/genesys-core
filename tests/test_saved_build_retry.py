import pytest

from agent.jobs import JobManager, recheck_request, recheck_source, saved_build_retry


def test_verified_build_failure_preserves_fingerprint():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'buildPassed': True, 'browserVerified':True,'buildFingerprint': 'saved'}}, 'Counter') == 'saved'


def test_provider_failure_after_edits_resumes_implementation():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'errorType': 'ai_request', 'modifiedFiles': ['src/App.jsx']}},
        'Counter') is None


def test_interrupted_unverified_retry_resumes_implementation():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'verificationRetry': 'old', 'result': {}}, 'Counter') is None


def test_new_request_or_completed_job_cannot_skip_implementation():
    previous = {'state': 'failed', 'prompt': 'Counter', 'result': {'buildPassed': True}}
    assert saved_build_retry(previous, 'Add expenses') is None
    previous['state'] = 'completed'
    assert saved_build_retry(previous, 'Counter') is None


def test_provider_failure_before_any_edit_does_not_skip_implementation():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'errorType': 'ai_request', 'modifiedFiles': []}}, 'Counter') is None


def test_compiled_app_with_missing_controls_does_not_skip_implementation():
    from agent.jobs import implementation_retry_context
    previous={'state':'failed','prompt':'Build a website builder','result':{
        'buildPassed':True,'browserVerified':False,'buildFingerprint':'compiled',
        'verification':{'failed':['Create New Site: Requested control is missing'],
                        'incomplete':['Accent color must persist after reload']}}}
    assert saved_build_retry(previous,previous['prompt']) is None
    context=implementation_retry_context(previous,previous['prompt'])
    assert 'Create New Site' in context and 'Accent color' in context
    assert implementation_retry_context(previous,'Build a portfolio') is None

def test_incomplete_verification_preserves_compiled_source_for_retry():
    from agent.jobs import implementation_retry_context
    previous={'state':'failed','prompt':'Zombie game','result':{'buildPassed':True,'browserVerified':False,'buildFingerprint':'compiled-source','errorType':'verification_incomplete','verification':{'failed':[],'incomplete':['Canvas observation could not finish']}}}
    assert saved_build_retry(previous,'Zombie game')=='compiled-source'
    assert implementation_retry_context(previous,'Zombie game') is None
    previous['result']['verification']['failed']=['Actual movement handler is broken']
    assert saved_build_retry(previous,'Zombie game') is None


@pytest.mark.parametrize('prompt', ['do the check agian', 'do the check again', 'Run the tests again.', 'check again', 'recheck',
                                    're-verify', 'verify again', 'please run all the checks', '/build retry the verification'])
def test_plain_recheck_wording_is_recognised(prompt):
    assert recheck_request(prompt)


@pytest.mark.parametrize('prompt', ['check again that the cart works and fix it', 'Add tests for the cart', 'make the zombies faster',
                                    'check the header', '/plan check again', '/discuss recheck'])
def test_real_requests_are_never_treated_as_a_recheck(prompt):
    assert not recheck_request(prompt)


def saved(prompt='/build Create a zombie game', **result):
    return {'state': 'failed', 'prompt': prompt, 'result': {'buildPassed': True, 'errorType': 'verification_incomplete',
        'verification': {'failed': [], 'incomplete': ['Design note']}, 'buildFingerprint': 'saved', **result}}


def test_recheck_finds_the_real_request_behind_earlier_rechecks():
    original = saved()
    history = [original, saved('do the check again'), saved('/build check again')]
    assert recheck_source(history) is original


def test_recheck_never_skips_a_later_change_or_a_build_with_real_failures():
    change = {'state': 'completed', 'prompt': 'Make it faster', 'result': {'buildPassed': True}}
    assert recheck_source([saved(), change]) is None
    assert recheck_source([saved(verification={'failed': ['Cart is broken'], 'incomplete': []})]) is None
    assert recheck_source([]) is None


def test_recheck_reaches_the_agent_as_a_test_only_run(tmp_path, monkeypatch):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'jobs.sqlite3'))
    monkeypatch.delenv('RAILWAY_ENVIRONMENT_ID', raising=False)
    manager = JobManager()
    job_id = manager.submit('project', 'request', prompt='Build', verification_retry='saved', verification_recheck=True)
    with manager.connection() as db:
        db.execute("UPDATE jobs SET state='running',owner=?,attempts=1 WHERE id=?", (manager.owner, job_id))
    seen = []
    manager.execute = lambda prompt, project, history, reservation, recovery: seen.append(recovery) or {'status': 'success'}
    manager.run(manager.get(job_id, 'project'), [], None, 1)
    assert seen == [{'verificationRetry': 'saved', 'functionalRecheck': True}]


def test_recheck_restores_the_trusted_game_contract_over_a_rewritten_one():
    from types import SimpleNamespace
    from agent.build_spec import prepare_build_spec
    written = {}
    workspace = SimpleNamespace(read_file=lambda _: {'content': 'export default function App(){return <main>Zombies</main>}'},
        write_file=lambda path, content: written.update({path: content}) or {'status': 'success'})
    brief = {'productType': 'game', 'buildIntent': 'modify', 'originalRequest': 'Create a top-down zombie wave survival shooter'}
    spec = prepare_build_spec(workspace, brief['originalRequest'], brief, None, restore_foundation=True)
    assert spec['foundationContractVersion'] == 1 and written
