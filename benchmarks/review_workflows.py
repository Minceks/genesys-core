"""Reviewed selectors for the synthetic booking/dashboard fresh-build artifacts.

Offline only; does not generalize these selectors to arbitrary user projects.
"""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import sys
from pathlib import Path
import threading


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def confirm(page, control, message, accept):
    received = []
    def handle(dialog):
        received.append((dialog.type, dialog.message))
        if accept and dialog.type == 'confirm' and dialog.message == message:
            dialog.accept()
        else:
            dialog.dismiss()
    page.once('dialog', handle)
    control.click()
    assert received == [('confirm', message)], received


def dashboard(page, context, expect, width):
    marker = f'Genesys verification task {width}'
    edited = marker + ' edited'
    page.get_by_role('button', name='Create Task', exact=True).click()
    page.get_by_role('button', name='Save task', exact=True).click()
    expect(page.get_by_text('Title is required', exact=True)).to_be_visible()
    page.get_by_label(re.compile(r'^Title')).press_sequentially(marker)
    page.get_by_label('Project', exact=True).fill('Synthetic project')
    page.get_by_label('Due date', exact=True).fill('2026-11-01')
    page.get_by_role('button', name='Save task', exact=True).click()
    rows = page.locator('.task-list')
    expect(rows.get_by_text(marker, exact=True)).to_be_visible()
    page.get_by_role('button', name='Edit ' + marker, exact=True).click()
    page.get_by_label(re.compile(r'^Title')).fill(edited)
    page.get_by_role('button', name='Save task', exact=True).click()
    page.reload()
    expect(rows.get_by_text(edited, exact=True)).to_be_visible()
    page.get_by_role('checkbox', name='Mark ' + edited + ' complete', exact=True).check()
    page.get_by_role('button', name='Active', exact=True).click()
    expect(rows.get_by_text(edited, exact=True)).to_have_count(0)
    page.get_by_role('button', name='Completed', exact=True).click()
    expect(rows.get_by_text(edited, exact=True)).to_be_visible()
    other = context.new_page()
    try:
        other.goto(page.url)
        expect(other.locator('.task-list').get_by_text(edited, exact=True)).to_be_visible()
    finally:
        other.close()
    control = page.get_by_role('button', name='Delete ' + edited, exact=True)
    confirm(page, control, 'Delete this task?', False)
    expect(rows.get_by_text(edited, exact=True)).to_be_visible()
    confirm(page, control, 'Delete this task?', True)
    expect(rows.get_by_text(edited, exact=True)).to_have_count(0)
    page.reload()
    page.get_by_role('button', name='All', exact=True).click()
    expect(rows.get_by_text(edited, exact=True)).to_have_count(0)
    for seed in ('Design landing hero', 'Create icon set', 'Review sprint goals'):
        expect(rows.get_by_text(seed, exact=True)).to_be_visible()
    return {'passed': True, 'checks': ['required title', 'keyboard typing', 'create/edit',
        'reload/new-tab persistence', 'completion/filtering', 'cancel deletion', 'confirmed deletion/reload', 'sample records preserved']}


def booking(page, context, expect, width):
    marker = f'Genesys verification customer {width}'
    page.locator('.hero').get_by_role('link', name='Book a workshop', exact=True).click()
    page.get_by_role('button', name='Confirm booking', exact=True).click()
    expect(page.get_by_text('Please enter your full name.', exact=True)).to_be_visible()
    expect(page.get_by_text('Please choose a workshop.', exact=True)).to_be_visible()
    name = page.get_by_label('Full name', exact=True)
    name.press_sequentially(marker)
    typing = name.input_value() == marker and name.evaluate('el=>el===document.activeElement')
    # Continue separate state/persistence checks with programmatic fill; this
    # never erases the observed keyboard failure from the overall result.
    name.fill(marker)
    page.get_by_label('Workshop', exact=True).select_option('wheel')
    page.get_by_label('Date and time', exact=True).fill('2026-11-01T12:00')
    page.get_by_label('Email', exact=True).fill('invalid')
    page.get_by_role('button', name='Confirm booking', exact=True).click()
    expect(page.get_by_text('Please enter a valid email address.', exact=True)).to_be_visible()
    page.get_by_label('Email', exact=True).fill('fixture@example.test')
    page.get_by_role('button', name='Confirm booking', exact=True).click()
    expect(page.get_by_role('heading', name='Booking confirmed', exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role('heading', name='Booking confirmed', exact=True)).to_be_visible()
    page.get_by_role('link', name='View my bookings', exact=True).click()
    expect(page.get_by_text(marker, exact=False)).to_be_visible()
    other = context.new_page()
    try:
        other.goto(page.url)
        expect(other.get_by_text(marker, exact=False)).to_be_visible()
    finally:
        other.close()
    control = page.get_by_role('button', name='Cancel', exact=True)
    message = 'Cancel this booking? This will remove it from your local browser.'
    confirm(page, control, message, False)
    expect(page.get_by_text(marker, exact=False)).to_be_visible()
    confirm(page, control, message, True)
    expect(page.get_by_text(marker, exact=False)).to_have_count(0)
    page.reload()
    expect(page.get_by_text(marker, exact=False)).to_have_count(0)
    return {'passed': typing, 'keyboardTypingPassed': typing,
        'checks': ['required/email validation', 'booking/confirmation', 'confirmation reload',
                   'reload/new-tab persistence', 'cancel dismissal', 'confirmed cancellation/reload'],
        'failures': [] if typing else ['Name input remounts during typing and loses focus; only the first character is entered.']}


def run(folder):
    from playwright.sync_api import sync_playwright, expect
    expect.set_options(timeout=4000)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for case, check in (('booking', booking), ('dashboard', dashboard)):
                entry = folder / case / 'app' / 'dist' / 'index.html'
                server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(entry.parent)))
                threading.Thread(target=server.serve_forever, daemon=True).start()
                base = f'http://127.0.0.1:{server.server_port}/'
                try:
                    for width in (1440, 390):
                        context = browser.new_context(viewport={'width': width, 'height': 1000})
                        context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base)
                                      and r.request.method in {'GET', 'HEAD'} else r.abort())
                        page = context.new_page()
                        page.set_default_timeout(6000)
                        errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        try:
                            page.goto(base)
                            result = check(page, context, expect, width)
                            result.update(case=case, width=width, runtimeErrors=errors)
                            result['passed'] = result['passed'] and not errors
                        except Exception as error:
                            result = {'case': case, 'width': width, 'passed': False,
                                      'error': str(error), 'runtimeErrors': errors}
                        finally:
                            context.close()
                        rows.append(result)
                        print(json.dumps({'case': case, 'width': width, 'passed': result['passed']}), flush=True)
                        (folder / 'reviewed-workflows.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
                finally:
                    server.shutdown()
        finally:
            browser.close()
    (folder / 'reviewed-workflows.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    results = run(args.folder.resolve())
    print(json.dumps(results, indent=2))
    sys.exit(0 if all(row['passed'] for row in results) else 1)
