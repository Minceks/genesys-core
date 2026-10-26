import json
import time
from types import SimpleNamespace

import pytest

from agent import design_research, product_design
from agent.engineering_strategy import engineering_strategy, SENIOR_ENGINEERING_STANDARD
from agent.trend_intelligence import discovery_entries, trend_context, FRESH_SECONDS


def test_atom_launches_keep_dates_and_safe_source_links_without_following_destinations():
    feed=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Focused team calendar</title>
        <link href="https://www.producthunt.com/posts/calendar?token=secret#tracking"/>
        <published>2026-10-26T10:00:00Z</published></entry>
        <entry><title>External link</title><link href="https://private.example/app"/></entry>
        <entry><title>Unsafe</title><link href="javascript:alert(1)"/></entry></feed>'''
    entries=discovery_entries(feed,'https://www.producthunt.com/feed','application/atom+xml')
    assert len(entries)==1
    assert entries[0]['url']=='https://www.producthunt.com/posts/calendar'
    assert entries[0]['publishedAt']>0
    assert 'secret' not in json.dumps(entries)


@pytest.mark.parametrize('body',[b'<!DOCTYPE feed [<!ENTITY x "injected">]><feed/>',
    '<!DOCTYPE feed [<!ENTITY x "injected">]><feed/>'.encode('utf-16'), b'<feed><bad></feed>'])
def test_unsafe_or_invalid_xml_is_a_research_failure(body):
    with pytest.raises(ValueError):
        discovery_entries(body,'https://www.producthunt.com/feed','application/atom+xml')


def test_bounded_partial_feed_and_rss_are_supported():
    body=b'<feed>'+b''.join(f'<entry><title>Launch {i}</title><link href="https://www.producthunt.com/posts/{i}"/></entry>'.encode() for i in range(30))
    assert len(discovery_entries(body,'https://www.producthunt.com/feed','application/atom+xml'))==8
    rss=b'<rss><channel><item><title>Tool</title><link>https://www.producthunt.com/posts/tool</link><pubDate>Mon, 26 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    assert discovery_entries(rss,'https://www.producthunt.com/feed','application/rss+xml')[0]['publishedAt']>0


@pytest.mark.parametrize('source,html,expected',[
    ('https://www.awwwards.com/websites/',b'<a href="/websites/">Menu</a><a href="/sites/studio">Studio project</a>', 'Studio project'),
    ('https://itch.io/games/new-and-popular',b'<a href="/games">Browse</a><a href="https://author.itch.io/puzzle">A quiet puzzle</a>', 'A quiet puzzle'),
    ('https://store.steampowered.com/charts/mostplayed',b'<a href="https://store.steampowered.com/app/123/Game/">Game title</a>', 'Game title'),
])
def test_html_discovery_extracts_actual_listings_and_not_navigation(source,html,expected):
    entries=discovery_entries(html,source,'text/html')
    assert [e['title'] for e in entries]==[expected]


def test_gallery_uses_actual_accessible_card_name_without_inventing_visual_details():
    entries=discovery_entries(b'<a href="/sites/studio" aria-label="Studio identity"><img alt="Thumbnail"></a>',
                              'https://www.awwwards.com/websites/','text/html')
    assert entries[0]['title']=='Studio identity'
    assert 'colors' not in entries[0] and 'layout' not in entries[0]


def test_steam_snapshot_resolves_only_three_valid_numeric_ids_and_keeps_platform_scope():
    from agent.trend_intelligence import steam_entries
    calls=[]
    body=json.dumps({'response':{'rollup_date':1000000,'ranks':[
        {'appid':i,'rank':i} for i in range(1,10)]}}).encode()
    entries=steam_entries(body,lambda appid:calls.append(appid) or f'Game {appid}')
    assert calls==[1,2,3] and [e['platformRank'] for e in entries]==[1,2,3]
    assert all(e['publishedAt']==1000000 and 'not a global' in e['metric'] for e in entries)
    body=json.dumps({'response':{'rollup_date':1000000,'ranks':[{'appid':'../../private','rank':1}]}}).encode()
    assert steam_entries(body,lambda _:pytest.fail('Invalid app IDs cannot become requests'))==[]


def test_positive_cache_expires_after_six_hours(monkeypatch):
    url='https://www.producthunt.com/feed'
    monkeypatch.setattr(design_research,'_cache',{url:{'url':url,'status':'fetched','fetchedAt':time.time()-FRESH_SECONDS-1}})
    calls=[]
    def offline(*_,**__):calls.append(True);raise design_research.httpx.ConnectError('Offline')
    monkeypatch.setattr(design_research.httpx,'stream',offline)
    assert design_research.fetch_reference(url)['status']=='unavailable' and calls==[True]


def test_stale_future_and_undated_fetches_never_become_current_evidence():
    now=2000000
    entry={'title':'Observed listing','url':'https://www.producthunt.com/posts/tool','publishedAt':None}
    refs=[{'url':'source','status':'fetched','fetchedAt':now-age,'entries':[entry]} for age in [FRESH_SECONDS+1,-1]]
    refs.append({'url':'source','status':'fetched','entries':[entry]})
    assert trend_context({'references':refs},'app',now)['status']=='curated-fallback'
    fresh={'url':'source','status':'fetched','fetchedAt':now,'entries':[entry]}
    result=trend_context({'references':[fresh]},'app',now)
    assert result['status']=='recent-public-signals' and len(result['observations'])==1
    assert 'No global popularity ranking' in result['evidenceScope']
    for date in (now+86400,now-31*86400):
        fresh['entries']=[dict(entry,publishedAt=date)]
        assert trend_context({'references':[fresh]},'app',now)['observations']==[]


def test_live_feed_fetch_is_bounded_cached_and_does_not_send_user_context(monkeypatch):
    calls=[]
    class Response:
        headers={'content-type':'application/atom+xml'}
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def raise_for_status(self):pass
        def iter_bytes(self):
            yield b'<feed><entry><title>Current tool</title><link href="https://www.producthunt.com/posts/tool"/></entry></feed>'
    def stream(method,url,**kwargs):
        calls.append((method,url,kwargs));return Response()
    monkeypatch.setattr(design_research.httpx,'stream',stream)
    monkeypatch.setattr(design_research,'_cache',{})
    url='https://www.producthunt.com/feed'
    first=design_research.fetch_reference(url)
    second=design_research.fetch_reference(url)
    assert first['status']=='fetched' and first['entries'][0]['title']=='Current tool'
    assert first['discoveryOnly'] and first==second and len(calls)==1
    assert calls[0][2]['follow_redirects'] is False
    assert set(calls[0][2]['headers'])=={'User-Agent'}
    assert 'prompt' not in calls[0][2] and 'authorization' not in str(calls).lower()


def test_unavailable_feed_and_negative_cache_do_not_stop_builds(monkeypatch):
    calls=[]
    def unavailable(*args,**kwargs):
        calls.append(True);raise design_research.httpx.ConnectError('Offline')
    monkeypatch.setattr(design_research.httpx,'stream',unavailable)
    monkeypatch.setattr(design_research,'_cache',{})
    first=design_research.fetch_reference('https://www.producthunt.com/feed')
    assert design_research.fetch_reference('https://www.producthunt.com/feed')==first
    assert first['status']=='unavailable' and len(calls)==1


def test_senior_strategy_preserves_user_genre_and_targeted_edit_scope():
    brief={'productType':'game','buildIntent':'edit-product','originalRequest':'A minimal retro puzzle game, no animation'}
    result=engineering_strategy(brief,'Fix score persistence',{'status':'recent-public-signals'})
    assert result['mode']=='preserve-and-repair'
    assert result['objective']==brief['originalRequest']
    assert 'repair only' in result['decisionContract']['scope']
    assert all(item['basis'].startswith('Curated') for item in result['candidatePatterns'])
    assert 'choose zero' in SENIOR_ENGINEERING_STANDARD
    assert 'User requirements' in SENIOR_ENGINEERING_STANDARD


def test_product_brief_carries_evidence_to_execution_without_refetching_on_fixes(monkeypatch):
    calls=[]
    def research(prompt,product):
        calls.append(prompt)
        return {'family':product,'references':[{'url':'https://www.producthunt.com/feed','status':'fetched','fetchedAt':time.time(),
            'discoveryOnly':True,'entries':[{'title':'New launch','url':'https://www.producthunt.com/posts/launch','publishedAt':None}]}]}
    monkeypatch.setattr(design_research,'research_design',research)
    class Workspace:
        project_id='senior-strategy'
        content=''
        def read_file(self,_):return {'status':'success','content':self.content}
        def write_file(self,_,content):self.content=content;return {'status':'success'}
    w=Workspace()
    first=product_design.prepare_design(w,'Create a minimal task app')
    assert first['engineeringStrategy']['mode']=='design-and-build'
    assert first['trendIntelligence']['status']=='recent-public-signals'
    assert first['designExecution']['engineeringDecisions']==first['engineeringStrategy']['decisionContract']
    assert first['designExecution']['trendAdaptation']['status']=='recent-public-signals'
    fixed=product_design.prepare_design(w,'Fix the save button')
    assert fixed['engineeringStrategy']['mode']=='preserve-and-repair' and len(calls)==1
    assert fixed['visualSystem']==first['visualSystem']


def test_explicit_trend_refresh_is_a_design_request_but_negation_is_not():
    from agent.trend_intelligence import trend_refresh_requested
    assert trend_refresh_requested('Refresh this website using the latest design trends')
    assert not trend_refresh_requested("Do not follow design trends; keep the retro look")
    assert not trend_refresh_requested('Fix an error after following trends')
    strategy=engineering_strategy({'buildIntent':'edit-product','productType':'website'},'Follow current design trends',{})
    assert strategy['mode']=='design-and-build'


def test_discovery_galleries_are_not_used_as_the_game_visual_reference(monkeypatch):
    from agent.reference_inspection import prepare_reference
    monkeypatch.setattr('agent.reference_inspection.inspect_reference',lambda *_:pytest.fail('A game listing is not a playable-scene reference'))
    brief={'designResearch':{'references':[{'url':'https://itch.io/games/new-and-popular','status':'fetched','discoveryOnly':True}]}}
    assert prepare_reference(SimpleNamespace(),'Create a playable puzzle game',brief) is None


def test_strategy_and_evidence_reach_specification_and_review(monkeypatch):
    from agent.build_spec import prepare_build_spec
    from agent.parallel_build import review_draft
    from agent.design_quality import BUILD_STANDARD
    assert SENIOR_ENGINEERING_STANDARD in BUILD_STANDARD
    strategy={'mode':'design-and-build','decisionContract':{'trendAdaptation':'Choose relevant evidence'}}
    trends={'status':'curated-fallback','observations':[]}
    brief={'productType':'app','engineeringStrategy':strategy,'trendIntelligence':trends}
    seen=[]
    class Files:
        def read_file(self,_):return {'content':'{}'}
        def write_file(self,*_):return {'status':'success'}
    def specify(messages,*_):
        seen.append(json.loads(messages[1]['content'])['designBrief'])
        return SimpleNamespace(text=json.dumps({'pages':['Tasks'],'requirements':[{'id':'R1','name':'Add task','scope':'browser','acceptance':'Enter a title, add a task and reload to confirm it persists.'}]}))
    prepare_build_spec(Files(),'Create a task app',brief,SimpleNamespace(generate=specify))
    def review(messages,*_):
        seen.append(json.loads(messages[1]['content'])['design'])
        return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
    review_draft({'src/App.jsx':'export default ()=>null'}, {},json.dumps({'designBrief':brief}),SimpleNamespace(generate=review))
    assert all(item['engineeringStrategy']==strategy and item['trendIntelligence']==trends for item in seen)
