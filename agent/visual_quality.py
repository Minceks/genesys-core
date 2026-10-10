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
  return { width: innerWidth, overflow: document.documentElement.scrollWidth > innerWidth + 2,
    controls: controls.length, styledControls, composedLayout, customBackground,
    textLength: text.length, hasGraphics: !!document.querySelector('canvas,svg,img,video'),
    starterVisible: text.includes('Your project is ready') && text.includes('Describe what you want to build'),
    headings: [...document.querySelectorAll('h1,h2,h3')].filter(visible).map(el => el.innerText.slice(0,120)).slice(0,12) };
}"""


def assess_visual_quality(snapshots, *, allow_unstyled=False):
    issues = []
    for snapshot in snapshots:
        width = snapshot['width']
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
