"""Bring-your-own per-application backend, never Genesys account credentials."""
import json
import os
import re

PATH='src/appBackend.js'
SDK_VERSION='2.117.3'


def validate(value):
    url=str(value.get('url') or '').strip().rstrip('/')
    key=str(value.get('publishableKey') or '').strip()
    if not re.fullmatch(r'https://[a-z0-9]{10,64}\.supabase\.co',url):
        raise ValueError('Use your app Supabase project HTTPS URL.')
    if url==os.getenv('SUPABASE_URL','').rstrip('/'):
        raise ValueError('Use a separate app backend, not the Genesys account project.')
    if not re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]{12,200}',key):
        raise ValueError('Use a publishable key beginning sb_publishable_. Secret and service-role keys are not accepted.')
    return url,key


def source(url,key):
    return """// Public app configuration. Configure database RLS before exposing data.
import { createClient } from '@supabase/supabase-js'
export const appBackend = createClient(%s, %s, {
  auth: {persistSession: false, autoRefreshToken: true, detectSessionInUrl: false}
})
// Auth is memory-only until the app implements an explicit session policy.
// Use appBackend.auth, appBackend.from and appBackend.storage in real handlers.
// Configuration alone does not create tables, access policies or verified workflows.
""" % (json.dumps(url),json.dumps(key))


def install(workspace,value):
    from .builder_controls import assert_writable
    from .version_history import operate
    url,key=validate(value)
    for path in (PATH,'package.json','package-lock.json'):
        assert_writable(workspace.project_id,path)
    operate(workspace,'capture',label='Before app backend configuration')
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    result=workspace.sandbox.process.exec(
        f'npm install --save-exact @supabase/supabase-js@{SDK_VERSION} --ignore-scripts --no-audit --no-fund',
        cwd=REMOTE_PROJECT_ROOT,timeout=120)
    if result.exit_code!=0:raise RuntimeError('Backend SDK installation failed. The source version can be restored.')
    result=workspace.write_file(PATH,source(url,key))
    if result.get('status')!='success':raise RuntimeError('App backend configuration was not saved.')
    return {'configured':True,'provider':'supabase','url':url,'verified':False,
        'message':'App backend client configured. Tables, access policies, authentication settings and working app flows still require implementation and verification.'}
