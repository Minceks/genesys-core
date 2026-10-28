"""Choose a currently enabled option through an explicitly named UI group."""


def choose_available(locator):
    if locator.count() != 1 or not locator.is_visible():
        raise ValueError('Invalid verification plan: availability group is missing or ambiguous')
    valid = locator.evaluate('''e => (['group','radiogroup'].includes(e.getAttribute('role')) || e.tagName === 'FIELDSET')
        && Boolean(e.getAttribute('aria-label')?.trim() || e.getAttribute('aria-labelledby')?.trim() || e.querySelector('legend')?.textContent.trim())''')
    if not valid:
        raise ValueError('Invalid verification plan: chooseAvailable requires a named option group')
    options = locator.locator('button,input[type=radio],[role=radio]')
    if options.count() > 24:
        raise ValueError('Invalid verification plan: availability group has too many options')
    for index in range(options.count()):
        option = options.nth(index)
        if option.is_visible() and option.is_enabled():
            option.click(timeout=3000)
            return
    raise ValueError('Invalid verification execution: no enabled visible option in the availability group')
