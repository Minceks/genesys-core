"""Read-only post-deployment checks of persisted customer previews."""
import hashlib
from html.parser import HTMLParser
import json
import logging
import os
import re
import threading
import time
from urllib.parse import urljoin, urlsplit
import uuid

import httpx

log = logging.getLogger(__name__)
ASSET_CDNS = {'fonts.googleapis.com', 'fonts.gstatic.com', 'images.unsplash.com', 'cdn.jsdelivr.net', 'unpkg.com'}


class Assets(HTMLParser):
    def __init__(self):
        super().__init__(); self.items = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'script' and values.get('src'):
            self.items.append((values['src'], 'script'))
        elif tag == 'link' and 'stylesheet' in values.get('rel', '').split() and values.get('href'):
            self.items.append((values['href'], 'style'))
        elif tag == 'link' and 'icon' in values.get('rel', '').split() and values.get('href'):
            self.items.append((values['href'], 'image'))


def saved_targets(limit=2):
    from .preview_hosting import configured, directory, root
    if not configured(): return []
    domain = os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip().lower()
    if not re.fullmatch(r'[a-z0-9.-]+', domain): return []
    base = root()
    if not base.is_dir(): return []
    targets = []
    for path in sorted(base.iterdir(), key=lambda item: item.name):
        if re.fullmatch(r'[0-9a-f]{32}', path.name) and directory(path.name):
            targets.append({'ticket': path.name, 'url': f'https://{path.name}.{domain}/'})
        if len(targets) >= limit: break
    return targets


def _read(client, url, limit, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0: raise TimeoutError('Deployment check time budget exhausted')
    with client.stream('GET', url, timeout=min(12, remaining), headers={'Range': f'bytes=0-{limit - 1}'}) as response:
        if response.status_code not in {200, 206}:
            raise ValueError(f'HTTP {response.status_code} for {urlsplit(url).path}')
        data = bytearray()
        for part in response.iter_bytes(chunk_size=16384):
            data.extend(part)
            if len(data) >= limit: break
        return bytes(data[:limit]), response.headers.get('Content-Type', '').lower()


def check_http(url, deadline, client=None):
    owns = client is None
    client = client or httpx.Client(follow_redirects=False, trust_env=False)
    try:
        body, mime = _read(client, url, 512000, deadline)
        if 'text/html' not in mime or not re.search(rb'<[a-zA-Z!]', body):
            raise ValueError('Saved preview did not return HTML')
        parser = Assets(); parser.feed(body.decode('utf-8', errors='replace'))
        origin = urlsplit(url)
        assets, skipped = [], 0
        for source, kind in list(dict.fromkeys(parser.items))[:16]:
            target = urljoin(url, source)
            parsed = urlsplit(target)
            if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc) or parsed.username or parsed.password:
                skipped += 1; continue
            if len(target) > 2048 or any(ord(char) < 32 for char in target):
                raise ValueError('Invalid local asset URL')
            content, asset_mime = _read(client, target, 65536, deadline)
            if not content: raise ValueError('Empty local asset: ' + parsed.path)
            if kind == 'script' and not any(value in asset_mime for value in ('javascript', 'ecmascript')):
                raise ValueError('JavaScript asset returned an incorrect content type: ' + parsed.path)
            if kind == 'style' and 'text/css' not in asset_mime:
                raise ValueError('Stylesheet returned an incorrect content type: ' + parsed.path)
            if kind == 'image' and not asset_mime.startswith('image/'):
                raise ValueError('Icon returned an incorrect content type: ' + parsed.path)
            assets.append(parsed.path)
        return {'assetsChecked': assets, 'externalAssetsSkipped': skipped,
                'htmlSha256': hashlib.sha256(body).hexdigest()}
    finally:
        if owns: client.close()


def check_browser(url, deadline):
    from playwright.sync_api import sync_playwright
    origin = urlsplit(url).netloc
    results, blocked = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for width, height in ((1280, 800), (390, 844)):
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise TimeoutError('Browser check time budget exhausted')
                context = browser.new_context(viewport={'width': width, 'height': height}, service_workers='block')
                errors, failures = [], []
                def read_only(route):
                    request = route.request; target = urlsplit(request.url)
                    allowed = (request.method in {'GET', 'HEAD'} and target.scheme == 'https'
                               and (target.netloc == origin or (target.hostname in ASSET_CDNS
                                    and request.resource_type in {'script', 'stylesheet', 'font', 'image'})))
                    if allowed: route.continue_()
                    else: blocked.append(request.resource_type); route.abort()
                context.route('**/*', read_only)
                if hasattr(context, 'route_web_socket'):
                    context.route_web_socket('**/*', lambda socket: socket.close())
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)[:300]))
                page.on('response', lambda response: failures.append(urlsplit(response.url).path)
                        if response.status >= 400 and urlsplit(response.url).netloc == origin else None)
                try:
                    response = page.goto(url, wait_until='domcontentloaded', timeout=min(15000, int(remaining * 1000)))
                    if not response or response.status != 200: raise ValueError('Browser could not open saved preview')
                    page.wait_for_function('''() => document.body &&
                        (document.body.innerText.trim().length >= 10 || [...document.querySelectorAll('canvas,svg,video,img')]
                        .some(el=>{const r=el.getBoundingClientRect();return r.width>40&&r.height>40}))''', timeout=10000)
                    page.wait_for_timeout(300)
                    if failures: raise ValueError('Browser asset failures: ' + ', '.join(failures[:5]))
                    if errors: raise ValueError('Browser runtime errors: ' + '; '.join(errors[:2]))
                    results.append({'width': width, 'rendered': True, 'runtimeErrors': errors,
                                    'status': 'limited' if errors else 'passed'})
                finally:
                    context.close()
        finally:
            browser.close()
    return {'viewports': results, 'blockedRequests': len(blocked),
            'scope': 'Fresh browser contexts; no clicks, existing sessions or write requests. External integration calls are not exercised.'}


def run_checks():
    from .preview_hosting import directory
    targets = saved_targets()
    deadline = time.monotonic() + 100
    results = []
    for target in targets:
        try:
            http = check_http(target['url'], deadline)
            rendered = check_browser(target['url'], deadline)
            results.append({'ticket': target['ticket'], 'status': 'warning' if any(view['status'] != 'passed' for view in rendered['viewports']) else 'passed',
                            'http': http, 'browser': rendered})
        except Exception as error:
            results.append({'ticket': target['ticket'], 'status': 'failed' if directory(target['ticket']) else 'skipped',
                            'error': str(error)[:600]})
    status = ('failed' if any(item['status'] == 'failed' for item in results) else
              'warning' if any(item['status'] == 'warning' for item in results) else
              'passed' if any(item['status'] == 'passed' for item in results) else 'skipped')
    return {'status': status, 'checkedAt': int(time.time()), 'projects': results,
            'scope': 'Saved preview availability, local assets and desktop/phone rendering; not functional, security or aesthetic certification.'}


def persist_report(result):
    from .preview_hosting import root
    directory = root().parent / 'deployment-smoke'; directory.mkdir(parents=True, exist_ok=True)
    staged = directory / (uuid.uuid4().hex + '.json')
    staged.write_text(json.dumps(result), encoding='utf-8')
    os.replace(staged, directory / 'latest.json')


class DeploymentChecks:
    def __init__(self):
        self.lock = threading.Lock(); self.running = False; self.pending = []; self.seen = set()
        self.report = {'status': 'not_run', 'projects': []}

    def schedule(self, trigger):
        trigger = str(trigger)[:160]
        with self.lock:
            if trigger in self.seen: return False
            if len(self.pending) >= 5: return False
            self.seen.add(trigger)
            if len(self.seen) > 200: self.seen = {trigger}
            self.pending.append(trigger)
            if self.running: return True
            self.running = True
        threading.Thread(target=self._run, daemon=True, name='deployment-smoke').start()
        return True

    def _run(self):
        triggers = []
        try:
            time.sleep(3)
            with self.lock:
                triggers, self.pending = self.pending, []
            self.report = {'status': 'waiting_for_rollout', 'projects': []}
            # Public routing switches only after Railway accepts the new worker.
            deployment = os.getenv('RAILWAY_DEPLOYMENT_ID', '')
            backend = os.getenv('GENESYS_SMOKE_BACKEND_URL', '').rstrip('/')
            if not backend and os.getenv('RAILWAY_PUBLIC_DOMAIN'):
                backend = 'https://' + os.environ['RAILWAY_PUBLIC_DOMAIN']
            if deployment and backend:
                rollout_deadline = time.monotonic() + 180
                for _ in range(60):
                    if time.monotonic() >= rollout_deadline: raise TimeoutError('Public rollout check timed out')
                    try:
                        value = httpx.get(backend + '/health', timeout=4, follow_redirects=False).json()
                        if value.get('deploymentId') == deployment: break
                    except Exception: pass
                    time.sleep(3)
                else: raise TimeoutError('Public backend has not switched to this deployment')
            self.report = {'status': 'checking', 'projects': []}
            result = {**run_checks(), 'deploymentId': deployment, 'triggers': triggers}
            persist_report(result)
            self.report = result
            log.log(logging.ERROR if result['status'] == 'failed' else logging.INFO,
                    'deployment_smoke_result %s', json.dumps(result))
        except Exception as error:
            self.report = {'status': 'failed', 'projects': [], 'error': str(error)[:500],
                           'checkedAt': int(time.time()), 'triggers': triggers}
            try: persist_report(self.report)
            except Exception: log.exception('deployment_smoke_report_save_failed')
            log.exception('deployment_smoke_failed')
        finally:
            with self.lock:
                self.running = False
                pending = bool(self.pending)
                if pending: self.running = True
            if pending:
                threading.Thread(target=self._run, daemon=True, name='deployment-smoke-followup').start()

    def summary(self):
        value = self.report
        return {'status': value['status'], 'projectsChecked': len(value.get('projects', [])),
                'failed': sum(item.get('status') == 'failed' for item in value.get('projects', [])),
                **({'checkedAt': value['checkedAt']} if value.get('checkedAt') else {})}


checks = DeploymentChecks()


def start_checks():
    if os.getenv('RAILWAY_ENVIRONMENT_ID') and os.getenv('GENESYS_DEPLOY_SMOKE_ENABLED', '1') != '0':
        checks.schedule('backend:' + os.getenv('RAILWAY_DEPLOYMENT_ID', 'startup'))
