import json
from types import SimpleNamespace

import pytest

from agent.ai_provider import GroqProvider, recover_namespaced_tool
from agent.tools import TOOLS


ARGS = {'filename': 'src/App.jsx', 'old_text': 'old source', 'new_text': 'new source\n'}


@pytest.mark.parametrize('prefix', ['functions/', 'functions.'])
def test_exact_namespace_recovery_preserves_edit_arguments(prefix):
    call = recover_namespaced_tool({'name': prefix+'edit_file', 'arguments': ARGS}, TOOLS)
    assert call.name == 'edit_file'
    assert call.arguments == ARGS


@pytest.mark.parametrize('failed,tools', [
    ({'name': 'functions/edit_file', 'arguments': ARGS}, []),
    ({'name': 'functions/delete_everything', 'arguments': {}}, TOOLS),
    ({'name': 'other/edit_file', 'arguments': ARGS}, TOOLS),
    ({'name': 'functions/edit_file', 'arguments': {**ARGS, 'extra': True}}, TOOLS),
    ({'name': 'functions/edit_file', 'arguments': {'filename': 'src/App.jsx'}}, TOOLS),
    ({'name': 'functions/edit_file', 'arguments': {**ARGS, 'new_text': None}}, TOOLS),
    ({'name': 'functions/edit_file', 'arguments': json.dumps(ARGS)}, TOOLS),
])
def test_namespace_recovery_never_expands_tools_or_repairs_invalid_arguments(failed, tools):
    assert recover_namespaced_tool(failed, tools) is None


def test_actual_groq_400_recovers_call_without_another_paid_request():
    class Rejected(Exception):
        status_code = 400
        body = {'error': {'code': 'tool_use_failed', 'failed_generation': json.dumps(
            {'name': 'functions/edit_file', 'arguments': ARGS})}}
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        raise Rejected()
    provider = GroqProvider.__new__(GroqProvider)
    provider.model = 'fixture'
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    result = provider.generate([{'role': 'user', 'content': 'Edit the existing file.'}], TOOLS)
    assert len(calls) == 1
    assert result.tool_calls[0].name == 'edit_file'
    assert result.tool_calls[0].arguments == ARGS
    assert not result.text
