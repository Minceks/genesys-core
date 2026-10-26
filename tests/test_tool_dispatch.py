from types import SimpleNamespace
import pytest
from agent import tools,orchestrator


def test_scheduling_metadata_does_not_change_tool_payload_or_project(monkeypatch):
    calls=[]
    def write(filename,content,project_id='default'):
        calls.append((filename,content,project_id));return {'status':'success'}
    monkeypatch.setitem(tools.AVAILABLE_TOOLS,'write_file',write)
    result=tools.execute_tool('write_file',{'filename':'src/App.jsx','content':'Exact source',
        'priority':'high','project_id':'other'},project_id='owned-project')
    assert calls==[('src/App.jsx','Exact source','owned-project')]
    assert result['ignoredMetadata']==['priority']


def test_unknown_arguments_fail_before_tool_side_effects(monkeypatch):
    calls=[]
    def write(filename,content,project_id='default'):calls.append(filename)
    monkeypatch.setitem(tools.AVAILABLE_TOOLS,'write_file',write)
    result=tools.execute_tool('write_file',{'filename':'src/App.jsx','content':'data','force':True},'owned-project')
    assert not calls and result['status']=='error'
    assert result['allowedArguments']==['filename','content']
    assert 'No operation was executed' in result['repairInstruction']


def test_priority_does_not_bypass_full_file_read_guard(monkeypatch):
    calls=[]
    workspace=SimpleNamespace(read_file=lambda _: {'content':'x'*4000,'truncated':False},
        write_file=lambda *args:calls.append(args))
    monkeypatch.setattr(tools,'get_workspace',lambda _:workspace)
    with pytest.raises(ValueError,match='Use edit_file'):
        tools.execute_tool('write_file',{'filename':'src/App.jsx','content':'replacement','priority':'high'},'owned-project')
    assert calls==[]


def test_runtime_type_error_is_not_replayed_or_redirected_to_default_project(monkeypatch):
    calls=[]
    def execute(name,arguments,project_id='default'):
        calls.append(project_id);raise TypeError('Internal operation failed after its first side effect')
    monkeypatch.setattr(orchestrator,'execute_tool',execute)
    with pytest.raises(TypeError,match='Internal operation'):
        orchestrator._execute_agent_tool('write_file',{},'owned-project')
    assert calls==['owned-project']


@pytest.mark.parametrize('shape',['keyword','positional','legacy'])
def test_dispatch_compatibility_binds_before_calling_once(monkeypatch,shape):
    calls=[]
    if shape=='keyword':
        def execute(name,arguments,*,project_id):calls.append(project_id);return 'ok'
    elif shape=='positional':
        def execute(name,arguments,project,/):calls.append(project);return 'ok'
    else:
        def execute(name,arguments):calls.append('legacy');return 'ok'
    monkeypatch.setattr(orchestrator,'execute_tool',execute)
    assert orchestrator._execute_agent_tool('write_file',{},'owned-project')=='ok'
    assert calls==(['legacy'] if shape=='legacy' else ['owned-project'])
