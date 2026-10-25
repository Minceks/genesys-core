"""Bounded real input for canvas, keyboard and other continuous browser controls."""
import math
import re
import time

INPUT_ACTIONS = {'press', 'hold', 'pointer', 'wait'}
KEY = re.compile(r'^(?:[a-zA-Z0-9]|ArrowUp|ArrowDown|ArrowLeft|ArrowRight|Space|Enter|Escape|Tab|Backspace|Delete|Home|End|PageUp|PageDown)$')


def validate_number(step):
    value = step.get('value')
    if (type(value) not in {int, float} or not math.isfinite(value)
            or step.get('comparison') not in {'gt','gte','lt','lte','eq'}):
        raise ValueError('Invalid verification plan: numeric assertions require a finite value and comparison')


def assert_number(page, locator, step):
    validate_number(step)
    if locator.count() != 1:
        raise ValueError('Invalid verification plan: numeric assertion requires one named output')
    deadline = time.monotonic() + 3
    while True:
        if not locator.is_visible(): raise ValueError('Requested numeric output is not visible')
        numbers = re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', locator.inner_text())
        if len(numbers) != 1:
            raise ValueError('Invalid verification plan: numeric output must contain exactly one number')
        actual, value = float(numbers[0]), step['value']
        matches = {'gt':actual>value,'gte':actual>=value,'lt':actual<value,'lte':actual<=value,'eq':actual==value}
        if matches[step['comparison']]: return
        if time.monotonic() >= deadline:
            raise AssertionError('Numeric outcome did not satisfy ' + step['comparison'] + ' ' + str(value) + '; observed ' + str(actual))
        page.wait_for_timeout(100)


def input_duration(step):
    action = step.get('action')
    if action not in INPUT_ACTIONS: return 0
    if action in {'hold', 'wait'}:
        duration = step.get('durationMs')
        maximum = 3000 if action == 'hold' else 2000
        if type(duration) is not int or not 50 <= duration <= maximum:
            raise ValueError('Invalid verification plan: bounded input duration required')
    else:
        duration = 0
    if action in {'press', 'hold'}:
        keys = [step.get('key')] if action == 'press' else step.get('keys')
        if (not isinstance(keys, list) or not 1 <= len(keys) <= 3 or len(set(map(str, keys))) != len(keys)
                or any(not isinstance(key, str) or not KEY.fullmatch(key) for key in keys)):
            raise ValueError('Invalid verification plan: unsupported keyboard input; modifiers and shortcuts are forbidden')
    if action == 'pointer':
        if step.get('mode') not in {'move', 'click', 'drag', 'hold'}:
            raise ValueError('Invalid verification plan: unsupported pointer mode')
        duration = step.get('durationMs', 0)
        if type(duration) is not int or not 0 <= duration <= 3000 or (step['mode'] == 'hold' and duration < 50):
            raise ValueError('Invalid verification plan: bounded pointer duration required')
        if step['mode'] in {'move', 'click'} and duration:
            raise ValueError('Invalid verification plan: pointer waits require hold or drag')
        for name in (('x', 'y', 'endX', 'endY') if step['mode'] == 'drag' else ('x', 'y')):
            value = step.get(name)
            if type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Invalid verification plan: pointer coordinates must be fractions within the observed control')
    return duration


def validate_input_budget(checks):
    total = 0
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get('steps'), list):
            raise ValueError('Invalid verification plan structure')
        duration = sum(input_duration(step) for step in check.get('steps', []) if isinstance(step, dict))
        if duration > 15000:
            raise ValueError('Invalid verification plan: input wait budget exceeds 15 seconds per workflow')
        total += duration
    if total > 45000:
        raise ValueError('Invalid verification plan: total input wait budget exceeds 45 seconds')


def perform_input(page, locator, step):
    input_duration(step)
    action = step['action']
    if action == 'wait':
        page.wait_for_timeout(step['durationMs']); return
    if locator is None or locator.count() != 1 or not locator.is_visible():
        raise ValueError('Invalid verification plan: real input requires one visible named control')
    if action in {'hold', 'press'}:
        # Focus a real accessible control. Never dispatch synthetic events or
        # change application state, clocks, localStorage or simulation globals.
        locator.focus(timeout=3000)
        if not locator.evaluate('e => e === document.activeElement'):
            raise ValueError('Requested keyboard control cannot receive focus')
        keys = [step['key']] if action == 'press' else step['keys']
        keys = [' ' if key == 'Space' else key for key in keys]
        if action == 'press':
            locator.press(keys[0], timeout=3000); return
        held = []
        try:
            for key in keys:
                page.keyboard.down(key); held.append(key)
            page.wait_for_timeout(step['durationMs'])
        finally:
            for key in reversed(held): page.keyboard.up(key)
        return
    locator.scroll_into_view_if_needed(timeout=3000)
    box = locator.bounding_box()
    if not box or box['width'] <= 0 or box['height'] <= 0:
        raise ValueError('Requested pointer control has no visible area')
    def point(x, y):
        return (box['x'] + min(box['width'] - 1, box['width'] * x),
                box['y'] + min(box['height'] - 1, box['height'] * y))
    start = point(step['x'], step['y'])
    if action == 'pointer' and step['mode'] == 'click':
        # Locator click retains Playwright's overlay/actionability checks.
        locator.click(position={'x': start[0] - box['x'], 'y': start[1] - box['y']}, timeout=3000)
    else:
        page.mouse.move(*start)
        if step['mode'] in {'drag', 'hold'}:
            # Refuse to drag through an overlay outside the target's subtree.
            if not locator.evaluate('(e,p) => e.contains(document.elementFromPoint(p[0],p[1]))', list(start)):
                raise ValueError('Requested pointer control is covered by another element')
            page.mouse.down()
            try:
                if step['mode'] == 'drag': page.mouse.move(*point(step['endX'], step['endY']), steps=12)
                if step.get('durationMs'): page.wait_for_timeout(step['durationMs'])
            finally: page.mouse.up()
