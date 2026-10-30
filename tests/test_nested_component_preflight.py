import os
from pathlib import Path
import subprocess

import pytest

from agent.react_preflight import HOOK_PREFLIGHT


@pytest.mark.parametrize('source,rejected', [
    ('export default function App(){ function Form(){return <input/>} return <Form/> }', True),
    ('export default function App(){ const Form=()=> <input/>; return <Form/> }', True),
    ('export default function App(){ return <Form/>; function Form(){return <input/>} }', True),
    ('import {memo} from "react"; export default function App(){const Form=memo(()=> <input/>); return <Form/>}', True),
    ('export default ()=>{function Form(){return <input/>} return <Form/>}', True),
    ('function Form(){return <input/>} export default function App(){return <Form/>}', False),
    ('export default function App(){function unused(){return <input/>} return <input/>}', False),
    ('export default function App(){const renderForm=()=> <input/>;return renderForm()}', False),
    ('import {useMemo} from "react"; export default function App(){const Form=useMemo(()=>()=> <input/>,[]);return <Form/>}', False),
    ('export default function App(){function Form(){return <input/>}return [].map(Form=><Form/>)}', False),
    ('export default function App(){function Form(){return <input/>}const render=({Form})=><Form/>;return render({Form:null})}', False),
])
def test_rendered_component_identity_is_stable(tmp_path, source, rejected):
    (tmp_path / 'src').mkdir()
    entry = tmp_path / 'src' / 'App.jsx'
    entry.write_text(source)
    root = Path(__file__).resolve().parents[1]
    modules = root / 'node_modules'
    if not (modules / 'esbuild').exists():
        modules = root / '.verification-node-deps' / 'node_modules'
    result = subprocess.run(['node', '-e', HOOK_PREFLIGHT], cwd=tmp_path,
        env=dict(os.environ, NODE_PATH=str(modules)), capture_output=True, text=True)
    assert result.returncode == (1 if rejected else 0), result.stdout + result.stderr
    if rejected:
        assert 'loses input focus/state' in result.stderr
    assert entry.read_text() == source
