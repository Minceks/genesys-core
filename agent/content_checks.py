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
    if re.search(r'\bexpenses?\b', prompt, re.I):
        category = page.get_by_role('textbox', name=re.compile(r'^(category|description|expense name)$', re.I))
        amount = page.get_by_role('spinbutton', name=re.compile(r'^amount', re.I))
        add = page.get_by_role('button', name=re.compile(r'^add(?: expense)?$', re.I))
        marker = 'GeneSys verification expense'
        if category.count() != 1 or amount.count() != 1 or add.count() != 1:
            issues.append('Expense workflow cannot be verified. Provide accessible Category and Amount fields and an Add expense button.')
        else:
            try:
                category.fill(marker)
                amount.fill('12.50')
                add.click()
                page.wait_for_timeout(200)
                item = page.get_by_text(marker, exact=True)
                if not item.count():
                    raise ValueError('Adding an expense does not show the submitted expense.')
                tested.append('add expense')
                page.reload(wait_until='networkidle')
                item = page.get_by_text(marker, exact=True)
                if not item.count():
                    raise ValueError('Added expense disappears after reload. Persist expense data.')
                tested.append('expense reload persistence')
                container = item.first
                for _ in range(6):
                    remove = container.get_by_role('button', name=re.compile(r'^(remove|delete)(?: expense)?$', re.I))
                    if remove.count() == 1:
                        remove.click()
                        break
                    container = container.locator('..')
                else:
                    raise ValueError('Provide a Remove button for each expense.')
                page.wait_for_timeout(200)
                dialog = page.get_by_role('dialog')
                if dialog.count() == 1 and dialog.is_visible():
                    confirm = dialog.get_by_role('button', name=re.compile(r'^(confirm(?: removal)?|remove(?: expense)?|delete(?: expense)?)$', re.I))
                    if confirm.count() == 1:
                        confirm.click()
                page.wait_for_timeout(200)
                if page.get_by_text(marker, exact=True).count():
                    raise ValueError('Remove expense does not remove the item. Native browser dialogs are blocked in embedded previews; use in-page confirmation or Undo.')
                tested.append('remove expense')
                page.reload(wait_until='networkidle')
                if page.get_by_text(marker, exact=True).count():
                    raise ValueError('Removed expense returns after reload.')
                tested.append('expense removal persistence')
            except Exception as error:
                issues.append(str(error)[:600])
            finally:
                # Verification uses an isolated browser; clear only starter-owned local data.
                page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('user-app:')).forEach(k => localStorage.removeItem(k))")
                page.reload(wait_until='networkidle')
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
                        remove = container.get_by_role('button', name=re.compile(r'^remove\b', re.I))
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
    if re.search(r'\b(game|zombie|shooter|platformer)\b', prompt, re.I):
        start = page.get_by_role('button', name=re.compile(r'^(play|start|start game|play game|start / restart)$', re.I))
        if start.count() == 1 and start.is_visible():
            start.click(timeout=3000)
            page.wait_for_timeout(250)
            tested.append('game start')
        canvas = page.locator('canvas:visible')
        if canvas.count() == 1:
            canvas.click(timeout=3000)
            page.wait_for_timeout(250)
            tested.append('game canvas input')
        restart = page.get_by_role('button', name=re.compile(r'^(restart|restart game|start / restart)$', re.I))
        if restart.count() == 1 and restart.is_visible():
            restart.click(timeout=3000)
            page.wait_for_timeout(250)
            tested.append('game restart')
    return {'status': 'error' if issues else 'success', 'issues': issues, 'testedInteractions': tested}
