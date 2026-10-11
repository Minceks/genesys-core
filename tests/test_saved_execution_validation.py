"""Exercise the production validator without initializing provider/workspace SDKs."""
import ast
from pathlib import Path
from typing import Any


def validator():
    source = Path(__file__).parents[1] / 'agent' / 'orchestrator.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == '_validate_execution')
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {'Any': Any}
    exec(compile(module, str(source), 'exec'), namespace)
    return namespace['_validate_execution']


def test_saved_build_can_be_verified_without_new_edits():
    result = validator()({'targetedFiles': ['src/App.jsx']}, [], allow_no_changes=True)
    assert result['valid']
    assert result['modifiedFiles'] == []


def test_normal_implementation_still_requires_changes():
    result = validator()({'targetedFiles': ['src/App.jsx']}, [])
    assert not result['valid']
    assert 'No project files were modified.' in result['issues']


def test_retry_does_not_bypass_protected_file_validation():
    result = validator()({'targetedFiles': ['src/routeTree.gen.ts']},
                         ['src/routeTree.gen.ts'], allow_no_changes=True)
    assert not result['valid']
    assert result['protectedFiles'] == ['src/routeTree.gen.ts']
