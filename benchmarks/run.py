"""Offline by default. Run reference fixtures or a reviewed generated-app manifest."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import itertools
from pathlib import Path
import re
import sys
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.functional_verification import verify_functions
from agent.visual_quality import SNAPSHOT_SCRIPT, assess_visual_quality


class ReviewedPlan:
    def __init__(self, plan): self.plan = plan
    def generate(self, messages, tools):
        if self.plan is None:
            raise RuntimeError('No trusted recipe matched; supply a reviewed plan. No AI provider was called.')
        if messages[0]['content'].startswith('You are a browser verification planner.'):
            return SimpleNamespace(text=json.dumps(self.plan))
        return SimpleNamespace(text=json.dumps({'kind': 'verification_failure', 'evidence': 'Inspect recorded benchmark assertions.'}))


def run(manifest_path, output, allow_remote=False, presentation_regression=False):
    from playwright.sync_api import sync_playwright
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for case in manifest['cases']:
            if not re.fullmatch('[a-z0-9-]+', case['id']): raise ValueError('Invalid case ID')
            server = None
            if case.get('path'):
                path = (manifest_path.parent / case['path']).resolve()
                server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(path.parent)))
                threading.Thread(target=server.serve_forever, daemon=True).start()
                url = f'http://127.0.0.1:{server.server_port}/{path.name}'
                sources = {'app': path.read_text(encoding='utf-8')} if path.suffix == '.html' else {}
            else:
                url = case['url']
                if urlsplit(url).scheme not in {'http', 'https'}: raise ValueError('HTTP URL required')
                if not allow_remote and urlsplit(url).hostname not in {'127.0.0.1', 'localhost'}:
                    raise ValueError('Use --allow-remote for reviewed remote app URLs')
                sources = {name: (manifest_path.parent / source_path).read_text(encoding='utf-8') for name, source_path in case.get('sources', {}).items()}
            if case.get('sources'):
                sources = {name: (manifest_path.parent / path).read_text(encoding='utf-8') for name,path in case['sources'].items()}
            try:
                variants = ('baseline', 'presentation-edit') if presentation_regression else ('baseline',)
                for variant, width in itertools.product(variants, (1440, 390)):
                    context = browser.new_context(viewport={'width': width, 'height': 900})
                    if variant == 'presentation-edit':
                        # Apply only CSS, across every reload, while retaining the
                        # original request, source handlers and acceptance checks.
                        css = 'h1{letter-spacing:-.045em} main{padding-top:32px} button{border-radius:12px} input,textarea,select{border-radius:10px}'
                        context.add_init_script('document.addEventListener("DOMContentLoaded",()=>{const style=document.createElement("style");style.textContent='+json.dumps(css)+';document.head.append(style)});')
                    # Verification fixtures never send writes, mail or payments.
                    context.route('**/*', lambda route: route.continue_() if route.request.method in {'GET','HEAD','OPTIONS'} else route.abort())
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    started = time.perf_counter()
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    loaded = time.perf_counter()
                    snapshot = page.evaluate(SNAPSHOT_SCRIPT)
                    screenshot = f'{case["id"]}-{variant}-{width}.png'
                    page.screenshot(path=str(output / screenshot), animations='disabled')
                    quality = assess_visual_quality([snapshot])
                    result = verify_functions(page, case['prompt'], ReviewedPlan(case.get('plan')), attempt=1,
                                              sources=sources, contract=case['contract'])
                    result.pop('_verifiedPlan', None)
                    row = {'case': case['id'], 'variant':variant, 'width': width, 'loadSeconds': round(loaded-started, 3),
                           'verificationSeconds': round(time.perf_counter()-loaded, 3), 'screenshot': screenshot,
                           'visual': quality, 'verification': result, 'runtimeErrors': errors,
                           'buildMetrics': case.get('buildMetrics'), 'modelCallsDuringBenchmark': 0}
                    row['passed'] = quality['status'] == 'success' and not result.get('issues') and not result.get('unverifiedCore') and not errors
                    rows.append(row)
                    context.close()
            finally:
                if server: server.shutdown()
        browser.close()
    report = {'suite': manifest['suite'], 'scope': 'Reviewed UI behavior/layout, not subjective beauty or fresh AI generation.',
              'passed': sum(row['passed'] for row in rows), 'total': len(rows), 'results': rows}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Benchmark results', '', report['scope'], '', '| Case | Variant | Width | Passed | Load seconds | Check seconds |', '|---|---|---:|---|---:|---:|']
    lines += [f'| {row["case"]} | {row["variant"]} | {row["width"]} | {row["passed"]} | {row["loadSeconds"]} | {row["verificationSeconds"]} |' for row in rows]
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default=str(Path(__file__).with_name('reference.json')))
    parser.add_argument('--output', default='.verification-evidence/benchmarks')
    parser.add_argument('--allow-remote', action='store_true')
    parser.add_argument('--presentation-regression', action='store_true', help='Repeat unchanged behavior checks after a CSS-only edit on each viewport')
    args = parser.parse_args()
    report = run(args.manifest, args.output, args.allow_remote, args.presentation_regression)
    print(f'{report["passed"]}/{report["total"]} benchmark viewports passed; report: {args.output}/report.md')
    raise SystemExit(0 if report['passed'] == report['total'] else 1)
