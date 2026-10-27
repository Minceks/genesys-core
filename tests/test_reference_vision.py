import json
from types import SimpleNamespace

import pytest

from agent.reference_vision import understand_reference, reference_schema
from agent.reference_selection import live_site_url, inspect_game_frames, visual_candidates


def result(label='reference-desktop'):
    return {'observations':[{'image':label,'area':'composition',
        'evidence':'A large image occupies the right half beside a short left headline.',
        'adaptation':'Use an original project scene in a split composition, stacking on phones.'}],
        'implementationPlan':{key:'Use the observed hierarchy with original content; unobserved details remain unknown.'
                              for key in ['composition','typography','palette','imagery','components','mobile','gameUI']},
        'limits':['No interactions were exercised.']}


def test_interpretation_receives_real_pixels_and_not_private_project_context():
    seen=[]
    captures={'desktop':b'\x89PNGdesktop','phone':b'\x89PNGphone'}
    def review(instruction,context,images,schema):
        seen.append((instruction,context,images,schema))
        return SimpleNamespace(text=json.dumps(result()))
    reference={'url':'https://example.com/','viewports':[{'primaryHeading':{'fontSize':48}}]}
    value=understand_reference(reference,captures,'website',SimpleNamespace(review_images=review))
    assert value['status']=='analyzed'
    assert seen[0][2]==[('reference-desktop',captures['desktop']),('reference-phone',captures['phone'])]
    assert set(seen[0][1])=={'productType','evidenceKind','source','measurements','samples','scope','resourceCoverage','targetGenre','targetRendering'}
    assert value['images'][0]['sha256'] and 'base64' not in json.dumps(value)
    assert value['implementationPlan']['composition']


def test_no_pixels_or_vision_does_not_turn_titles_into_observations():
    provider=SimpleNamespace(review_images=lambda *_:pytest.fail('No actual captures'))
    assert understand_reference({'title':'Modern website'}, {},'website',provider)['status']=='unavailable'
    assert understand_reference({}, {'desktop':b'png','phone':b'png'},'website',None)['status']=='unavailable'


def test_unseen_image_cannot_be_cited_as_reference_evidence():
    provider=SimpleNamespace(review_images=lambda *_:SimpleNamespace(text=json.dumps(result('invented-image'))))
    with pytest.raises(ValueError,match='actual supplied images'):
        understand_reference({}, {'desktop':b'png','phone':b'png'},'app',provider)


def test_game_frames_have_correct_labels_and_do_not_imply_mobile_observation():
    seen=[]
    reference={'evidenceKind':'gameplay-media','captureLabels':{'desktop':'reference-game-frame-1','phone':'reference-game-frame-2'}}
    def review(instruction,context,images,schema):
        seen.append((instruction,context,images))
        return SimpleNamespace(text=json.dumps(result('reference-game-frame-1')))
    value=understand_reference(reference,{'desktop':b'one','phone':b'two'},'game',SimpleNamespace(review_images=review))
    assert value['status']=='analyzed' and seen[0][1]['evidenceKind']=='gameplay-media'
    assert [label for label,_ in seen[0][2]]==['reference-game-frame-1','reference-game-frame-2']
    assert 'not a responsive desktop/phone recording' in seen[0][0]


def test_awards_case_study_resolves_actual_site_and_not_gallery(monkeypatch):
    from agent import reference_selection as selection
    monkeypatch.setattr(selection,'public_get',lambda *_args,**_kw:(200,{},b'<a href="https://studio.example/">Visit Website</a>'))
    assert live_site_url('https://www.awwwards.com/sites/studio')=='https://studio.example/'
    monkeypatch.setattr(selection,'public_get',lambda *_args,**_kw:(200,{},b'<a href="http://127.0.0.1/">Visit Website</a>'))
    with pytest.raises(ValueError):live_site_url('https://www.awwwards.com/sites/studio')


def test_trending_site_is_selected_for_rendering_ahead_of_generic_reference():
    brief={'productType':'website','trendIntelligence':{'observations':[{'url':'https://www.awwwards.com/sites/studio'}]},
           'designResearch':{'references':[{'url':'https://linear.app/','status':'fetched'}]}}
    assert visual_candidates('Create a studio website',brief)==['https://www.awwwards.com/sites/studio','https://linear.app/']


def test_reference_vision_schema_respects_provider_limits():
    from agent.structured_schema import validate_schema_limits
    assert validate_schema_limits(reference_schema(['reference-desktop','reference-phone']))['enumValues']<100


def test_real_game_media_is_captured_as_frames_not_storefront_or_phone_ui(monkeypatch):
    from playwright.sync_api import sync_playwright
    from agent import reference_selection as selection
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':640,'height':360})
        page.set_content('<body style="background:#123"><h1 style="color:white">Game scene and HUD</h1></body>')
        image=page.screenshot(type='png');browser.close()
    reads=[]
    def read(url,**kwargs):
        reads.append(url)
        if '/api/appdetails' in url:
            return 200,{},json.dumps({'123':{'success':True,'data':{'screenshots':[
                {'path_full':'https://cdn.example/scene1.png'},{'path_full':'https://cdn.example/scene2.png'}]}}}).encode()
        return 200,{'Content-Type':'image/png'},image
    monkeypatch.setattr(selection,'public_get',read)
    brief={'trendIntelligence':{'observations':[{'url':'https://store.steampowered.com/app/123/'}]}}
    observation,captures=inspect_game_frames(brief)
    assert len(reads)==3 and len(captures)==2
    assert all(data.startswith(b'\x89PNG') for data in captures.values())
    assert observation['evidenceKind']=='gameplay-media' and observation['viewports']==[]
    assert observation['captureLabels']['phone']=='reference-game-frame-2'
    assert all('not an observed phone viewport' in frame['presentation'] for frame in observation['gameFrames'])


def test_game_media_rejects_private_image_addresses_before_fetch(monkeypatch):
    from agent import reference_selection as selection
    calls=[]
    def read(url,**kwargs):
        calls.append(url)
        return 200,{},json.dumps({'123':{'success':True,'data':{'screenshots':[
            {'path_full':'http://127.0.0.1/private'},{'path_full':'https://cdn.example/scene2.png'}]}}}).encode()
    monkeypatch.setattr(selection,'public_get',read)
    with pytest.raises(ValueError):
        inspect_game_frames({'trendIntelligence':{'observations':[{'url':'https://store.steampowered.com/app/123/'}]}})
    assert len(calls)==1


def test_specific_game_genre_does_not_fall_back_to_unrelated_popular_game(monkeypatch):
    from agent import reference_selection as selection
    reads=[]
    def blocked(url,**_):reads.append(url);return 403,{},b'Access denied'
    monkeypatch.setattr(selection,'public_get',blocked)
    with pytest.raises(ValueError,match='requested genre'):
        inspect_game_frames({'originalRequest':'A 2D puzzle game','trendIntelligence':{
            'observations':[{'url':'https://store.steampowered.com/app/730/'}]}})
    assert len(reads)==1 and 'tags=1664' in reads[0]


def test_explicit_game_reference_overrides_trending_and_genre_discovery(monkeypatch):
    from agent import reference_selection as selection
    reads=[]
    def unavailable(url,**_):
        reads.append(url);return 200,{},b'{"620":{"success":false}}'
    monkeypatch.setattr(selection,'public_get',unavailable)
    brief={'originalRequest':'A puzzle game','trendIntelligence':{'observations':[{'url':'https://store.steampowered.com/app/730/'}]}}
    with pytest.raises(ValueError,match='Game media was unavailable'):
        inspect_game_frames(brief,source_url='https://store.steampowered.com/app/620/')
    assert len(reads)==1 and 'appids=620' in reads[0] and '/search/' not in reads[0]


def test_rendered_capture_interpretation_is_persisted_and_handed_to_builder(monkeypatch):
    from agent import reference_inspection as inspection
    from agent.design_execution import design_execution
    captures={'desktop':b'\x89PNGone','phone':b'\x89PNGtwo'}
    observation={'status':'observed','url':'https://example.com/','viewports':[],
                 'rea':{'status':'captured'},'scope':'Real fixture capture'}
    stored=[]
    monkeypatch.setattr(inspection,'inspect_reference',lambda *_:(dict(observation),captures))
    monkeypatch.setattr('agent.visual_evidence.save_review',lambda project,quality,images:stored.append((quality,images)) or {'id':'visual-ref'})
    provider=SimpleNamespace(review_images=lambda *_:SimpleNamespace(text=json.dumps(result())))
    brief={'productType':'website','designResearch':{'references':[{'url':'https://example.com/','status':'fetched'}]}}
    ref=inspection.prepare_reference(SimpleNamespace(project_id='test'),'Build a website',brief,vision_provider=provider)
    assert ref['visualUnderstanding']['status']=='analyzed' and ref['reviewId']=='visual-ref'
    assert stored[0][0]['reference']['visualUnderstanding']==ref['visualUnderstanding']
    execution=design_execution({**brief,'referenceAnalysis':ref})
    assert execution['referenceAdaptation']['observedDesign']['implementationPlan']==ref['visualUnderstanding']['implementationPlan']


def test_vision_outage_keeps_actual_measurements_without_fabricating_analysis(monkeypatch):
    from agent import reference_inspection as inspection
    monkeypatch.setattr(inspection,'inspect_reference',lambda *_:({'status':'observed','url':'https://example.com/',
        'viewports':[{'primaryHeading':{'fontSize':48}}],'rea':{},'scope':'Measured'}, {'desktop':b'png','phone':b'png'}))
    monkeypatch.setattr('agent.visual_evidence.save_review',lambda *_:{'id':'ref'})
    def unavailable(*_):raise RuntimeError('Vision unavailable')
    brief={'productType':'website','designResearch':{'references':[{'url':'https://example.com/','status':'fetched'}]}}
    ref=inspection.prepare_reference(SimpleNamespace(project_id='test'),'Build a website',brief,vision_provider=SimpleNamespace(review_images=unavailable))
    assert ref['status']=='observed' and ref['viewports'][0]['primaryHeading']['fontSize']==48
    assert ref['visualUnderstanding']['status']=='unavailable'
