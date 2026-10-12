"""Objective layout/style checks; these do not claim to measure aesthetic taste."""

SNAPSHOT_SCRIPT = """() => {
  const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const controls = [...document.querySelectorAll('button,input:not([type=hidden]),select,textarea')].filter(visible);
  const styledControls = controls.filter(el => {
    const s = getComputedStyle(el);
    return parseFloat(s.paddingTop) >= 7 || parseFloat(s.borderRadius) >= 4 || parseFloat(s.height) >= 36;
  }).length;
  const containers = [...document.querySelectorAll('main,section,article,header,nav,form,div')].filter(visible);
  const composedLayout = containers.some(el => ['grid','flex'].includes(getComputedStyle(el).display));
  const bodyStyle = getComputedStyle(document.body);
  const color = bodyStyle.backgroundColor;
  const customBackground = !['rgb(255, 255, 255)','rgba(0, 0, 0, 0)'].includes(color);
  const text = document.body.innerText.trim();
  const viewportArea = innerWidth * innerHeight;
  const visibleArea = el => { const r=el.getBoundingClientRect(); return Math.max(0,Math.min(r.right,innerWidth)-Math.max(r.left,0))*Math.max(0,Math.min(r.bottom,innerHeight)-Math.max(r.top,0)); };
  const mainTitle = [...document.querySelectorAll('main h1,main h2,main h3,h1')]
    .filter(el => visible(el) && !el.closest('header,nav'))
    .sort((a,b) => parseFloat(getComputedStyle(b).fontSize)-parseFloat(getComputedStyle(a).fontSize))[0];
  const dataSurfaces = [...document.querySelectorAll('table,[role=grid],form')].filter(visible);
  return { width: innerWidth, overflow: document.documentElement.scrollWidth > innerWidth + 2,
    overflowElements: [...document.querySelectorAll('body *')].filter(el => visible(el) && el.getBoundingClientRect().right > innerWidth + 2)
      .slice(0,10).map(el => ({tag:el.tagName,class:typeof el.className==='string'?el.className.slice(0,120):'',width:Math.round(el.getBoundingClientRect().width),display:getComputedStyle(el).display})),
    loadedImages: [...document.images].filter(el => visible(el) && el.complete && el.naturalWidth > 0).length,
    brokenImages: [...document.images].filter(el => visible(el) && el.complete && el.naturalWidth === 0).length,
    controls: controls.length, styledControls, composedLayout, customBackground,
    textLength: text.length, hasGraphics: !!document.querySelector('canvas,svg,img,video'),
    starterVisible: text.includes('Your project is ready') && text.includes('Describe what you want to build'),
    titleSize: mainTitle ? parseFloat(getComputedStyle(mainTitle).fontSize) : 0,
    brandVisual: !!document.querySelector('header svg,header img,nav svg,nav img'),
    favicon: !!document.querySelector('link[rel*=icon][href]'),
    dataSurfaceRatio: Math.max(0,...dataSurfaces.map(el=>visibleArea(el)/viewportArea)),
    headings: [...document.querySelectorAll('h1,h2,h3')].filter(visible).map(el => el.innerText.slice(0,120)).slice(0,12) };
}"""


def assess_visual_quality(snapshots, *, allow_unstyled=False, require_images=False, public_website=False):
    issues = []
    for snapshot in snapshots:
        width = snapshot['width']
        if public_website and not allow_unstyled:
            if not snapshot.get('brandVisual') or not snapshot.get('favicon'):
                issues.append('The public website needs a visible original logo and a configured favicon. Add appropriate SVG branding without imitating another company.')
            if snapshot.get('titleSize', 0) < (32 if width >= 900 else 28):
                issues.append(f'At {width}px, the public homepage lacks a clear visual headline hierarchy. Compose a visitor-facing hero with readable, prominent typography.')
            if snapshot.get('dataSurfaceRatio', 0) > 0.45:
                issues.append(f'At {width}px, a form/table dominates the public homepage. Put detailed booking or management workflows in a dedicated view and lead with the visitor-facing website.')
        if require_images and snapshot.get('loadedImages', 0) < 2:
            issues.append(f'At {width}px, the photography portfolio needs at least two visible, successfully loaded photos; include actual hero and gallery images.')
        if require_images and snapshot.get('brokenImages', 0):
            issues.append(f'At {width}px, portfolio photos failed to load. Replace broken image sources.')
        if snapshot['overflow']:
            issues.append(f"At {width}px, the page overflows horizontally; make the layout responsive.")
        if snapshot['starterVisible']:
            issues.append("The preview still shows the starter placeholder instead of the requested application.")
        if snapshot['textLength'] < 15 and not snapshot['hasGraphics']:
            issues.append("The rendered page is empty or has almost no visible application content.")
        if not allow_unstyled and snapshot['controls'] and not snapshot['styledControls']:
            issues.append(f"At {width}px, all form controls use small browser-default styling. Add deliberate control styling, spacing and usable sizes in the application stylesheet.")
    return {'status': 'success' if not issues else 'error', 'issues': list(dict.fromkeys(issues)),
            'snapshots': snapshots, 'scope': 'Rendered content, control styling and horizontal overflow; not an aesthetic score.'}
