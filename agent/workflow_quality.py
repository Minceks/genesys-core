"""Bounded visual evidence from real checked states, before baseline restoration."""


def remaining_design_blockers(review):
    """Concrete unresolved major findings block delivery; outages are not app defects."""
    if review.get('status') != 'needs_polish':
        return []
    return ['Workflow design review: '+item['evidence']+' Required correction: '+item['correction']
            for item in review.get('findings', []) if item.get('severity') == 'major']


REACHABILITY_SCRIPT = '''() => {
  const modal = [...document.querySelectorAll('dialog[open],[aria-modal=true]')]
    .filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden').at(-1);
  const controls = [...(modal || document).querySelectorAll('button,a[href],input:not([type=hidden]),select,textarea')];
  const blockedControls = [];
  for (const e of controls.slice(0,160)) {
    const r=e.getBoundingClientRect(), s=getComputedStyle(e);
    if (e.disabled || e.closest('[inert],[aria-hidden=true]') || s.visibility==='hidden' || s.pointerEvents==='none'
        || r.width<12 || r.height<12 || r.top<0 || r.left<0 || r.right>innerWidth || r.bottom>innerHeight) continue;
    const points=[[.5,.5],[.25,.25],[.75,.25],[.25,.75],[.75,.75]];
    const blockers=points.map(([x,y])=>{
      const top=document.elementFromPoint(r.left+r.width*x,r.top+r.height*y);
      if (!top || top===e || e.contains(top) || top.contains(e)) return null;
      for(let node=top;node && node!==document.body;node=node.parentElement)
        if(['fixed','sticky'].includes(getComputedStyle(node).position))return node;
      return null;
    });
    if (blockers[0] && blockers.filter(Boolean).length>=3) {
      blockedControls.push({label:(e.getAttribute('aria-label')||e.innerText||e.name||e.tagName).slice(0,100),
        blocker: blockers[0].tagName, blockerClass:String(blockers[0].className||'').slice(0,100)});
      if(blockedControls.length===6)break;
    }
  }
  return {blockedControls};
}'''


class WorkflowEvidence:
    """Sample three checked states at two widths; no clicks, routes or state injection."""
    def __init__(self):
        self.images = []
        self.details = {}
        self.issues = []
        self.unavailable = []
        self.states = 0

    def capture(self, page, name):
        if self.states >= 3:
            return
        self.states += 1
        viewport = None
        scroll = None
        try:
            viewport = page.viewport_size
            scroll = page.evaluate('() => ({x:scrollX,y:scrollY})')
            for label, width, height in [('desktop',1280,800),('phone',390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                page.wait_for_timeout(100)
                metrics = page.evaluate(REACHABILITY_SCRIPT)
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                key = f'generated-workflow-{self.states}-{label}'
                self.details[key] = {'workflow':name[:180], 'width':width, 'height':height,
                                     'overflow':overflow, **metrics,
                                     'scope':'Same checked state resized for visual review; not separate phone functional execution.'}
                if overflow:
                    self.issues.append(f'Workflow {name[:120]} at {width}px overflows horizontally; reflow the actual view without hiding content.')
                for item in metrics['blockedControls']:
                    self.issues.append(f'Workflow {name[:120]} at {width}px: {item["label"]} is covered by fixed/sticky {item["blocker"]} class={item["blockerClass"]}; reserve navigation space or repair stacking.')
                data = page.screenshot(type='jpeg', quality=60, animations='disabled', timeout=2000)
                if len(data) <= 2_000_000:
                    self.images.append((key,data))
                else:
                    self.unavailable.append(key+': screenshot exceeded bounded size')
        except Exception as error:
            # Evidence infrastructure failure is not an application defect.
            self.unavailable.append('Workflow screenshot capture unavailable: '+type(error).__name__)
        finally:
            try:
                if viewport:
                    page.set_viewport_size(viewport)
                if scroll is not None:
                    page.evaluate('(p)=>scrollTo({top:p.y,left:p.x,behavior:"instant"})',scroll)
            except Exception as error:
                self.unavailable.append('Workflow viewport restoration unavailable: '+type(error).__name__)

    def summary(self):
        return {'capturedViews':self.details, 'limitations':self.unavailable,
                'scope':'At most three real checked workflow states, sampled at desktop and phone widths; not exhaustive route or behavior coverage.'}
