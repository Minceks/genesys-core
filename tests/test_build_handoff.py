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


def agent_at_visual_review(monkeypatch,reserve_seconds,polish_error,workflow_review=None,workflow_repair=False):
    """Drive the real loop to a passed build whose screenshot review requests polish."""
    from agent import orchestrator
    from agent.ai_provider import AIResponse,AIToolCall
    class FunctionalChecksReached(BaseException):pass
    calls=[]
    review={'status':'needs_polish','summary':'Hero needs a focal point','findings':[]}
    browser=SimpleNamespace(stop=lambda:None,visual_quality=Mock(side_effect=[
        {'status':'success','visualPolishRequested':True,'visualReview':review},
        {'status':'success','visualPolishRequested':False,'visualReview':review}]))
    def content_checks(*_,**__):
        if workflow_review is None:raise FunctionalChecksReached()
        return {'status':'success','issues':[],'unverified':[],'unverifiedCore':[],'testedInteractions':['Booking flow'],'coverage':{}}
    browser.content_checks=content_checks
    browser.review_workflow_design=lambda *_:(workflow_review,workflow_repair)
    browser.get_console=lambda:{'hasRuntimeErrors':False}
    workspace=SimpleNamespace(prepare=lambda:None,
        read_file=lambda _: {'status':'success','content':'export default function App(){return <main>Ready</main>}', 'truncated':False},
        get_diff=lambda: {'status':'success','diff':'diff --git a/src/App.jsx b/src/App.jsx\n--- a/src/App.jsx\n+++ b/src/App.jsx\n-old\n+new'},
        run_build=Mock(return_value={'status':'success','success':True,'exitCode':0,'output':'Compiled'}),
        start_preview=Mock(return_value={'status':'success','url':'https://preview.test'}),
        create_checkpoint=Mock(side_effect=FunctionalChecksReached()))
    class Editor:
        model='fixture-model'
        def generate(self,messages,tools):
            calls.append(messages)
            if len(calls)==1:
                return AIResponse(text='',tool_calls=[AIToolCall(id='edit',name='write_file',
                    arguments={'filename':'src/App.jsx','content':'export default function App(){return <main>Updated</main>}'})])
            if len(calls)==2:return AIResponse(text='Saved')
            raise polish_error
    project='00000000-0000-4000-8000-000000000001'
    monkeypatch.setattr(orchestrator,'settings',SimpleNamespace(provider_name='openai',agent_timeout_seconds=240))
    monkeypatch.setattr(orchestrator,'REVIEW_RESERVE_SECONDS',reserve_seconds)
    monkeypatch.setattr(orchestrator,'get_provider',lambda:Editor())
    monkeypatch.setattr(orchestrator,'provider_for',lambda _:SimpleNamespace(model='fixture',
        generate=Mock(side_effect=ModelDeadlineExceeded('Fallback request window ended'))))
    monkeypatch.setattr(orchestrator,'FALLBACK_PROVIDER','gemini')
    monkeypatch.setattr(orchestrator,'get_workspace',lambda _:workspace)
    monkeypatch.setattr(orchestrator,'get_browser',lambda _:browser)
    monkeypatch.setattr(orchestrator,'stop_browser',lambda _:None)
    monkeypatch.setattr(orchestrator,'BrowserSession',lambda **_:browser)
    monkeypatch.setattr('agent.builder_controls.get_controls',lambda _: {})
    monkeypatch.setattr('agent.version_history.operate',lambda *_,**__:{'status':'success'})
    monkeypatch.setattr('agent.product_design.prepare_design',lambda *_:{'productType':'app','subtype':'app'})
    monkeypatch.setattr('agent.build_spec.prepare_build_spec',lambda *_,**__:{})
    monkeypatch.setattr(orchestrator,'_compact_messages',lambda messages:messages)
    monkeypatch.setattr(orchestrator,'scan_project',lambda *_,**__: {'status':'success','sourceFiles':['src/App.jsx']})
    monkeypatch.setattr(orchestrator,'build_project_context',lambda _: 'CURRENT INSPECTED SOURCE CONTEXT')
    monkeypatch.setattr(orchestrator,'target_project_files',lambda *_:['src/App.jsx'])
    monkeypatch.setattr(orchestrator,'_validate_change_plan',lambda *_:{'valid':True})
    monkeypatch.setattr(orchestrator,'_validate_diff',lambda *_:{'valid':True})
    monkeypatch.setattr(orchestrator,'MAX_STEPS',6)
    monkeypatch.setattr(orchestrator,'TOTAL_MAX_STEPS',8)
    monkeypatch.setattr(orchestrator,'_execute_agent_tool',lambda name,*_,**__:
        {'status':'success','files':['src/App.jsx']} if name=='list_files' else {'status':'success'})
    monkeypatch.setattr(orchestrator,'execute_tool',lambda *_,**__:{'status':'success','hasRuntimeErrors':False})
    with pytest.raises(FunctionalChecksReached):orchestrator.run_agent('Fix application code',project)
    return workspace,browser,calls


@pytest.mark.parametrize('polish_error',[ModelDeadlineExceeded('Polish window ended'),TimeoutError('Polish request timed out')])
def test_timed_out_polish_verifies_the_saved_build_instead_of_failing(monkeypatch,polish_error):
    workspace,browser,calls=agent_at_visual_review(monkeypatch,100,polish_error)
    assert len(calls)==3 and 'SCREENSHOT DESIGN REVIEW' in str(calls[-1])
    assert browser.visual_quality.call_count==2
    workspace.run_build.assert_called_once()  # The unchanged build stays proven.


def test_polish_without_time_to_finish_goes_directly_to_functional_checks(monkeypatch):
    workspace,browser,calls=agent_at_visual_review(monkeypatch,200,RuntimeError('Polish must not start'))
    assert len(calls)==2
    assert browser.visual_quality.call_count==1
    workspace.run_build.assert_called_once()


def test_passing_checks_with_open_design_notes_finish_as_a_verified_build(monkeypatch):
    # A working build whose review still has opinions after its repair budget.
    review={'status':'needs_polish','summary':'Phone controls feel cramped','findings':[
        {'severity':'major','evidence':'Skill buttons are small.','correction':'Enlarge them.'}]}
    workspace,browser,calls=agent_at_visual_review(monkeypatch,200,RuntimeError('Polish must not start'),review)
    workspace.create_checkpoint.assert_called_once()  # Reached only after browser_verified.
    assert len(calls)==2


def test_a_build_gets_one_polish_round_even_when_a_second_view_asks_for_another(monkeypatch):
    review={'status':'needs_polish','summary':'Still cramped','findings':[]}
    workspace,browser,calls=agent_at_visual_review(monkeypatch,100,ModelDeadlineExceeded('Polish window ended'),review,True)
    assert str(calls[-1]).count('SCREENSHOT DESIGN REVIEW')==1
    workspace.create_checkpoint.assert_called_once()
