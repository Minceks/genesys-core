"""Objective layout/style checks; these do not claim to measure aesthetic taste."""

SNAPSHOT_SCRIPT = """async () => {
  const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const controls = [...document.querySelectorAll('button,input:not([type=hidden]),select,textarea')].filter(visible);
  const styledControls = controls.filter(el => {
    const s = getComputedStyle(el);
    return parseFloat(s.paddingTop) >= 7 || parseFloat(s.borderRadius) >= 4 || parseFloat(s.height) >= 36;
  }).length;
  const containers = [...document.querySelectorAll('main,section,article,header,nav,form,div')].filter(visible);
  const composedLayout = containers.some(el => ['grid','flex'].includes(getComputedStyle(el).display));
  // A flex navigation bar says nothing about the actual page composition.
  const contentContainers = containers.filter(el => el.closest('main') && !el.closest('nav,header,footer'));
  const contentLayout = contentContainers.some(el => ['grid','inline-grid','flex','inline-flex'].includes(getComputedStyle(el).display));
  const subjectMedia = [...document.querySelectorAll('main img,main svg,main canvas,main video')]
    .filter(el => visible(el) && !el.closest('nav,header,footer,button,a') &&
      (el.tagName.toLowerCase()!=='img' || (el.complete && el.naturalWidth>0)));
  const bodyStyle = getComputedStyle(document.body);
  const color = bodyStyle.backgroundColor;
  const customBackground = !['rgb(255, 255, 255)','rgba(0, 0, 0, 0)'].includes(color);
  const text = document.body.innerText.trim();
  const viewportArea = innerWidth * innerHeight;
  const visibleArea = el => { const r=el.getBoundingClientRect(); return Math.max(0,Math.min(r.right,innerWidth)-Math.max(r.left,0))*Math.max(0,Math.min(r.bottom,innerHeight)-Math.max(r.top,0)); };
  const mainTitle = [...document.querySelectorAll('main h1,main h2,main h3,h1')]
    .filter(el => visible(el) && !el.closest('header,nav'))
    .sort((a,b) => parseFloat(getComputedStyle(b).fontSize)-parseFloat(getComputedStyle(a).fontSize))[0];
  const bodySizes = [...document.querySelectorAll('main p')].filter(visible)
    .map(el=>parseFloat(getComputedStyle(el).fontSize)).filter(size=>Number.isFinite(size) && size>=12 && size<=24).sort((a,b)=>a-b);
  const bodyTextSize = bodySizes.length ? bodySizes[Math.floor(bodySizes.length/2)] : 16;
  const dataSurfaces = [...document.querySelectorAll('table,[role=grid],form')].filter(visible);
  const faviconHref=document.querySelector('link[rel*=icon][href]')?.href;
  const faviconSubjects=[...document.querySelectorAll('main img')].filter(el=>visible(el)
    && !el.closest('header,nav,footer') && el.src===faviconHref
    && (el.classList.contains('card-image') || (el.alt.trim() && !/logo|brand|icon|favicon/i.test(el.alt))))
    .map(el=>({alt:el.alt.slice(0,120),class:el.className}));
  const faviconLoaded=faviconHref ? await new Promise(resolve=>{
    const image=new Image();let settled=false;
    const done=value=>{if(!settled){settled=true;clearTimeout(timer);resolve(value)}};
    const timer=setTimeout(()=>done(false),2000);
    image.onload=()=>done(image.naturalWidth>0);image.onerror=()=>done(false);image.src=faviconHref;
  }) : null;
  const geometry = el => {
    const r=el.getBoundingClientRect(), s=getComputedStyle(el);
    return {tag:el.tagName,id:el.id,class:typeof el.className==='string'?el.className.slice(0,120):'',
      left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width),
      scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,display:s.display,
      minWidth:s.minWidth,maxWidth:s.maxWidth,gridColumns:s.gridTemplateColumns,
      gap:s.gap,flexWrap:s.flexWrap,position:s.position,
      inlineStyle:(el.getAttribute('style')||'').slice(0,300),
      inlineGridColumns:el.style?.gridTemplateColumns||'',inlineWidth:el.style?.width||''};
  };
  return { width: innerWidth, overflow: document.documentElement.scrollWidth > innerWidth + 2,
    overflowElements: [...document.querySelectorAll('body *')].filter(el => visible(el) && el.getBoundingClientRect().right > innerWidth + 2)
      .slice(0,10).map(el => {const s=getComputedStyle(el), p=el.parentElement; return {
        tag:el.tagName,class:typeof el.className==='string'?el.className.slice(0,120):'',
        width:Math.round(el.getBoundingClientRect().width),display:s.display,
        minWidth:s.minWidth,maxWidth:s.maxWidth,gridColumns:s.gridTemplateColumns,
        parentWidth:p?Math.round(p.getBoundingClientRect().width):null,
        parentDisplay:p?getComputedStyle(p).display:null,
        ancestors:(()=>{const result=[];let a=p;for(let i=0;a&&i<5;i++,a=a.parentElement)result.push(geometry(a));return result;})()};}),
    loadedImages: [...document.images].filter(el => visible(el) && el.complete && el.naturalWidth > 0).length,
    brokenImages: [...document.images].filter(el => visible(el) && el.complete && el.naturalWidth === 0).length,
    controls: controls.length, styledControls, composedLayout, customBackground,
    contentLayout, firstScreenMediaRatio: Math.max(0,...subjectMedia.map(el=>visibleArea(el)/viewportArea)),
    textLength: text.length, hasGraphics: !!document.querySelector('canvas,svg,img,video'),
    starterVisible: text.includes('Your project is ready') && text.includes('Describe what you want to build'),
    titleSize: mainTitle ? parseFloat(getComputedStyle(mainTitle).fontSize) : 0,
    bodyTextSize,
    titleElement: mainTitle ? {tag:mainTitle.tagName,id:mainTitle.id,class:mainTitle.className,text:mainTitle.innerText.slice(0,160)} : null,
    brandVisual: !!document.querySelector('header svg,header img,nav svg,nav img'),
    favicon: !!document.querySelector('link[rel*=icon][href]'),
    faviconLoaded,
    faviconSubjects,
    dataSurfaceRatio: Math.max(0,...dataSurfaces.map(el=>visibleArea(el)/viewportArea)),
    smallTargets: controls.filter(el=>{const r=el.getBoundingClientRect();return r.width<36 || r.height<36;})
      .slice(0,8).map(el=>({label:el.getAttribute('aria-label')||el.innerText||el.name,tag:el.tagName})),
    smallBodyText: [...document.querySelectorAll('main p,main li')].filter(el=>visible(el)&&parseFloat(getComputedStyle(el).fontSize)<14).length,
    longLines: [...document.querySelectorAll('main p')].filter(el=>visible(el)&&el.innerText.length>160&&el.getBoundingClientRect().width>800).length,
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    headings: [...document.querySelectorAll('h1,h2,h3')].filter(visible).map(el => el.innerText.slice(0,120)).slice(0,12) };
}"""


def assess_visual_quality(snapshots, *, allow_unstyled=False, require_images=False, public_website=False):
    issues = []
    suggestions = []
    for snapshot in snapshots:
        width = snapshot['width']
        if width < 600 and snapshot.get('smallTargets'):
            labels = ', '.join(str(item.get('label') or item.get('tag'))[:60] for item in snapshot['smallTargets'])
            suggestions.append(f'At {width}px, increase small touch targets: {labels}. Prefer 44px for primary controls.')
        if snapshot.get('smallBodyText'):
            suggestions.append(f'At {width}px, review {snapshot["smallBodyText"]} body text blocks below 14px for readability.')
        if snapshot.get('longLines'):
            suggestions.append(f'At {width}px, constrain long paragraphs to a comfortable reading width, around 60–75 characters.')
        if public_website and not allow_unstyled:
            if snapshot.get('faviconSubjects'):
                issues.append(f'At {width}px, the favicon is reused as subject/product imagery. Replace it with actual subject-matched artwork or photography; branding is not product evidence.')
            if (width >= 900 and snapshot.get('contentLayout') is False
                    and snapshot.get('firstScreenMediaRatio', 0) < 0.08
                    and snapshot.get('titleSize', 0) < 40):
                issues.append(f'At {width}px, the public page body is plain document flow with no substantial first-screen artwork and a small headline. '
                              'Implement the chosen composition in the page stylesheet, not only the header or shared controls. '
                              'For an intentionally text-led design, establish an expressive display hierarchy and deliberate reading width; media is not mandatory.')
            if not snapshot.get('brandVisual') or not snapshot.get('favicon'):
                issues.append('The public website needs a visible original logo and a configured favicon. Add appropriate SVG branding without imitating another company.')
            elif snapshot.get('faviconLoaded') is False:
                issues.append('The configured favicon could not load. Create the referenced asset or repair its URL; a link tag alone is not a working favicon.')
            title_size = snapshot.get('titleSize', 0)
            body_size = snapshot.get('bodyTextSize', 16)
            minimum = 28 if width >= 900 else 20
            ratio = 1.4 if width >= 900 else 1.3
            if title_size < minimum or title_size < body_size * ratio:
                element = snapshot.get('titleElement') or {}
                issues.append(f'At {width}px, the main headline is {title_size}px versus {body_size}px body text. '
                              f'Give it readable emphasis: at least {minimum}px and {ratio} times the body size. '
                              f'Repair the applicable responsive CSS for {element.get("tag", "heading")} '
                              f'id={element.get("id", "")} class={element.get("class", "")} '
                              f'text={element.get("text", "")[:100]}; preserve phone wrapping and content.')
            if snapshot.get('dataSurfaceRatio', 0) > 0.45:
                issues.append(f'At {width}px, a form/table dominates the public homepage. Put detailed booking or management workflows in a dedicated view and lead with the visitor-facing website.')
        if require_images and snapshot.get('loadedImages', 0) < 2:
            issues.append(f'At {width}px, the photography portfolio needs at least two visible, successfully loaded photos; include actual hero and gallery images.')
        if (require_images or public_website) and snapshot.get('brokenImages', 0):
            issues.append(f'At {width}px, website images failed to load. Replace broken sources with subject-matched assets.')
        if snapshot['overflow']:
            issues.append(f"At {width}px, the page overflows horizontally; make the layout responsive.")
            ancestor = next(iter(snapshot.get('overflowElements') or []), None)
            if ancestor and ancestor.get('parentWidth'):
                suggestions.append(f"Start with the first overflowing ancestor {ancestor.get('tag')} "
                    f"class={ancestor.get('class', '')}: {ancestor.get('width')}px wide inside a "
                    f"{ancestor['parentWidth']}px {ancestor.get('parentDisplay', '')} parent. "
                    "Inspect that ancestor's width and intrinsic grid/flex sizing before changing descendants. "
                    "A max-width plus auto margins can still shrink-wrap or exceed a phone; "
                    "use an explicit bounded width, minmax(0,1fr) tracks and wrapping where appropriate. "
                    "Do not hide overflow or remove content.")
                parents=ancestor.get('ancestors',[])
                constrained=next((p for p in parents if p.get('display') in {'grid','inline-grid'}
                    and p.get('inlineGridColumns')),None)
                if constrained:
                    suggestions.append(f"The controlling ancestor {constrained.get('tag')} id={constrained.get('id','')} "
                        f"class={constrained.get('class','')} has inline grid-template-columns={constrained['inlineGridColumns']} "
                        f"(computed {constrained.get('gridColumns')}) inside {constrained.get('width')}px. "
                        "Locate this ancestor in the component source. A descendant/sidebar max-width rule does not change "
                        "its grid tracks. Move the inline layout into a named responsive class and reflow its tracks "
                        "at phone widths while preserving the desktop layout and all content.")
        if snapshot['starterVisible']:
            issues.append("The preview still shows the starter placeholder instead of the requested application.")
        if snapshot['textLength'] < 15 and not snapshot['hasGraphics']:
            issues.append("The rendered page is empty or has almost no visible application content.")
        if not allow_unstyled and snapshot['controls'] and not snapshot['styledControls']:
            issues.append(f"At {width}px, all form controls use small browser-default styling. Add deliberate control styling, spacing and usable sizes in the application stylesheet.")
    return {'status': 'success' if not issues else 'error', 'issues': list(dict.fromkeys(issues)),
            'snapshots': snapshots, 'suggestions': list(dict.fromkeys(suggestions)),
            'scope': 'Rendered content, typography, touch targets and horizontal overflow; not an aesthetic score.'}
