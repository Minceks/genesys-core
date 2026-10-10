"""Publish immutable build output without exposing in-progress source edits."""

import json
import shlex

SERVER_SOURCE = '''import os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
directory = os.path.abspath(sys.argv[1])
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    def do_GET(self):
        if not os.path.exists(self.translate_path(self.path)) and 'text/html' in self.headers.get('Accept', ''):
            self.path = '/index.html'
        super().do_GET()
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()
    def log_message(self, *args):
        pass
ThreadingHTTPServer(('0.0.0.0', 4174), Handler).serve_forever()
'''


def verified_preview(workspace, checkpoint=None):
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    root = REMOTE_PROJECT_ROOT
    if checkpoint:
        # Assets are content hashed. Retain previous assets for already-open tabs.
        script = '''import json, pathlib, shutil
root = pathlib.Path(%s)
live = root.parent / '.genesys-verified-preview'
staged = root.parent / '.genesys-verified-next'
old = root.parent / '.genesys-verified-old'
shutil.rmtree(staged, ignore_errors=True)
shutil.copytree(root / 'dist', staged)
if (live / 'assets').exists():
    shutil.copytree(live / 'assets', staged / 'assets', dirs_exist_ok=True)
(staged / '.proof.json').write_text(%s)
shutil.rmtree(old, ignore_errors=True)
if live.exists(): live.rename(old)
staged.rename(live)
shutil.rmtree(old, ignore_errors=True)
'''
        proof = {key: checkpoint[key] for key in ('checkpointId', 'commit')}
        script = script % (repr(root), repr(json.dumps(proof)))
        result = workspace.sandbox.process.exec('python3 -c ' + shlex.quote(script), timeout=45)
        if result.exit_code != 0:
            raise RuntimeError('Verified snapshot could not be published.')
    check = workspace.sandbox.process.exec(
        'test -f ../.genesys-verified-preview/index.html && test -f ../.genesys-verified-preview/.proof.json',
        cwd=root, timeout=10,
    )
    if check.exit_code != 0:
        return None
    server = root + '/../.genesys-verified-server.py'
    workspace.sandbox.fs.upload_file(SERVER_SOURCE.encode(), server)
    health = workspace.sandbox.process.exec('curl -fsS --max-time 2 http://127.0.0.1:4174/ -o /dev/null', timeout=5)
    if health.exit_code != 0:
        result = workspace.sandbox.process.exec(
            'nohup python3 ../.genesys-verified-server.py ../.genesys-verified-preview > /tmp/genesys-verified-preview.log 2>&1 < /dev/null &',
            cwd=root, timeout=10,
        )
        if result.exit_code != 0:
            raise RuntimeError('Verified preview server could not start.')
        import time
        for _ in range(10):
            health = workspace.sandbox.process.exec('curl -fsS --max-time 2 http://127.0.0.1:4174/ -o /dev/null', timeout=5)
            if health.exit_code == 0:
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Verified preview server is unavailable.')
    signed = workspace.sandbox.create_signed_preview_url(4174, expires_in_seconds=3600)
    return signed.url


def restore_verified(workspace):
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    result = workspace.sandbox.process.exec('cat ../.genesys-verified-preview/.proof.json', cwd=REMOTE_PROJECT_ROOT, timeout=10)
    if result.exit_code != 0:
        raise ValueError('No verified version is available yet.')
    proof = json.loads(result.result)
    # Preserve failed tracked and untracked edits before the existing reset operation.
    saved = workspace.sandbox.process.exec(
        "git stash push --include-untracked -m 'Before restoring verified version'", cwd=REMOTE_PROJECT_ROOT, timeout=30,
    )
    if saved.exit_code != 0:
        raise RuntimeError('Current edits could not be backed up; restore cancelled.')
    return workspace.rollback_to_checkpoint(proof['checkpointId'])
