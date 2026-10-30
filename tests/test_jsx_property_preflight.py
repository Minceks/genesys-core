import os
from pathlib import Path
import subprocess

import pytest

from agent.react_preflight import HOOK_PREFLIGHT


@pytest.mark.parametrize(('source', 'expected'), [
    (r'export default () => <text fontFamily="\"Avenir Next\"">Logo</text>', 'src/App.jsx:1:'),
    ('export default () => <svg><stop stop-color="red" /></svg>', 'Use stopColor'),
    ('export default () => <svg><path stroke-width="2" /></svg>', 'Use strokeWidth'),
    ('export default () => <svg aria-label="Logo" data-testid="logo"><stop stopColor="red" /></svg>', None),
    ('const Icon = () => null; export default () => <Icon stop-color="red" />', None),
])
def test_jsx_dom_properties_are_checked_without_rewriting_source(tmp_path, source, expected):
    (tmp_path / 'src').mkdir()
    entry = tmp_path / 'src' / 'App.jsx'
    entry.write_text(source)
    root = Path(__file__).resolve().parents[1]
    modules = root / 'node_modules'
    if not (modules / 'esbuild').exists():
        modules = root / '.verification-node-deps' / 'node_modules'
    env = dict(os.environ, NODE_PATH=str(modules))
    result = subprocess.run(['node', '-e', HOOK_PREFLIGHT], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert result.returncode == (1 if expected else 0), result.stdout + result.stderr
    if expected:
        assert expected in result.stderr
    assert entry.read_text() == source
