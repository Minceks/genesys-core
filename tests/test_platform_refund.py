import pytest
import cloud_agent


class Limiter:
    def __init__(self):self.released=[]
    def release(self,reservation,refund=False):self.released.append((reservation,refund))


@pytest.mark.parametrize('result,refund',[
    ({'status':'error','errorType':'agent_timeout'},True),
    ({'status':'error','errorType':'ai_request'},True),
    ({'status':'error','errorType':'workspace_unavailable'},True),
    ({'status':'error','errorType':'model_budget'},False),
    ({'status':'error','errorType':'build'},False),
    ({'status':'success'},False),
])
def test_only_platform_failures_return_the_build_allowance(monkeypatch,result,refund):
    limiter=Limiter()
    monkeypatch.setattr(cloud_agent,'usage_limiter',limiter)
    monkeypatch.setattr(cloud_agent,'_execute_agent_request',lambda *_:dict(result))
    cloud_agent.execute_agent_request('Build','project',[],('user',1.0))
    assert limiter.released==[(('user',1.0),refund)]


def test_unexpected_exception_still_releases_the_active_build_without_refund(monkeypatch):
    limiter=Limiter()
    def fail(*_):raise RuntimeError('Interrupted')
    monkeypatch.setattr(cloud_agent,'usage_limiter',limiter)
    monkeypatch.setattr(cloud_agent,'_execute_agent_request',fail)
    with pytest.raises(RuntimeError):cloud_agent.execute_agent_request('Build','project',[],('user',1.0))
    assert limiter.released==[(('user',1.0),False)]
