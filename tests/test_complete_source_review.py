import json
from types import SimpleNamespace
import pytest
from agent import model_context
from agent.parallel_build import review_draft,DraftReviewFailed


def test_review_compacts_design_without_truncating_source_or_interfaces(monkeypatch):
    monkeypatch.setenv('GENESYS_INPUT_TOKEN_LIMIT','4000')
    monkeypatch.setattr(model_context,'reserve_model_budget',lambda *_:None)
    files={'src/App.jsx':'export default function App(){return <button>Play</button>}','src/projectLogic.js':'export function useProjectLogic(){return {score:0}}'}
    source=json.dumps({'designBrief':{'trendIntelligence':{'notes':'decorative guidance '*10000}},'files':{'src/helper.js':'export const helper=42'}})
    class Provider:
        def generate(self,messages,*_):
            bounded=model_context.bounded_messages(messages,[])
            assert all('_preserve_complete_source' not in message for message in bounded)
            context=json.loads(bounded[-1]['content'])
            assert context['files']==files
            assert context['existingFiles']=={'src/helper.js':'export const helper=42'}
            assert context['plan']=={'interface':'useProjectLogic returns score'}
            assert context['omittedDesignFields']==['trendIntelligence']
            return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    assert review_draft(files,{'interface':'useProjectLogic returns score'},source,Provider())==files


def test_oversized_source_retains_drafts_and_is_never_sent_as_truncated_review(monkeypatch):
    monkeypatch.setenv('GENESYS_INPUT_TOKEN_LIMIT','2000')
    monkeypatch.setattr(model_context,'reserve_model_budget',lambda *_:None)
    files={'src/App.jsx':'export default function App(){return "'+('unicode café 🎮 '*2000)+'"}'}
    class Provider:
        called=False
        def generate(self,messages,*_):
            model_context.bounded_messages(messages,[])
            self.called=True
            raise AssertionError('Oversized review must fail before transport')
    provider=Provider()
    with pytest.raises(DraftReviewFailed) as caught:review_draft(files,{},'{}',provider)
    assert caught.value.drafts==files and not provider.called


def test_empty_draft_is_rejected_before_model_review():
    provider=SimpleNamespace(generate=lambda *_:pytest.fail('Empty draft must not be reviewed'))
    with pytest.raises(ValueError,match='nonempty'):review_draft({}, {}, '{}',provider)


def test_repair_timeout_gets_one_larger_bounded_attempt():
    import time
    from playwright.sync_api import sync_playwright
    from agent.functional_verification import verify_functions
    from agent.progress import model_request_scope,model_deadline
    class Provider:
        calls=0
        def generate(self,*_):
            self.calls+=1
            assert 60 < model_deadline.get()-time.monotonic() <= 90
            raise TimeoutError('Synthetic planner timeout')
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.route('https://fixture.test/**',lambda route:route.fulfill(content_type='text/html',body='<button>Play</button>'))
            page.goto('https://fixture.test/')
            provider=Provider()
            with model_request_scope(time.monotonic()+240):
                result=verify_functions(page,'Play game',provider,attempt=1,_repair_round=1)
            assert provider.calls==1
            assert result['issues']==[] and result['unverifiedCore']
        finally:browser.close()
