"""Build a standalone release using only allowlisted public browser settings."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit
import base64
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
settings = {**dotenv_values(root / '.env'), **os.environ}
public = {
    'VITE_SUPABASE_URL': settings.get('VITE_SUPABASE_URL') or settings.get('SUPABASE_URL'),
    'VITE_SUPABASE_PUBLISHABLE_KEY': settings.get('VITE_SUPABASE_PUBLISHABLE_KEY') or settings.get('SUPABASE_PUBLISHABLE_KEY'),
    'VITE_CLOUD_AGENT_URL': settings.get('VITE_CLOUD_AGENT_URL') or 'https://remarkable-generosity-production-7d5a.up.railway.app',
}
if not all(public.values()):
    raise SystemExit('Missing public frontend configuration: ' + ', '.join(key for key, value in public.items() if not value))
for key in ('VITE_SUPABASE_URL', 'VITE_CLOUD_AGENT_URL'):
    url = urlsplit(public[key])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise SystemExit('Production HTTPS URL required for ' + key)
key = public['VITE_SUPABASE_PUBLISHABLE_KEY']
if not key.startswith('sb_publishable_'):
    try:
        payload = key.split('.')[1]
        role = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4))).get('role')
    except Exception:
        role = None
    if role != 'anon':
        raise SystemExit('Frontend key must be a public publishable/anon key, never a service-role or secret key.')
check = root / '.builder-ui-check'
check.mkdir(exist_ok=True)
shutil.copytree(root / 'src', check / 'src', dirs_exist_ok=True)
for name in ('package.json', 'package-lock.json', 'index.html', 'vite.config.ts'):
    shutil.copyfile(root / name, check / name)
npm = 'npm.cmd' if os.name == 'nt' else 'npm'
subprocess.run([npm, 'ci', '--ignore-scripts'], cwd=check, check=True)
# Do not inherit server credentials or arbitrary VITE_ variables into the build.
environment = {name: value for name, value in os.environ.items() if name in {
    'PATH','Path','SystemRoot','SYSTEMROOT','TEMP','TMP','APPDATA','LOCALAPPDATA','USERPROFILE','COMSPEC','ComSpec','PATHEXT'}}
environment.update(public)
subprocess.run([npm, 'run', 'build'], cwd=check, env=environment, check=True)
release = root.parent / 'railway-frontend-deploy'
release.mkdir(exist_ok=True)
if (release / 'dist').exists():
    # Fixed, verified workspace child; remove only the prior generated assets.
    target = (release / 'dist').resolve()
    if target.parent != release.resolve(): raise RuntimeError('Unexpected release target')
    shutil.rmtree(target)
shutil.copytree(check / 'dist', release / 'dist')
shutil.copyfile(root / 'frontend_host.py', release / 'frontend_host.py')
shutil.copyfile(root / 'deployment_notify.py', release / 'deployment_notify.py')
(release / 'requirements.txt').write_text('Flask>=3,<4\ngunicorn>=23,<27\n', encoding='utf-8')
(release / '.python-version').write_text('3.14\n', encoding='utf-8')
(release / 'Dockerfile').write_text('FROM python:3.14-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY frontend_host.py deployment_notify.py ./\nCOPY dist ./dist\nENV PORT=8080\nCMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - frontend_host:app"]\n', encoding='utf-8')
(release / 'railway.toml').write_text('[deploy]\nstartCommand = "gunicorn --bind 0.0.0.0:$PORT --workers 2 --access-logfile - frontend_host:app"\nhealthcheckPath = "/health"\nhealthcheckTimeout = 30\n', encoding='utf-8')
manifest = {str(path.relative_to(release)).replace('\\','/'): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (release / 'dist').rglob('*') if path.is_file()}
(release / 'release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Standalone frontend release prepared:', release)
