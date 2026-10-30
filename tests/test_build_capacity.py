import time
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from agent.ai_provider import OpenAIProvider
from agent.parallel_build import review_draft, DraftReviewFailed
from agent.progress import draft_stage_deadline, model_request_scope, model_request_timeout


def test_quality_capacity_applies_to_actual_api_calls_and_length_retries(monkeypatch):
    monkeypatch.delenv('GENESYS_OUTPUT_TOKEN_LIMIT',raising=False)
    monkeypatch.delenv('GENESYS_OUTPUT_TOKEN_CEILING',raising=False)
    monkeypatch.delenv('GENESYS_REASONING_EFFORT',raising=False)
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    def response(reason):return SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason,message=SimpleNamespace(content='Complete code',tool_calls=[]))])
    create=Mock(side_effect=[response('length'),response('stop')])
    provider=OpenAIProvider(model='gpt-5-mini',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    assert provider.generate([{'role':'user','content':'Build the complete application'}],[]).text=='Complete code'
    assert [call.kwargs['max_completion_tokens'] for call in create.call_args_list]==[12000,24000]
    assert all(call.kwargs['reasoning_effort']=='medium' for call in create.call_args_list)
    assert create.call_args_list[0].kwargs['timeout']==180


def test_explicit_effort_and_output_settings_are_honored(monkeypatch):
    monkeypatch.setenv('GENESYS_REASONING_EFFORT','high');monkeypatch.setenv('GENESYS_OUTPUT_TOKEN_LIMIT','16000')
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))]))
    provider=OpenAIProvider(model='gpt-5-mini',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    provider.generate([{'role':'user','content':'Build app'}],[])
    assert create.call_args.kwargs['reasoning_effort']=='high'
    assert create.call_args.kwargs['max_completion_tokens']==16000


def test_draft_budget_reserves_real_time_for_build_repair_and_review(monkeypatch):
    monkeypatch.setattr('agent.progress.time.monotonic',lambda:100)
    assert draft_stage_deadline(1000)==520
    assert draft_stage_deadline(400)==280
    assert draft_stage_deadline(150)<150
    with model_request_scope(1000):
        with model_request_scope(draft_stage_deadline(1000)):
            assert model_request_timeout(900)==420
        assert model_request_timeout(900)==900


def test_review_timeout_preserves_complete_drafts_instead_of_starting_again():
    files={'src/App.jsx':'export default function App(){return <main>Complete design</main>}','src/projectLogic.js':'export function useProjectLogic(){return {}}'}
    def timeout(*_):raise TimeoutError('Synthetic review timeout')
    with pytest.raises(DraftReviewFailed) as caught:review_draft(files,{},'{}',SimpleNamespace(generate=timeout))
    assert caught.value.drafts==files
    assert 'do not restart from a scaffold' in str(caught.value)


def test_implementation_hands_off_with_time_for_real_browser_and_design_checks():
    from agent.build_context import verification_due
    assert verification_due(8,18,True,False,False,179)
    assert not verification_due(8,18,True,False,False,400)
    assert not verification_due(8,18,True,False,True,179)


def test_substantial_completed_design_reaches_protected_source_review():
    import json
    files={'src/App.jsx':'// detailed scene\n'+'const scene=1;\n'*4000}
    seen=[]
    def generate(messages,*_):
        seen.append(json.loads(messages[-1]['content'])['files'])
        assert messages[-1]['_preserve_complete_source']
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    assert review_draft(files,{},'{}',SimpleNamespace(generate=generate))==files
    assert seen==[files]


def test_one_worker_timeout_preserves_the_other_workers_completed_modules():
    import json,time
    from agent.parallel_build import draft_project
    def generate(messages,*_):
        instruction=messages[0]['content']
        if 'Plan a React user application' in instruction:
            return SimpleNamespace(text=json.dumps({'interface':'useProjectLogic returns score', 'requirements':['Play']}))
        if 'Build the responsive UI.' in instruction:
            return SimpleNamespace(text=json.dumps({'files':{'src/App.jsx':'export default function App(){return <main>Finished UI</main>}'}}))
        if 'Required files: src/styles.css' in instruction:
            return SimpleNamespace(text=json.dumps({'files':{'src/styles.css':'main {color:olive}'}}))
        raise TimeoutError('Synthetic logic worker timeout')
    with pytest.raises(DraftReviewFailed) as caught:
        draft_project('Synthetic game','{}',lambda _:SimpleNamespace(generate=generate),time.monotonic()+120)
    assert set(caught.value.drafts)=={'src/App.jsx','src/styles.css'}
    assert 'src/projectLogic.js' in str(caught.value)


def test_full_design_tier_is_separate_from_tool_execution_and_schema_planning(monkeypatch):
    monkeypatch.delenv('GENESYS_DESIGN_MODEL',raising=False)
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))]))
    provider=OpenAIProvider(model='gpt-5-mini',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    messages=[{'role':'system','content':'DEFAULT BUILD STANDARD: Build a complete product.'}]
    provider.generate(messages,[])
    assert create.call_args.kwargs['model']=='gpt-5.4'
    assert create.call_args.kwargs['max_completion_tokens']==24000
    provider.generate(messages,[{'type':'function','function':{'name':'save','parameters':{'type':'object'}}}])
    assert create.call_args.kwargs['model']=='gpt-5-mini'
    provider.generate_structured(messages,{'type':'object','properties':{},'required':[],'additionalProperties':False})
    assert create.call_args.kwargs['model']=='gpt-5-mini'
    monkeypatch.setenv('GENESYS_DESIGN_MODEL','gpt-5-mini')
    provider.generate(messages,[])
    assert create.call_args.kwargs['model']=='gpt-5-mini'


def test_design_requests_can_finish_their_output_allowance_within_the_draft_stage(monkeypatch):
    from agent.progress import DESIGN_REQUEST_TIMEOUT_SECONDS
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,_:messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
        message=SimpleNamespace(content='{}',tool_calls=[]))]))
    provider=OpenAIProvider(model='test-model',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    draft=[{'role':'system','content':'DEFAULT BUILD STANDARD: draft'},{'role':'user','content':'Build'}]
    provider.generate(draft,[])
    assert create.call_args.kwargs['timeout']==DESIGN_REQUEST_TIMEOUT_SECONDS>24000/70
    with model_request_scope(time.monotonic()+100):provider.generate(draft,[])
    assert create.call_args.kwargs['timeout']<=100


@pytest.fixture(autouse=True)
def plain_design_responses(monkeypatch):
    # These fakes return whole responses. Streaming is covered in test_build_upgrades.py.
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '0')
