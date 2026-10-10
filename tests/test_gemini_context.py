from types import SimpleNamespace

from agent.ai_provider import GeminiProvider


def capture_request(messages):
    captured = {}

    def generate_content(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(candidates=[])

    provider = GeminiProvider.__new__(GeminiProvider)
    provider.model = 'test-model'
    provider.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    provider.generate(messages, [])
    return captured


def test_all_system_instructions_survive_added_source_context():
    request = capture_request([
        {'role': 'system', 'content': 'Core build and persistence instructions.'},
        {'role': 'user', 'content': 'Create a reading tracker.'},
        {'role': 'system', 'content': 'Current source and repair context.'},
    ])
    assert request['config'].system_instruction == 'Core build and persistence instructions.\n\nCurrent source and repair context.'


def test_fallback_history_ends_with_user_and_merges_adjacent_turns():
    request = capture_request([
        {'role': 'user', 'content': 'Build an app.'},
        {'role': 'assistant', 'content': 'I will implement the app.'},
        {'role': 'assistant', 'content': 'The source has been edited.'},
        {'role': 'system', 'content': 'Previous tool result: edits succeeded.'},
    ])
    assert [turn.role for turn in request['contents']] == ['user', 'model', 'user']
    assert len(request['contents'][1].parts) == 2


def test_function_responses_stay_paired_and_keep_thought_signature():
    request = capture_request([
        {'role': 'user', 'content': 'Read the source.'},
        {'role': 'assistant', 'tool_calls': [{
            'id': 'call-1', 'thought_signature': b'original-signature',
            'function': {'name': 'read_file', 'arguments': '{"filename":"src/App.jsx"}'},
        }]},
        {'role': 'tool', 'name': 'read_file', 'tool_call_id': 'call-1', 'content': '{"status":"success"}'},
    ])
    assert [turn.role for turn in request['contents']] == ['user', 'model', 'user']
    assert request['contents'][1].parts[0].thought_signature == b'original-signature'
    assert request['contents'][2].parts[0].function_response.name == 'read_file'
