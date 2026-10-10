from types import SimpleNamespace

import pytest

from agent.ai_provider import GroqProvider


class RateLimit(Exception):
    status_code = 429


def provider_with_retry(wait, calls):
    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RateLimit(f'Please try again in {wait}s.')
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Done', tool_calls=[]))])
    provider = GroqProvider.__new__(GroqProvider)
    provider.model = 'test-model'
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return provider


def test_brief_tpm_cooldown_is_retried_without_provider_switch(monkeypatch):
    sleeps, calls = [], []
    monkeypatch.setattr('agent.ai_provider.time.sleep', sleeps.append)
    result = provider_with_retry(6.5, calls).generate([{'role': 'user', 'content': 'Build an app.'}], [])
    assert result.text == 'Done'
    assert sleeps == [6.75]
    assert len(calls) == 2


def test_long_cooldown_remains_bounded(monkeypatch):
    sleeps, calls = [], []
    monkeypatch.setattr('agent.ai_provider.time.sleep', sleeps.append)
    with pytest.raises(RateLimit):
        provider_with_retry(61, calls).generate([{'role': 'user', 'content': 'Build an app.'}], [])
    assert not sleeps
    assert len(calls) == 1
