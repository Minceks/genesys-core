"""Supabase identity and project access using the user's RLS-scoped token."""
import os
from uuid import UUID

import httpx


class AccessError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def configured():
    return bool(os.getenv('SUPABASE_URL') or os.getenv('SUPABASE_PUBLISHABLE_KEY'))


def call(method, path, token, **kwargs):
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
    if not url.startswith('https://') or not key:
        raise AccessError('User authentication is not configured.', 503)
    headers = {'apikey': key, 'Authorization': f'Bearer {token}'}
    headers.update(kwargs.pop('headers', {}))
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.request(method, url + path, headers=headers, **kwargs)
    except httpx.HTTPError:
        raise AccessError('Supabase is unavailable. Please retry.', 503) from None
    if response.status_code in (401, 403):
        raise AccessError('Invalid or expired session.', 401)
    if response.status_code >= 500:
        raise AccessError('Supabase is unavailable. Please retry.', 503)
    if response.status_code not in (200, 201):
        raise AccessError('Supabase request failed.', 502)
    try:
        return response.json()
    except ValueError:
        raise AccessError('Invalid Supabase response.', 502) from None


def current_user(authorization):
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise AccessError('Sign-in required.', 401)
    token = token.strip()
    user = call('GET', '/auth/v1/user', token)
    if not isinstance(user, dict) or not user.get('id'):
        raise AccessError('Invalid or expired session.', 401)
    return {'id': user['id'], 'access_token': token}


def owned_project(project_id, user):
    try:
        normalized = str(UUID(str(project_id)))
    except (ValueError, TypeError):
        raise AccessError('Project not found.', 404) from None
    if normalized != str(project_id):
        raise AccessError('Project not found.', 404)
    rows = call('GET', '/rest/v1/projects', user['access_token'], params={
        'select': 'id,name,owner_id,created_at', 'id': f'eq.{normalized}',
        'owner_id': f"eq.{user['id']}", 'limit': '1',
    })
    if not isinstance(rows, list):
        raise AccessError('Project lookup failed.', 502)
    if not rows or rows[0].get('owner_id') != user['id']:
        raise AccessError('Project not found.', 404)
    return rows[0]


def create_project(name, user):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200:
        raise AccessError('Project name must contain 1-200 characters.', 400)
    rows = call('POST', '/rest/v1/projects', user['access_token'],
        headers={'Prefer': 'return=representation'},
        json={'name': name.strip(), 'owner_id': user['id']})
    if not isinstance(rows, list) or not rows:
        raise AccessError('Project could not be created.', 502)
    return rows[0]
