"""Credential-free reference reads, pinned to validated public IP addresses."""
import http.client
import gzip
import io
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, urlunsplit


class ReferenceBlocked(ValueError):
    pass


def public_ip(value):
    address=ipaddress.ip_address(value)
    return address.is_global and not address.is_multicast


def public_addresses(host):
    try:
        addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    except OSError as error:
        raise ReferenceBlocked('Reference hostname could not be resolved') from error
    if not addresses or any(not public_ip(ip) for ip in addresses):
        raise ReferenceBlocked('Reference must resolve only to public addresses')
    return addresses


def reference_url(value):
    parts = urlsplit(value)
    if parts.scheme not in {'https', 'http'} or not parts.hostname or parts.username or parts.password:
        raise ReferenceBlocked('Reference must be a public HTTP(S) URL without credentials')
    if parts.port not in {None, 80 if parts.scheme == 'http' else 443}:
        raise ReferenceBlocked('Nonstandard reference port')
    host = parts.hostname.encode('idna').decode('ascii').lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.test')):
        raise ReferenceBlocked('Private reference hostname')
    try:
        if not public_ip(host):
            raise ReferenceBlocked('Private reference address')
    except ValueError as error:
        if isinstance(error, ReferenceBlocked):
            raise
    netloc=f'[{host}]' if ':' in host else host
    if parts.port is not None:netloc+=':'+str(parts.port)
    return urlunsplit((parts.scheme, netloc, parts.path or '/', parts.query, ''))


def public_get(url, *, timeout=2, limit=2_000_000):
    """Do not let browser DNS resolution bypass the public-address check."""
    url = reference_url(url)
    parts = urlsplit(url)
    host = parts.hostname.encode('idna').decode('ascii')
    address = public_addresses(host)[0]
    port = 443 if parts.scheme == 'https' else 80
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    raw = socket.create_connection((address, port), timeout=timeout)
    try:
        connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host) if port == 443 else raw
        path = urlunsplit(('', '', parts.path or '/', parts.query, ''))
        connection.request('GET', path, headers={
            'Host': parts.netloc, 'User-Agent': 'GeneSys-ReferenceInspection/1.0',
            'Accept': '*/*', 'Accept-Encoding': 'identity',
        })
        response = connection.getresponse()
        if response.getheader('Content-Length') and int(response.getheader('Content-Length')) > limit:
            raise ReferenceBlocked('Reference resource exceeds limit')
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ReferenceBlocked('Reference resource exceeds limit')
        encoding=(response.getheader('Content-Encoding') or '').lower()
        if encoding=='gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
                body=compressed.read(limit+1)
            if len(body)>limit:
                raise ReferenceBlocked('Decompressed reference exceeds limit')
        elif encoding not in {'','identity'}:
            raise ReferenceBlocked('Unsupported reference content encoding')
        # A fresh browser has no account cookies. Do not install third-party cookies
        # or forward authentication, even if an inspected page asks for them.
        excluded = {'set-cookie', 'connection', 'transfer-encoding', 'content-length', 'content-encoding'}
        headers = {key: value for key, value in response.getheaders() if key.lower() not in excluded}
        return response.status, headers, body
    finally:
        connection.close()
        raw.close()
