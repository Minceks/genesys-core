"""Notify the backend after a frontend deployment; credentials stay server-side."""
import json
import logging
import os
import threading
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def notify_deployment():
    key = os.getenv('GENESYS_DEPLOY_SMOKE_KEY', '')
    backend = os.getenv('GENESYS_SMOKE_BACKEND_URL', '').rstrip('/')
    parsed = urlsplit(backend)
    if (not os.getenv('RAILWAY_ENVIRONMENT_ID') or os.getenv('GENESYS_DEPLOY_SMOKE_ENABLED', '1') == '0'
            or len(key) < 32 or parsed.scheme != 'https'
            or not parsed.hostname or parsed.username or parsed.password): return
    deployment = os.getenv('RAILWAY_DEPLOYMENT_ID', 'startup')
    own_url = os.getenv('GENESYS_SMOKE_FRONTEND_URL', '').rstrip('/')
    if not own_url and os.getenv('RAILWAY_PUBLIC_DOMAIN'):
        own_url = 'https://' + os.environ['RAILWAY_PUBLIC_DOMAIN']
    def run():
        opener = build_opener(NoRedirects())
        body = json.dumps({'source': 'frontend', 'deploymentId': deployment}).encode()
        deadline = time.monotonic() + 180
        for _ in range(60):
            if time.monotonic() >= deadline: break
            try:
                if own_url:
                    with opener.open(own_url + '/health', timeout=4) as response:
                        if json.loads(response.read(4096)).get('deploymentId') != deployment:
                            time.sleep(3); continue
                request = Request(backend + '/internal/deployment-smoke', data=body, method='POST',
                                  headers={'Content-Type': 'application/json', 'X-GeneSys-Smoke-Key': key})
                with opener.open(request, timeout=5) as response:
                    if response.status == 202:
                        logging.getLogger(__name__).info('deployment_smoke_notified source=frontend')
                        return
            except Exception:
                pass
            time.sleep(3)
        logging.getLogger(__name__).error('deployment_smoke_notification_failed source=frontend')
    threading.Thread(target=run, daemon=True, name='frontend-deployment-smoke').start()
