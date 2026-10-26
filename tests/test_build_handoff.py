from types import SimpleNamespace
from unittest.mock import Mock
import time

import pytest
from agent.build_context import InspectionBudget, verification_due
from agent.progress import model_request_scope, model_request_timeout, model_deadline, ModelDeadlineExceeded
from agent.ai_provider import OpenAIProvider

TOOLS=[{'function':{'name':name}} for name in ('read_file','list_files','edit_file','write_file')]


def test_fallback_and_edits_do_not_reopen_unbounded_inspection():
    budget=InspectionBudget()
    assert all(budget.inspect() for _ in range(4))
    assert not budget.inspect()
    assert [t['function']['name'] for t in budget.tools(TOOLS)]==['edit_file','write_file']
    # The coordinator reuses this same object after a provider switch.
    assert not budget.inspect()
    budget.edited()
    assert budget.inspect() and budget.inspect() and not budget.inspect()
    budget.edited()
    assert budget.inspect() and budget.inspect() and not budget.inspect()
    budget.repair()
    assert budget.inspect() and budget.inspect() and not budget.inspect()


def test_saved_changes_get_verification_reserve_instead_of_step_limit_failure():
    assert verification_due(19,18,True,False,False,300)
    assert verification_due(10,18,True,False,False,50)
    assert not verification_due(10,18,True,False,False,300)
    assert not verification_due(19,18,False,False,False,300)
    assert not verification_due(19,18,True,True,False,300)
    assert not verification_due(19,18,True,False,True,300)


def test_nested_model_deadlines_cannot_extend_parent_and_restore_context():
    assert model_deadline.get() is None
    with model_request_scope(time.monotonic()+20):
        parent=model_deadline.get()
        with model_request_scope(time.monotonic()+100):assert model_deadline.get()==parent
        with model_request_scope(time.monotonic()+5):assert 0<model_request_timeout(90)<=5
        assert model_deadline.get()==parent
    assert model_deadline.get() is None


def provider(monkeypatch):
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
        message=SimpleNamespace(content='Saved',tool_calls=[]))]))
    return OpenAIProvider(model='test-model',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))),create


def test_openai_request_timeout_is_clamped_to_remaining_build_budget(monkeypatch):
    instance,create=provider(monkeypatch)
    with model_request_scope(time.monotonic()+12):instance.generate([{'role':'user','content':'Finish the saved edits'}],[])
    assert 0<create.call_args.kwargs['timeout']<=12


def test_expired_build_never_starts_another_paid_request(monkeypatch):
    instance,create=provider(monkeypatch)
    with model_request_scope(time.monotonic()-1):
        with pytest.raises(ModelDeadlineExceeded):instance.generate([{'role':'user','content':'Continue'}],[])
    create.assert_not_called()


def test_failed_workspace_preparation_returns_a_structured_error_without_logging_scope_failure(monkeypatch):
    from agent import orchestrator
    def unavailable():raise RuntimeError('Editor unavailable')
    monkeypatch.setattr(orchestrator,'get_provider',lambda:SimpleNamespace())
    monkeypatch.setattr(orchestrator,'get_workspace',lambda _:SimpleNamespace(prepare=unavailable))
    monkeypatch.setattr('agent.builder_controls.get_controls',lambda _: {})
    result=orchestrator.run_agent('Build a website','00000000-0000-4000-8000-000000000001')
    assert result['errorType']=='workspace_unavailable' and not result['modifiedFiles']


@pytest.mark.parametrize('failure_mode',['none','fallback','deadline','fallback_deadline'])
def test_real_agent_hands_saved_changes_to_build_and_keeps_inspection_context(monkeypatch,failure_mode):
    from agent import orchestrator
    from agent.ai_provider import AIResponse,AIToolCall
    class PreviewReached(BaseException):pass
    calls=[];writes=[]
    workspace=SimpleNamespace(prepare=lambda:None,
        read_file=lambda _: {'status':'success','content':'export default function App(){return <main>Ready</main>}', 'truncated':False},
        get_diff=lambda: {'status':'success','diff':'diff --git a/src/App.jsx b/src/App.jsx\n--- a/src/App.jsx\n+++ b/src/App.jsx\n-old\n+new'},
        run_build=Mock(return_value={'status':'success','success':True,'exitCode':0,'output':'Compiled'}),
        create_checkpoint=Mock())
    def preview():raise PreviewReached()
    workspace.start_preview=preview
    class Editor:
        model='fixture-model'
        def generate(self,messages,tools):
            calls.append(messages)
            if len(calls)==2 and failure_mode in {'deadline','fallback_deadline'}:
                if failure_mode=='fallback_deadline':raise TimeoutError('Fixture timeout after saved edits')
                raise ModelDeadlineExceeded('Implementation request window ended')
            return AIResponse(text='',tool_calls=[AIToolCall(id='edit',name='write_file',
                arguments={'filename':'src/App.jsx','content':'export default function App(){return <main>Updated</main>}'})])
    primary=SimpleNamespace(model='timed-out-model',generate=Mock(side_effect=TimeoutError('Fixture provider timeout')))
    monkeypatch.setattr(orchestrator,'settings',SimpleNamespace(provider_name='openai',agent_timeout_seconds=240))
    monkeypatch.setattr(orchestrator,'get_provider',lambda:primary if failure_mode=='fallback' else Editor())
    monkeypatch.setattr(orchestrator,'provider_for',lambda _:SimpleNamespace(model='fixture',
        generate=Mock(side_effect=ModelDeadlineExceeded('Fallback request window ended'))) if failure_mode=='fallback_deadline' else Editor())
    monkeypatch.setattr(orchestrator,'FALLBACK_PROVIDER','gemini')
    monkeypatch.setattr(orchestrator,'get_workspace',lambda _:workspace)
    monkeypatch.setattr(orchestrator,'BrowserSession',lambda **_:SimpleNamespace())
    monkeypatch.setattr('agent.builder_controls.get_controls',lambda _: {})
    monkeypatch.setattr(orchestrator,'_compact_messages',lambda messages:messages)
    monkeypatch.setattr(orchestrator,'scan_project',lambda *_,**__: {'status':'success','sourceFiles':['src/App.jsx']})
    monkeypatch.setattr(orchestrator,'build_project_context',lambda _: 'CURRENT INSPECTED SOURCE CONTEXT')
    monkeypatch.setattr(orchestrator,'target_project_files',lambda *_:['src/App.jsx'])
    monkeypatch.setattr(orchestrator,'_validate_change_plan',lambda *_:{'valid':True})
    monkeypatch.setattr(orchestrator,'_validate_diff',lambda *_:{'valid':True})
    monkeypatch.setattr(orchestrator,'MAX_STEPS',4 if 'deadline' in failure_mode else 1)
    monkeypatch.setattr(orchestrator,'TOTAL_MAX_STEPS',6)
    def execute(name,*_,**__):
        if name=='write_file':writes.append(name)
        return {'status':'success','files':['src/App.jsx']} if name=='list_files' else {'status':'success'}
    monkeypatch.setattr(orchestrator,'_execute_agent_tool',execute)
    with pytest.raises(PreviewReached):orchestrator.run_agent('Fix application code')
    workspace.run_build.assert_called_once()
    workspace.create_checkpoint.assert_not_called()  # Compilation cannot bypass browser checks.
    assert len(calls)==(2 if 'deadline' in failure_mode else 1)
    assert len(writes)==1
    assert any('CURRENT INSPECTED SOURCE CONTEXT' in str(message.get('content')) for message in calls[0])
