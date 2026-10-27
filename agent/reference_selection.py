"""Resolve discovery listings to real public interfaces or actual game frames."""
import base64
from html.parser import HTMLParser
import json
import re
import time
from urllib.parse import urlsplit
from .reference_network import public_get, reference_url


class LiveSiteLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.current=None;self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            values=dict(attrs)
            self.current={'href':values.get('href',''),'text':values.get('aria-label') or values.get('title') or ''}
    def handle_data(self,value):
        if self.current is not None:self.current['text']=(self.current['text']+' '+value)[:200]
    def handle_endtag(self,tag):
        if tag!='a' or self.current is None:return
        if re.search(r'\bvisit\b.{0,20}\b(?:site|website)\b|\blive website\b',self.current['text'],re.I):
            self.links.append(self.current['href'])
        self.current=None


def live_site_url(url):
    """An awards directory is not the nominated site's rendered interface."""
    url=reference_url(url)
    if urlsplit(url).hostname!='www.awwwards.com' or not urlsplit(url).path.startswith('/sites/'):
        return url
    status,headers,body=public_get(url,timeout=3,limit=2_000_000)
    if status!=200:raise ValueError('Discovery detail was unavailable')
    parser=LiveSiteLinks();parser.feed(body.decode('utf-8',errors='replace'))
    for link in parser.links[:8]:
        try:
            candidate=reference_url(link)
            if urlsplit(candidate).hostname not in {'www.awwwards.com','awwwards.com'} and not urlsplit(candidate).query:
                return candidate
        except ValueError:pass
    raise ValueError('No actual public website destination was found')


def visual_candidates(prompt,brief):
    if brief.get('productType')=='app':
        if re.search(r'\b(todo|task manager|task app)\b',prompt,re.I):
            return ['https://todomvc.com/examples/react/dist/']
        if re.search(r'\b(whiteboard|drawing|diagram)\b',prompt,re.I):
            return ['https://excalidraw.com/']
    discoveries=[item['url'] for item in brief.get('trendIntelligence',{}).get('observations',[])
                 if 'www.awwwards.com/sites/' in item.get('url','')][:1]
    references=[item['url'] for item in brief.get('designResearch',{}).get('references',[])
                if item.get('status')=='fetched' and not item.get('discoveryOnly')]
    return list(dict.fromkeys(discoveries+references))[:2]


def inspect_game_frames(brief, source_url=None):
    """Read real game screenshots; never mislabel storefront chrome as gameplay."""
    entries=brief.get('trendIntelligence',{}).get('observations',[])
    request=str(brief.get('originalRequest') or brief.get('latestRequest') or '')
    genres=[('puzzle','1664',r'\bpuzzle\b'),('platformer','1625',r'\bplatformer\b'),
            ('survival','1662',r'\b(survival|zombie)\b'),('racing','699',r'\bracing\b'),
            ('shooter','1774',r'\b(shooter|fps)\b'),('strategy','9',r'\bstrategy\b')]
    genre=next(((name,tag) for name,tag,pattern in genres if re.search(pattern,request,re.I)),None)
    if source_url:
        if not re.match(r'^https://store\.steampowered\.com/app/\d+/',source_url):
            raise ValueError('Unsupported explicit game media source')
        candidate={'url':source_url}
    elif genre:
        tags=genre[1]+(',3871' if brief.get('subtype')=='2D' else '')
        status,_,body=public_get('https://store.steampowered.com/search/?tags='+tags+'&filter=topsellers',timeout=3,limit=2_000_000)
        ids=re.findall(rb'data-ds-appid=[\"\x27](\d+)[\"\x27]',body) if status==200 else []
        if not ids:raise ValueError('No rendered game examples matched the requested genre')
        candidate={'url':'https://store.steampowered.com/app/'+ids[0].decode('ascii')+'/'}
    else:
        candidate=next((item for item in entries if re.match(r'^https://store\.steampowered\.com/app/\d+/',item.get('url',''))),None)
    if not candidate:raise ValueError('No public game screenshot source is available')
    appid=re.search(r'/app/(\d+)/',candidate['url']).group(1)
    if not 0<int(appid)<2**31:raise ValueError('Invalid game source ID')
    url=f'https://store.steampowered.com/api/appdetails?appids={appid}&filters=screenshots'
    status,_,body=public_get(url,timeout=3,limit=500_000)
    record=json.loads(body).get(appid,{})
    if status!=200 or record.get('success') is not True:raise ValueError('Game media was unavailable')
    sources=[item.get('path_full') for item in record.get('data',{}).get('screenshots',[])[:2]]
    if len(sources)!=2:raise ValueError('Two actual game frames are required')
    images=[]
    for source in sources:
        source=reference_url(source)
        status,headers,data=public_get(source,timeout=3,limit=2_000_000)
        if status!=200 or not (data.startswith(b'\x89PNG') or data.startswith(b'\xff\xd8')):
            raise ValueError('Game frame is not a bounded PNG/JPEG')
        images.append((source,data))
    from playwright.sync_api import sync_playwright
    captures={};frames=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            context=browser.new_context(viewport={'width':1280,'height':720},service_workers='block')
            context.route('**/*',lambda route:route.abort())
            page=context.new_page()
            for index,((source,data),slot) in enumerate(zip(images,('desktop','phone')),1):
                mime='image/png' if data.startswith(b'\x89PNG') else 'image/jpeg'
                encoded=base64.b64encode(data).decode('ascii')
                page.set_content(f'<body style="margin:0;background:#111"><img style="width:1280px;height:720px;object-fit:contain" src="data:{mime};base64,{encoded}"></body>')
                page.locator('img').evaluate('(img)=>img.decode()')
                png=page.screenshot(type='png')
                if len(png)>2_000_000:raise ValueError('Game frame capture exceeds image budget')
                captures[slot]=png
                frames.append({'label':f'reference-game-frame-{index}','source':source.split('?')[0],
                               'presentation':'Source game still scaled to fit; not an observed phone viewport.'})
        finally:browser.close()
    return {'version':1,'status':'observed','evidenceKind':'gameplay-media','url':candidate['url'],
            'targetGenre':genre[0] if genre else 'unspecified',
            'targetRendering':brief.get('subtype') if brief.get('subtype') in {'2D','2.5D','3D'} else 'unspecified',
            'capturedAt':time.time(),'viewports':[],'gameFrames':frames,
            'captureLabels':{'desktop':'reference-game-frame-1','phone':'reference-game-frame-2'},
            'rea':{'status':'not-applicable','reason':'Actual game image media, not a web-page interaction capture.'},
            'scope':'Two actual public game stills. Scene/HUD appearance only; gameplay, motion and mobile behavior were not tested.'},captures
