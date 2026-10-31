from types import SimpleNamespace

import pytest

from agent.build_repair import default_import_fix
from agent.daytona_workspace import DaytonaWorkspace


ERROR = 'error during build:\nsrc/App.jsx (5:9): "HomePage" is not exported by "src/pages/HomePage.jsx", imported by "src/App.jsx".'


def reader(app, page='export default function HomePage(){return null}'):
    return lambda path: {'src/App.jsx': app, 'src/pages/HomePage.jsx': page}[path]


@pytest.mark.parametrize('before,after', [
    ("import { HomePage } from '@/pages/HomePage'", "import HomePage from '@/pages/HomePage'"),
    ('import { HomePage, heroCopy } from "./pages/HomePage.jsx"', 'import HomePage, { heroCopy } from "./pages/HomePage.jsx"'),
    ("import { HomePage as Landing } from '@/pages/HomePage'", "import Landing from '@/pages/HomePage'"),
])
def test_default_export_imported_by_name_is_rewritten(before, after):
    path, fixed = default_import_fix(ERROR, reader(before + '\nimport { StoreShell } from "@/components/StoreShell"'))
    assert path == 'src/App.jsx' and fixed.startswith(after) and 'StoreShell' in fixed


def test_other_files_and_real_missing_exports_are_left_for_repair():
    assert default_import_fix('Unexpected token', reader('')) is None
    assert default_import_fix(ERROR, reader("import { HomePage } from '@/pages/HomePage'", 'export const other = 1')) is None
    assert default_import_fix(ERROR, reader("import { HomePage } from '@/other/Thing'")) is None


def workspace(results, files=None):
    calls = []
    def execute(*_, **__):
        calls.append(1)
        code, text = results.pop(0)
        return SimpleNamespace(exit_code=code, result=text)
    built = DaytonaWorkspace.__new__(DaytonaWorkspace)
    built.sandbox = SimpleNamespace(id='sandbox', process=SimpleNamespace(exec=execute))
    built.project_id = 'project'
    written = {}
    built.read_file = lambda path: {'content': (files or {}).get(path, '')}
    built.write_file = lambda path, content: written.update({path: content}) or {'status': 'success'}
    return built, calls, written


def test_killed_build_retries_without_entering_repair():
    built, calls, _ = workspace([(137, 'Killed'), (0, 'built')])
    assert built.run_build()['success'] is True and len(calls) == 2


def test_build_killed_twice_is_reported():
    built, calls, _ = workspace([(137, 'Killed'), (137, 'Killed')])
    result = built.run_build()
    assert result['success'] is False and result['exitCode'] == 137 and len(calls) == 2


def test_import_style_is_fixed_and_rebuilt():
    files = {'src/App.jsx': "import { HomePage } from '@/pages/HomePage'", 'src/pages/HomePage.jsx': 'export default function HomePage(){}'}
    built, calls, written = workspace([(1, ERROR), (0, 'built')], files)
    assert built.run_build()['success'] is True and len(calls) == 2
    assert written == {'src/App.jsx': "import HomePage from '@/pages/HomePage'"}


def test_an_ordinary_build_error_goes_straight_to_repair():
    built, calls, written = workspace([(1, 'Unexpected token')])
    assert built.run_build()['success'] is False and len(calls) == 1 and not written
