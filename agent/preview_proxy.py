"""Register verified preview destinations with the separate proxy service."""
import os
import httpx


def publish_preview(url):
    service = os.getenv('GENESYS_PREVIEW_PROXY_URL', '').rstrip('/')
    if not service:
        return url
    key = os.getenv('GENESYS_PREVIEW_PROXY_KEY', '')
    if len(key) < 32 or not service.startswith(('https://', 'http://genesys-preview.railway.internal:')):
        raise RuntimeError('Preview proxy configuration is incomplete.')
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        response = client.post(service + '/internal/previews',
            headers={'X-GeneSys-Proxy-Key': key}, json={'url': url})
    response.raise_for_status()
    result = response.json()
    domain = os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip().lower()
    from urllib.parse import urlsplit
    parsed = urlsplit(result.get('url', ''))
    if not domain or parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.' + domain):
        raise RuntimeError('Preview proxy returned an invalid address.')
    return result['url']
