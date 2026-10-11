from agent.jobs import saved_build_retry


def test_verified_build_failure_preserves_fingerprint():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'buildPassed': True, 'buildFingerprint': 'saved'}}, 'Counter') == 'saved'


def test_provider_failure_after_edits_rebuilds_saved_files():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'errorType': 'ai_request', 'modifiedFiles': ['src/App.jsx']}},
        'Counter') == 'rebuild-saved-project'


def test_interrupted_retry_does_not_restart_implementation():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'verificationRetry': 'old', 'result': {}}, 'Counter') == 'rebuild-saved-project'


def test_new_request_or_completed_job_cannot_skip_implementation():
    previous = {'state': 'failed', 'prompt': 'Counter', 'result': {'buildPassed': True}}
    assert saved_build_retry(previous, 'Add expenses') is None
    previous['state'] = 'completed'
    assert saved_build_retry(previous, 'Counter') is None


def test_provider_failure_before_any_edit_does_not_skip_implementation():
    assert saved_build_retry({'state': 'failed', 'prompt': 'Counter',
        'result': {'errorType': 'ai_request', 'modifiedFiles': []}}, 'Counter') is None
