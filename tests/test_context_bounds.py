import json

from agent import model_context


def test_serialized_code_stays_within_budget(monkeypatch):
    monkeypatch.setenv('GENESYS_INPUT_TOKEN_LIMIT', '4000')
    monkeypatch.setattr(model_context, 'reserve_model_budget', lambda tokens: None)
    messages = [{'role': 'system', 'content': 'Preserve the requested behavior.'},
                {'role': 'user', 'content': 'Build a counter with reset.'}]
    messages += [{'role': 'tool', 'content': ('"\\\n' * 12000)} for _ in range(5)]
    result = model_context.bounded_messages(messages, [], limit=4000)
    encoder = model_context.encoding()
    count = lambda value: len(encoder.encode(json.dumps(value, ensure_ascii=False, default=str), disallowed_special=()))
    assert count(result) + count([]) + 512 <= 4000
    assert result[0]['role'] == 'system'
    assert any(item['content'] == messages[1]['content'] for item in result)
    assert all(item['role'] != 'tool' for item in result)
