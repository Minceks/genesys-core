from pathlib import Path

from agent import model_context


def test_tokenizer_is_declared_and_checked_during_build():
    root = Path(__file__).resolve().parents[1]
    assert 'tiktoken' in (root / 'requirements.txt').read_text().splitlines()
    assert 'tiktoken' in (root / 'railway.toml').read_text()


def test_verification_context_can_use_real_tokenizer(monkeypatch):
    monkeypatch.setattr(model_context, 'reserve_model_budget', lambda _: None)
    messages = [{'role': 'system', 'content': 'Return JSON only.'},
                {'role': 'user', 'content': 'Verify the cart workflow.'}]
    assert model_context.bounded_messages(messages, []) == messages
