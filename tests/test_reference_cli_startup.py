import subprocess
from types import SimpleNamespace
import pytest
from scripts.check_reference_runtime import check_cli_runtime

def test_cli_check_retries_one_cold_timeout_and_requires_real_help():
    calls=[]
    def run(command,**kwargs):
        calls.append((command,kwargs))
        if len(calls)==1:raise subprocess.TimeoutExpired(command,kwargs['timeout'])
        return SimpleNamespace(returncode=0,stdout='Passively inspect a public page')
    check_cli_runtime(['node','installed-rea.mjs'],run)
    assert len(calls)==2 and all(options['timeout']==45 for _,options in calls)
    assert all(command==['node','installed-rea.mjs','inspect-web-page','--help'] for command,_ in calls)

def test_cli_timeout_remains_a_failure_after_two_attempts():
    calls=[]
    def run(command,**kwargs):calls.append(command);raise subprocess.TimeoutExpired(command,kwargs['timeout'])
    with pytest.raises(SystemExit,match='two cold-start attempts'):check_cli_runtime(['node','installed-rea.mjs'],run)
    assert len(calls)==2

@pytest.mark.parametrize('code,output',[(1,'Passively inspect'),(0,'Unrelated help')])
def test_cli_does_not_accept_missing_or_invalid_commands(code,output):
    with pytest.raises(SystemExit,match='unavailable'):
        check_cli_runtime(['node','installed-rea.mjs'],lambda *_args,**_kw:SimpleNamespace(returncode=code,stdout=output))
