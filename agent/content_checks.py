"""Check explicit content requests and safe book-list interactions in the rendered app."""

import re


def explicit_text_requirements(prompt):
    requirements = []
    # Only enforce literal wording clearly supplied as UI text, not inferred descriptions.
    for match in re.finditer(r'\b(heading|title|subtitle|button|label)\s*(?::|(?:must be|should be|named|called|labeled))\s*["\u201c\u2018\']?([^\n.!?"\u201d\u2019\']{2,100})', prompt, re.I):
        text = match.group(2).strip()
        if text:
            requirements.append({'text': text, 'unique': match.group(1).lower() in ('heading', 'subtitle', 'title')})
    subtitle = re.search(r'\bsubtitle\s+["\u201c\u2018\']?([^\n.!?"\u201d\u2019\']{2,100}?)\s+(?:directly\s+)?(?:beneath|below|under)\b', prompt, re.I)
    if subtitle:
        requirements.append({'text': subtitle.group(1).strip(), 'unique': True})
    return list({requirement['text']: requirement for requirement in requirements}.values())[:6]


def verify_content(page, prompt):
    issues = []
    for requirement in explicit_text_requirements(prompt):
        matches = page.get_by_text(requirement['text'], exact=True)
        visible = sum(matches.nth(index).is_visible() for index in range(matches.count()))
        if not visible:
            issues.append(f"Required text is missing: {requirement['text']}")
        elif requirement['unique'] and visible > 1:
            issues.append(f"Required heading/subtitle is duplicated: {requirement['text']}. Render it once.")
    tested = []
    # Isolated verification browser, synthetic data, and only an explicitly requested
    # book-list flow. Never click arbitrary destructive/account/payment controls.
    if re.search(r'\b(book|reading)\b', prompt, re.I):
        field = page.get_by_label(re.compile(r'^book title$', re.I))
        add = page.get_by_role('button', name=re.compile(r'^add book$', re.I))
        if field.count() == 1 and add.count() == 1:
            marker = 'GeneSys verification book'
            field.fill(marker)
            add.click()
            page.wait_for_timeout(150)
            match = page.get_by_text(marker, exact=True)
            if not match.count():
                issues.append('Add book does not add the submitted title to the visible list.')
            else:
                tested.append('add book')
                page.reload(wait_until='networkidle')
                if not page.get_by_text(marker, exact=True).count():
                    issues.append('Book data disappears after refresh. Persist user-created data.')
                else:
                    tested.append('refresh persistence')
                    item = page.get_by_text(marker, exact=True).first
                    container = item
                    for _ in range(5):
                        remove = container.get_by_role('button', name=re.compile(r'^remove(?: book)?$', re.I))
                        if remove.count() == 1:
                            remove.click()
                            page.wait_for_timeout(150)
                            if page.get_by_text(marker, exact=True).count():
                                issues.append('Remove book does not remove the selected title.')
                            else:
                                tested.append('remove book')
                            break
                        container = container.locator('..')
                    else:
                        if re.search(r'\bremove\b', prompt, re.I):
                            issues.append('The requested Remove button is missing from the book item.')
            # Remove any synthetic data from this isolated browser, not users' browsers.
            page.evaluate("Object.keys(localStorage).filter(key => key.startsWith('user-app:')).forEach(key => localStorage.removeItem(key))")
            page.reload(wait_until='networkidle')
    return {'status': 'error' if issues else 'success', 'issues': issues, 'testedInteractions': tested}
