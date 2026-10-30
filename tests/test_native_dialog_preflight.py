import os
from pathlib import Path
import subprocess

import pytest

from agent.react_preflight import HOOK_PREFLIGHT


@pytest.mark.parametrize('source,rejected', [
    ('export function remove(){return window.confirm("Remove?")}', True),
    ('export function remove(){return globalThis["confirm"]("Remove?")}', True),
    ('export function ask(){return prompt("Name")}', True),
    ('export function submit(){alert("Saved")}', True),
    ('export function remove(confirm){return confirm("Remove?")}', False),
    ('const confirm=()=>true; export function remove(){return confirm()}', False),
    ('export function remove(api){return api.confirm()}', False),
    ('export function remove(window){return window.confirm()}', False),
    ('export function remove(){ {const confirm=()=>true; confirm()} }', False),
    ('export default ()=><p>window.confirm("Remove?")</p>', False),
    ('export default ()=> <dialog open><button>Confirm</button><button>Cancel</button></dialog>', False),
])
def test_native_dialog_guard_is_read_only_and_respects_local_apis(tmp_path, source, rejected):
    (tmp_path/'src').mkdir()
    entry=tmp_path/'src/App.jsx'
    entry.write_text(source)
    root=Path(__file__).resolve().parents[1]
    modules=root/'node_modules'
    if not (modules/'esbuild').exists():
        modules=root/'.verification-node-deps/node_modules'
    result=subprocess.run(['node','-e',HOOK_PREFLIGHT],cwd=tmp_path,
        env=dict(os.environ,NODE_PATH=str(modules)),capture_output=True,text=True)
    assert result.returncode == int(rejected), result.stdout+result.stderr
    if rejected:
        assert 'browser-native' in result.stderr and 'in-page' in result.stderr
    assert entry.read_text()==source
