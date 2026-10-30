from types import SimpleNamespace
import pytest
from benchmarks.spend_guard import SpendGuard, SpendLimit


def test_limit_prevents_request_before_spending(tmp_path):
    guard = SpendGuard(tmp_path/'cost.json', '.10')
    with pytest.raises(SpendLimit):
        guard.call(lambda **_: pytest.fail('Unfunded request executed'), model='gpt-5-mini',max_completion_tokens=6000)


def test_reported_usage_reconciles_conservative_reservation(tmp_path):
    guard = SpendGuard(tmp_path/'cost.json', '1')
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=1000,completion_tokens=100))
    guard.call(lambda **_: response, model='gpt-5-mini',max_completion_tokens=6000)
    assert float(guard.read()['chargedUpperUsd']) == .00045
    assert guard.read()['calls'][0]['state'] == 'reported'


def test_unknown_usage_or_failure_retains_full_reservation(tmp_path):
    guard = SpendGuard(tmp_path/'cost.json', '.23')
    guard.call(lambda **_: SimpleNamespace(),model='gpt-5-mini',max_completion_tokens=6000)
    def failure(**_): raise TimeoutError()
    with pytest.raises(TimeoutError):
        guard.call(failure,model='gpt-5-mini',max_completion_tokens=6000)
    with pytest.raises(SpendLimit):
        guard.call(lambda **_: pytest.fail('Unknown usage was refunded'),model='gpt-5-mini',max_completion_tokens=6000)
    assert float(guard.read()['chargedUpperUsd']) == .224


def test_unpriced_model_cannot_bypass_guard(tmp_path):
    guard=SpendGuard(tmp_path/'cost.json','4')
    with pytest.raises(SpendLimit):
        guard.call(lambda **_: pytest.fail('Unpriced model called'),model='other-model',max_completion_tokens=6000)
