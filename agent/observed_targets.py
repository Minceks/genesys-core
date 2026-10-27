"""Narrow typography corrections and modal scoping against the live DOM."""
import re
import unicodedata


def canonical_name(value):
    text = unicodedata.normalize('NFKC', str(value))
    text = re.sub(r'(?<=\w)[\-\u2010-\u2015](?=\w)', ' ', text)
    return re.sub(r'\s+', ' ', text).strip().casefold()


def observed_spelling(scope, name):
    """Do not fuzzy-match products, numbers, assertions or substrings."""
    if not callable(getattr(scope, 'locator', None)):
        return name
    names = scope.locator('h1,h2,h3,h4,h5,h6,button,label,input,textarea,select,[aria-label]').evaluate_all('''els => els.flatMap(e => [
        e.getAttribute('aria-label'), e.textContent, e.getAttribute('alt'),
        ...(e.labels ? [...e.labels].map(l=>l.textContent) : [])
    ]).filter(Boolean)''')
    # CSS text-transform changes innerText without changing Playwright's text
    # selector or the DOM accessible name. Read actual leaf text, including status
    # badges, rather than replacing "pending" with an unmatchable "PENDING".
    names.extend(scope.locator('*').evaluate_all('''els => els.filter(e =>
        e.childElementCount === 0 && !['SCRIPT','STYLE'].includes(e.tagName)
    ).map(e => e.textContent).filter(Boolean)'''))
    if name in names:
        return name
    matches = {value.strip() for value in names if canonical_name(value) == canonical_name(name)}
    # Case/typography may differ in repeated representations of the same name;
    # require one exact observed spelling before changing a selector.
    return next(iter(matches)) if len(matches) == 1 else name


def active_dialog_target(page, specification, resolve):
    if not isinstance(specification, dict) or specification.get('withinRole') or specification.get('withinText'):
        return None
    dialogs = page.locator('[role="dialog"],[role="alertdialog"],dialog[open],[aria-modal="true"]')
    visible = [dialogs.nth(i) for i in range(dialogs.count()) if dialogs.nth(i).is_visible()]
    if len(visible) != 1:
        return None
    found = resolve(visible[0], specification)
    return found if found.count() == 1 and found.is_visible() else None


def exact_label_target(page, specification, action, resolve):
    """Correct a planner's method/role only for the exact same named surface."""
    if not isinstance(specification,dict) or not str(specification.get('name','')).strip():return None
    if action not in {'visible','tabTo','hold','press','pointer'}:return None
    candidate=dict(specification,by='label');candidate.pop('role',None)
    try:found=resolve(page,candidate)
    except ValueError:return None
    if found.count()!=1 or not found.is_visible():return None
    if action!='visible' and found.evaluate("e => e.tagName!=='CANVAS' && e.getAttribute('role')!=='group'"):
        return None
    return found,candidate


def surface_targets(page):
    """Live names/methods, including canvas and labelled panels omitted by ARIA trees."""
    return page.locator('[aria-label]').evaluate_all('''els => els.filter(e=>{
      const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&!e.closest('[inert],[aria-hidden="true"]');
    }).slice(0,40).map(e=>({by:'label',name:e.getAttribute('aria-label'),tag:e.tagName.toLowerCase(),role:e.getAttribute('role')}))''')


def diagnosable_failure(failure, sources, initial_text):
    """A guessed/missing locator or capture cannot justify editing application code."""
    step=failure.get('step') or {};spec=step.get('target') or {}
    if step.get('action') not in {'type','visible','absent','value','attribute','invalid','sameText','focused','newTabValue','newTabText','number','style'}:
        return False
    if failure.get('executedActions',0)<1:return False
    if any(word in failure.get('error','') for word in ('Invalid verification','Unsupported','strict mode violation')):return False
    name=spec.get('name','')
    if not isinstance(name,str) or not name.strip():return False
    if failure.get('targetResolved'):return True
    if step.get('action') not in {'visible','absent'}:return False
    if name in initial_text:return True
    literal=re.compile(r'''["']'''+re.escape(name)+r'''["']|>\s*'''+re.escape(name)+r'''\s*<''')
    return any(isinstance(code,str) and literal.search(code) for code in (sources or {}).values())
