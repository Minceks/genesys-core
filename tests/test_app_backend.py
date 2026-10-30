import pytest
from agent.app_backend import validate,source


def test_backend_accepts_only_dedicated_public_configuration(monkeypatch):
    url='https://abcdefghijklmnopqrst.supabase.co';key='sb_publishable_abcdefghijklmnopqrst'
    assert validate({'url':url,'publishableKey':key})==(url,key)
    for invalid in ['sb_secret_abcdefghijklmnopqrst','eyJ.service_role.secret','anything']:
        with pytest.raises(ValueError):validate({'url':url,'publishableKey':invalid})
    monkeypatch.setenv('SUPABASE_URL',url)
    with pytest.raises(ValueError,match='separate'):validate({'url':url,'publishableKey':key})


@pytest.mark.parametrize('url',['http://localhost','https://127.0.0.1','https://user:pass@abcdefghijklmnopqrst.supabase.co','https://abcdefghijklmnopqrst.supabase.co/?token=x'])
def test_backend_rejects_unsafe_or_credentialed_urls(url):
    with pytest.raises(ValueError):validate({'url':url,'publishableKey':'sb_publishable_abcdefghijklmnopqrst'})


def test_client_does_not_claim_provisioning_or_persist_auth_secrets():
    content=source('https://abcdefghijklmnopqrst.supabase.co','sb_publishable_exampleexample')
    assert 'persistSession: false' in content
    assert 'does not create tables' in content


def test_backend_install_saves_version_before_sdk_and_client_writes(monkeypatch):
    from types import SimpleNamespace
    from agent.app_backend import install
    events=[]
    monkeypatch.delenv('SUPABASE_URL',raising=False)
    monkeypatch.setattr('agent.builder_controls.assert_writable',lambda *args:None)
    monkeypatch.setattr('agent.version_history.operate',lambda *args,**kw:events.append('backup'))
    workspace=SimpleNamespace(project_id='app',sandbox=SimpleNamespace(process=SimpleNamespace(
        exec=lambda *args,**kw:events.append('install') or SimpleNamespace(exit_code=0))),
        write_file=lambda path,content:events.append('write') or {'status':'success'})
    result=install(workspace,{'url':'https://abcdefghijklmnopqrst.supabase.co','publishableKey':'sb_publishable_abcdefghijklmnopqrst'})
    assert events==['backup','install','write']
    assert result['configured'] and not result['verified']
