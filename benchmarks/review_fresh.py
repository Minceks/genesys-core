"""Offline presentation evidence for exported fresh build bundles (no model calls)."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from agent.visual_quality import SNAPSHOT_SCRIPT, assess_visual_quality


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def review(folder):
    from playwright.sync_api import sync_playwright
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for case in ('store', 'portfolio', 'booking', 'dashboard'):
            out = folder / case
            entry = out / 'app' / 'dist' / 'index.html'
            if not entry.exists():
                rows.append({'case': case, 'rendered': False})
                continue
            server = ThreadingHTTPServer(('127.0.0.1', 0),
                functools.partial(QuietHandler, directory=str(entry.parent)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for width in (1440, 390):
                    context = browser.new_context(viewport={'width': width, 'height': 1000})
                    # Synthetic local apps must not contact services during review.
                    context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(
                        ('http://127.0.0.1:', 'data:', 'blob:')) else r.abort())
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.goto(f'http://127.0.0.1:{server.server_port}/', wait_until='networkidle')
                    shot = f'homepage-{width}.png'
                    page.screenshot(path=str(out / shot), animations='disabled', full_page=True)
                    snapshot = page.evaluate(SNAPSHOT_SCRIPT)
                    rows.append({'case': case, 'width': width, 'rendered': True,
                        'runtimeErrors': errors, 'screenshot': f'{case}/{shot}',
                        'layout': assess_visual_quality([snapshot], public_website=case!='dashboard'),
                        'scope': 'Homepage layout and runtime only; behavior is in full-pipeline result.json.'})
                    context.close()
            finally:
                server.shutdown()
        browser.close()
    (folder / 'presentation.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    print(json.dumps([{'case': r['case'], 'width': r.get('width'), 'rendered': r['rendered'],
        'layout': r.get('layout', {}).get('status')} for r in review(args.folder.resolve())]))
