import json
from types import SimpleNamespace

import pytest

from agent.visual_review import VisualPolishLoop,review_screenshots


IMAGES=[('generated-desktop',b'\xff\xd8desktop'),('generated-phone',b'\xff\xd8phone')]


def assessment(major=False):
    return {'assessment':'needs_polish' if major else 'ready','summary':'Review of supplied screenshots only.',
        'findings':[{'screenshot':'generated-phone','area':'Hero','evidence':'Headline and image overlap in the phone screenshot.',
                     'correction':'Stack the hero text and image at phone widths.','severity':'major'}] if major else []}


def test_vision_adapter_sends_actual_image_content_and_accounts_for_usage(monkeypatch):
    from agent.ai_provider import OpenAIProvider
    calls=[];usage=[];budgets=[]
    monkeypatch.setattr('agent.ai_provider.bounded_messages',lambda messages,tools,**kwargs:messages)
    monkeypatch.setattr('agent.model_context.reserve_model_budget',lambda tokens:budgets.append(tokens))
    monkeypatch.setattr('agent.ai_provider.record_model_usage',lambda response:usage.append(response))
    response=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(assessment())))])
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:calls.append(kw) or response)))
    provider=OpenAIProvider(model='test-vision-model',client=client)
    review=review_screenshots(provider,{'productType':'website'},IMAGES)
    content=calls[0]['messages'][1]['content']
    images=[part for part in content if part['type']=='image_url']
    assert len(images)==2 and all(part['image_url']['url'].startswith('data:image/jpeg;base64,') for part in images)
    assert calls[0]['max_completion_tokens']==6000 and calls[0]['timeout']==90
    assert calls[0]['response_format']['json_schema']['strict'] is True
    assert len(usage)==1 and budgets==[12000]
    assert review['status']=='ready' and len(review['screenshots'])==2
    assert 'base64' not in json.dumps(review)


def test_one_polish_then_one_recheck_is_bounded_and_cached_by_source():
    loop=VisualPolishLoop();calls=[]
    def review(previous):
        calls.append(previous)
        return {'status':'needs_polish','summary':'Phone overlap remains.','findings':assessment(True)['findings']}
    first,repair=loop.run('source-one',review)
    assert repair and first['sourceFingerprint']=='source-one'
    same,repair=loop.run('source-one',review)
    assert same==first and not repair and len(calls)==1
    second,repair=loop.run('source-two',review)
    assert not repair and second['status']=='needs_polish' and len(calls)==2
    exhausted,repair=loop.run('source-three',review)
    assert not repair and exhausted['status']=='unavailable' and len(calls)==2


def test_successful_recheck_receives_original_findings_without_prepassing():
    loop=VisualPolishLoop()
    loop.run('before',lambda _:dict(status='needs_polish',summary='Overlap',findings=assessment(True)['findings']))
    def review(previous):
        assert previous==assessment(True)['findings']
        return {'status':'ready','summary':'The captured overlap is resolved.','findings':[]}
    result,repair=loop.run('after',review)
    assert result['status']=='ready' and not repair


def test_provider_failure_is_unavailable_not_visual_approval_or_repair():
    loop=VisualPolishLoop()
    def unavailable(_):raise RuntimeError('Rate limited')
    result,repair=loop.run('source',unavailable)
    assert result['status']=='unavailable' and not repair
    result,repair=loop.run('other',lambda _:pytest.fail('No retry loop for a provider failure'))
    assert result['status']=='unavailable' and not repair


@pytest.mark.parametrize('invalid', ['missing-image','contradictory-verdict','missing-evidence'])
def test_unsupported_judgments_do_not_become_repair_instructions(invalid):
    value=assessment(True)
    if invalid=='missing-image':value['findings'][0]['screenshot']='unseen-cart'
    if invalid=='contradictory-verdict':value['assessment']='ready'
    if invalid=='missing-evidence':value['findings'][0]['evidence']=''
    provider=SimpleNamespace(review_images=lambda *_:SimpleNamespace(text=json.dumps(value)))
    with pytest.raises(ValueError):review_screenshots(provider,{},IMAGES)


def test_reference_images_are_context_not_targets_for_application_repairs():
    value=assessment(True);value['findings'][0]['screenshot']='reference-desktop'
    provider=SimpleNamespace(review_images=lambda *_:SimpleNamespace(text=json.dumps(value)))
    with pytest.raises(ValueError):review_screenshots(provider,{},IMAGES+[('reference-desktop',b'\x89PNGfixture')])


def test_report_keeps_visual_judgment_separate_from_function_passes():
    from agent.verification_report import verification_report
    visual={'status':'needs_polish','summary':'Spacing remains inconsistent.','findings':assessment(True)['findings']}
    report=verification_report({'status':'success','visualReview':visual,'suggestions':['Review remaining phone spacing']},
        {'testedInteractions':['Create and reload a record']})
    assert report['visualReview']['status']=='needs_polish'
    assert report['passed']==['Desktop and mobile layout','Create and reload a record']
    assert report['manualReview']==['Review remaining phone spacing']


def test_browser_delivers_real_desktop_and_phone_screenshots_to_the_reviewer(monkeypatch):
    from agent import browser
    seen=[];records=[]
    page_html='''<html><body style="margin:0;background:#f6f4ef;font:18px system-ui;color:#222"><main style="padding:24px;max-width:1000px;margin:auto"><section style="min-height:900px"><h1 style="font-size:48px">A considered studio</h1><p>Explore selected projects and learn about the studio approach.</p><button style="padding:14px 24px;background:#284f40;color:white;border:0;border-radius:8px">Explore work</button></section><section style="min-height:900px"><h2>Selected projects</h2><p>Supporting work and project context.</p></section></main></body></html>'''
    import urllib.parse
    workspace=SimpleNamespace(start_preview=lambda:{'url':'data:text/html,'+urllib.parse.quote(page_html)},build_fingerprint=lambda:'fixture-source')
    monkeypatch.setattr(browser,'get_workspace',lambda _:workspace)
    def review(*args):
        seen.append(args[2])
        return SimpleNamespace(text=json.dumps(assessment()))
    monkeypatch.setattr('agent.ai_provider.OpenAIProvider',lambda **_:SimpleNamespace(review_images=review))
    monkeypatch.setattr('agent.visual_evidence.save_review',lambda project,quality,captures:records.append(quality) or {'id':'fixture-review'})
    try:
        result=browser.get_browser('vision-fixture').visual_quality(vision_loop=VisualPolishLoop(),design_brief={'productType':'website'})
        assert result['status']=='success',result
        assert result['visualReview']['status']=='ready' and not result['visualPolishRequested']
        assert [label for label,_ in seen[0]]==['generated-desktop','generated-phone']
        assert all(data.startswith(b'\xff\xd8') and len(data)>1000 for _,data in seen[0])
        assert records[0]['visualReview']['screenshots'][0]['sha256']
        assert all(len(samples) >= 2 for samples in result['visualReview']['capturedViews'].values())
        assert result['visualReview']['capturedViews']['generated-phone'][1]['scrollY'] > 0
    finally:browser.stop_browser('vision-fixture')
