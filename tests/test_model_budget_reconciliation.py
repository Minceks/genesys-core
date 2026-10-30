import time
import pytest
from agent.model_context import reserve_model_budget,reconcile_model_budget,ModelBudgetExceeded
from agent.beta_storage import connection


def used():
    with connection() as db:return db.execute('SELECT reserved FROM model_allowance WHERE day=?',(int(time.time()//86400),)).fetchone()[0]


def test_success_refunds_only_its_own_known_excess_and_hard_admission_still_applies(monkeypatch,tmp_path):
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'budget.sqlite3'))
    monkeypatch.setenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET','10000')
    first=reserve_model_budget(8500)
    with pytest.raises(ModelBudgetExceeded):reserve_model_budget(2000)
    reconcile_model_budget(first,500)
    assert used()==500
    reconcile_model_budget(first,0)
    assert used()==500
    pending=reserve_model_budget(9000)
    reconcile_model_budget(pending,None)
    assert used()==9500
    with pytest.raises(ModelBudgetExceeded):reserve_model_budget(501)


def test_openai_settles_the_reservation_even_when_provider_messages_are_normalized(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from agent.ai_provider import OpenAIProvider
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'budget.sqlite3'))
    monkeypatch.setenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET','100000')
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    response=SimpleNamespace(usage=SimpleNamespace(total_tokens=1234),choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))])
    provider=OpenAIProvider(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_:response))))
    provider.generate([{'role':'user','content':'A synthetic short request'}],[])
    assert used()==1234


def test_vision_reconciles_text_and_image_holds_and_refunds_an_unsent_request(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from agent.ai_provider import OpenAIProvider
    monkeypatch.setenv('GENESYS_JOB_DB',str(tmp_path/'vision-budget.sqlite3'))
    monkeypatch.setenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET','100000')
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda _:None)
    response=SimpleNamespace(usage=SimpleNamespace(total_tokens=2222),choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}'))])
    create=Mock(return_value=response)
    provider=OpenAIProvider(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    images=[('generated-desktop',b'\xff\xd8fixture'),('generated-phone',b'\xff\xd8fixture')]
    provider.review_images('Review synthetic images',{},images,{'type':'object','properties':{},'required':[],'additionalProperties':False})
    assert used()==2222
    monkeypatch.setenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET','10000')
    create.reset_mock()
    with pytest.raises(ModelBudgetExceeded):
        provider.review_images('Review synthetic images',{},images,{'type':'object','properties':{},'required':[],'additionalProperties':False})
    assert used()==2222 and not create.called
