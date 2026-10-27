import hashlib
from agent.saved_verification import matching_plan, saved_plan_record


def test_saved_checks_are_invalidated_by_build_or_request_changes():
    plan = {'checks': [{'name': 'Cart'}]}
    saved = {'version': 1, 'requestHash': hashlib.sha256(b'Store').hexdigest(),
             'buildFingerprint': 'build-a', 'plan': plan}
    assert matching_plan(saved, 'Store', 'build-a') == plan
    assert matching_plan(saved, 'Different request', 'build-a') is None
    assert matching_plan(saved, 'Store', 'build-b') is None


def test_automatic_cache_is_pinned_to_request_build_and_contract():
    plan = {'checks': [{'name': 'Cart'}]}
    contract = {'requirements': [{'id': 'cart', 'acceptance': 'Cart survives reload'}]}
    saved = saved_plan_record('Store', 'build-a', plan, contract)
    assert matching_plan(saved, 'Store', 'build-a', contract) == plan
    assert matching_plan(saved, 'Changed request', 'build-a', contract) is None
    assert matching_plan(saved, 'Store', 'changed-build', contract) is None
    assert matching_plan(saved, 'Store', 'build-a', {'requirements': []}) is None
    assert matching_plan(saved, 'Store', 'build-a') is None


def test_legacy_record_cannot_bypass_contract_changes():
    saved = {'version': 1, 'requestHash': hashlib.sha256(b'Store').hexdigest(),
             'buildFingerprint': 'build-a', 'plan': {'checks': []}}
    assert matching_plan(saved, 'Store', 'build-a', {'requirements': []}) is None


def test_saved_plan_is_replayed_once_then_repairs_use_the_real_provider():
    from types import SimpleNamespace
    from agent.saved_verification import SavedPlanProvider
    class Fallback:
        def generate(self, messages, tools):
            return SimpleNamespace(text='repaired')
    provider = SavedPlanProvider({'checks': []}, Fallback())
    messages = [{'role': 'system', 'content': 'You are a browser verification planner. Repair a plan'}]
    assert provider.generate(messages, []).text == '{"checks": []}'
    assert provider.generate(messages, []).text == 'repaired'


def test_retry_replays_passed_scopes_without_overwriting_other_workflows():
    from agent.verification_retry import retain_passed_checks
    passed = {'name': 'Create A', 'covers': ['R1'], 'steps': [
        {'action': 'click', 'target': {'name': 'Add', 'withinText': 'A'}}]}
    regressed = {'name': 'Create A', 'covers': ['R1'], 'steps': [
        {'action': 'click', 'target': {'name': 'Add'}}]}
    failed = {'name': 'Delete A', 'covers': ['R1'], 'steps': []}
    result = retain_passed_checks({'checks': [regressed, failed]}, [passed])
    assert result['checks'] == [passed, failed]
    result = retain_passed_checks({'checks': [failed]}, [passed])
    assert result['checks'] == [failed, passed]
    assert 'withinText' not in regressed['steps'][0]['target']
