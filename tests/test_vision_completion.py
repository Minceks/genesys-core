from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from agent.ai_provider import OpenAIProvider
from agent.beta_storage import connection


IMAGES=[('generated-desktop',b'\xff\xd8fixture'),('generated-phone',b'\xff\xd8fixture')]
SCHEMA={'type':'object','properties':{},'required':[],'additionalProperties':False}


def response(finish,text,tokens):
    return SimpleNamespace(usage=SimpleNamespace(total_tokens=tokens,completion_tokens=tokens),
        choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=text))])


def setup(monkeypatch,tmp_path,responses):
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'vision.sqlite3'))
    monkeypatch.setenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET','500000')
    record=Mock();monkeypatch.setattr('agent.ai_provider.record_model_usage',record)
    create=Mock(side_effect=responses)
    provider=OpenAIProvider(model='gpt-5.4',client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return provider,create,record


@pytest.mark.parametrize('instruction,limits',[
    ('DEFAULT BUILD STANDARD: GAME TARGETED POLISH.',[16000,24000]),
    ('Review these screenshots',[6000,12000])])
def test_truncated_vision_is_discarded_and_retried_with_separately_settled_budget(monkeypatch,tmp_path,instruction,limits):
    provider,create,record=setup(monkeypatch,tmp_path,[response('length','PRIVATE PARTIAL JSON',1500),response('stop','{}',2000)])
    assert provider.review_images(instruction,{'source':'complete fixture'},IMAGES,SCHEMA).text=='{}'
    assert [c.kwargs['max_completion_tokens'] for c in create.call_args_list]==limits
    assert record.call_count==2
    for call in create.call_args_list:
        assert 'PRIVATE PARTIAL JSON' not in str(call.kwargs['messages'])
        assert 'complete fixture' in str(call.kwargs['messages'])
    with connection() as db:assert db.execute('select sum(reserved) from model_allowance').fetchone()[0]==3500


def test_exhausted_vision_retry_never_applies_partial_game_source(monkeypatch,tmp_path):
    from agent.game_build import polish_game
    provider,create,_=setup(monkeypatch,tmp_path,[response('length','{"edits":[',1500),response('length','{"edits":[',2000)])
    files={'src/styles.css':'main { color:green; }'};before=dict(files)
    class Workspace:
        def read_file(self,path):return {'content':files.get(path,'')}
        def write_file(self,*_):raise AssertionError('Incomplete responses must never write source')
    with pytest.raises(RuntimeError,match='bounded retry; source was preserved'):
        polish_game(Workspace(),'Correct screenshot finding',provider,IMAGES)
    assert create.call_count==2 and files==before


def test_other_vision_failures_report_reason_without_retrying_or_dumping_content(monkeypatch,tmp_path):
    provider,create,_=setup(monkeypatch,tmp_path,[response('content_filter','PRIVATE CONTENT',100)])
    with pytest.raises(RuntimeError,match='finish_reason=content_filter') as failure:
        provider.review_images('Review',{},IMAGES,SCHEMA)
    assert create.call_count==1 and 'PRIVATE CONTENT' not in str(failure.value)


def test_empty_transient_completion_can_retry_but_refusal_cannot(monkeypatch,tmp_path):
    provider,create,_=setup(monkeypatch,tmp_path,[response('stop','',100),response('stop','{}',200)])
    assert provider.review_images('Review',{},IMAGES,SCHEMA).text=='{}' and create.call_count==2
    for finish in ['stop','length']:
        refused=response(finish,None,100)
        refused.choices[0].message.refusal='PRIVATE REFUSAL'
        create.reset_mock();create.side_effect=[refused]
        with pytest.raises(RuntimeError,match='finish_reason=refusal'):
            provider.review_images('Review',{},IMAGES,SCHEMA)
        assert create.call_count==1
