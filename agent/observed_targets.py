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
