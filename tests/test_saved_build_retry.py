from agent.jobs import saved_build_retry


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
