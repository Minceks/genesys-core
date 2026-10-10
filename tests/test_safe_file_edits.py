import json
from types import SimpleNamespace

import pytest

from agent import tools
from agent.ai_provider import READ_FILE_MAX_CHARS, compact_tool_result
from agent.daytona_workspace import DaytonaWorkspace


def test_compacted_read_is_marked_partial():
    result = json.loads(compact_tool_result(json.dumps({
        "path": "src/Hero.tsx", "content": "a" * (READ_FILE_MAX_CHARS + 1),
        "truncated": False,
    })))
    assert result["truncated"] is True
    assert "edit_file" in result["editInstruction"]


def test_placeholder_write_is_rejected_before_remote_io():
    workspace = DaytonaWorkspace.__new__(DaytonaWorkspace)
    with pytest.raises(ValueError, match="Compacted context"):
        workspace.write_file("src/Hero.tsx", "[... GeneSys context compacted ...]")


@pytest.mark.parametrize("content", [
    'import Page from "../recovered/src/routes/expenses";',
    'export { default } from "../recovered/src/routes/expenses";',
    'const Page = import("../recovered/src/routes/expenses");',
    'const Page = require("../recovered/src/routes/expenses");',
])
def test_recovered_import_is_rejected_before_remote_io(content):
    workspace = DaytonaWorkspace.__new__(DaytonaWorkspace)
    workspace.project_id = "568fece4-42cc-47be-9778-9ca6b7b120b4"
    with pytest.raises(ValueError, match="reference-only backup"):
        workspace.write_file("src/App.jsx", content)


def test_large_full_rewrite_is_rejected(monkeypatch):
    workspace = SimpleNamespace(read_file=lambda _: {
        "content": "a" * (READ_FILE_MAX_CHARS + 1), "truncated": False,
    })
    monkeypatch.setattr(tools, "get_workspace", lambda _: workspace)
    with pytest.raises(ValueError, match="Use edit_file"):
        tools.write_file("src/Hero.tsx", "shortened content")


def test_exact_edit_preserves_unshown_content(monkeypatch):
    original = "a" * 40000 + "unique heading" + "z" * 40000
    written = []
    workspace = SimpleNamespace(
        sandbox=SimpleNamespace(fs=SimpleNamespace(download_file=lambda _: original.encode())),
        write_file=lambda filename, content: written.append((filename, content)) or {"status": "success"},
    )
    monkeypatch.setattr(tools, "get_workspace", lambda _: workspace)
    assert tools.edit_file("src/Hero.tsx", "unique heading", "new heading")["status"] == "success"
    assert written == [("src/Hero.tsx", "a" * 40000 + "new heading" + "z" * 40000)]


def test_line_range_can_reach_content_beyond_default_read_budget(monkeypatch):
    original = "prefix\n" * 10000 + "requested middle\n" + "suffix\n" * 10000
    workspace = SimpleNamespace(sandbox=SimpleNamespace(fs=SimpleNamespace(
        download_file=lambda _: original.encode(),
    )))
    monkeypatch.setattr(tools, "get_workspace", lambda _: workspace)
    result = tools.read_file("src/Hero.tsx", start_line=10001, end_line=10001)
    assert result["content"] == "requested middle\n"
    assert result["truncated"] is True
    assert result["totalLines"] == 20001


@pytest.mark.parametrize("old_text", ["", "missing", "repeated"])
def test_ambiguous_edit_does_not_write(monkeypatch, old_text):
    workspace = SimpleNamespace(sandbox=SimpleNamespace(fs=SimpleNamespace(
        download_file=lambda _: b"repeated repeated",
    )))
    monkeypatch.setattr(tools, "get_workspace", lambda _: workspace)
    with pytest.raises(ValueError, match="exactly once"):
        tools.edit_file("src/Hero.tsx", old_text, "replacement")
