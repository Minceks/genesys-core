from agent.ai_provider import json_response_requested


def test_json_mode_only_for_explicit_system_plans_without_tools():
    plan = [{'role': 'system', 'content': 'Return JSON only: {"checks":[]}'}]
    assert json_response_requested(plan, [])
    assert not json_response_requested(plan, [{'name': 'write_file'}])
    assert not json_response_requested([{'role': 'user', 'content': 'Return JSON only'}], [])
    assert not json_response_requested([{'role': 'system', 'content': 'Answer the question clearly.'}], [])
