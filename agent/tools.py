import inspect
from typing import Any

from .browser import get_browser

import inspect

from .daytona_workspace import (
    get_workspace,
)

print(
    "🔥🔥🔥 TOOLS LOADED FROM:",
    __file__,
)

print(
    "🔥🔥🔥 DAYTONA MODULE FILE:",
    inspect.getfile(get_workspace),
)

from .runner import (
    run_build,
    start_preview,
    stop_preview,
    get_project_diff,
    reset_project,
    workspace_state,
)


# ============================================================
# FILESYSTEM TOOLS
# ============================================================

def list_files(
    project_id: str = "genesys-project",
) -> dict[str, Any]:

    workspace = get_workspace(
        project_id
    )

    print(
        "🔥 ACTIVE WORKSPACE LIST_FILES:",
        workspace.list_files.__func__.__code__.co_firstlineno,
    )

    print(
        "🔥 ACTIVE WORKSPACE CLASS:",
        workspace.__class__,
    )

    return workspace.list_files()


def read_file(
    filename: str,
    project_id: str = "genesys-project",
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, Any]:
    workspace = get_workspace(
        project_id
    )

    if start_line is not None or end_line is not None:
        from .daytona_workspace import safe_remote_path
        start = start_line if start_line is not None else 1
        if start < 1 or (end_line is not None and end_line < start):
            raise ValueError("Line ranges must be positive and end_line must follow start_line.")
        full_content = workspace.sandbox.fs.download_file(safe_remote_path(filename)).decode("utf-8")
        lines = full_content.splitlines(keepends=True)
        end = end_line if end_line is not None else len(lines)
        return {
            "status": "success", "projectId": project_id, "path": filename,
            "content": "".join(lines[start - 1:end]),
            "startLine": start, "endLine": min(end, len(lines)),
            "totalLines": len(lines), "truncated": start > 1 or end < len(lines),
        }

    return workspace.read_file(
        filename
    )


def write_file(
    filename: str,
    content: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    workspace = get_workspace(
        project_id
    )

    from .ai_provider import READ_FILE_MAX_CHARS
    try:
        existing = workspace.read_file(filename)
    except FileNotFoundError:
        existing = None
    if existing and (
        existing.get("truncated")
        or len(existing.get("content", "")) > READ_FILE_MAX_CHARS
    ):
        raise ValueError("Existing file exceeds the complete model read budget. Use edit_file to preserve its unshown content.")

    return workspace.write_file(
        filename,
        content,
    )


def edit_file(filename: str, old_text: str, new_text: str,
              project_id: str = "genesys-project") -> dict[str, Any]:
    """Replace one exact match in the complete remote file."""
    workspace = get_workspace(project_id)
    from .daytona_workspace import safe_remote_path
    content = workspace.sandbox.fs.download_file(safe_remote_path(filename)).decode("utf-8")
    if not old_text or content.count(old_text) != 1:
        raise ValueError("old_text must match exactly once. Supply a unique exact match from the file.")
    return workspace.write_file(filename, content.replace(old_text, new_text, 1))


# ============================================================
# BUILD / PREVIEW TOOLS
# ============================================================

def execute_build(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return run_build(
        project_id=project_id
    )


def execute_start_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return start_preview(
        project_id=project_id
    )


def execute_stop_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return stop_preview(
        project_id=project_id
    )

def execute_get_project_diff(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return get_project_diff(project_id)

def execute_reset_project(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return reset_project(
        project_id=project_id
    )


def execute_rollback_to_checkpoint(
    checkpoint_id: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    workspace = get_workspace(project_id)

    return workspace.rollback_to_checkpoint(
        checkpoint_id
    )


def execute_workspace_state(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return workspace_state(
        project_id=project_id
    )


# ============================================================
# BROWSER TOOLS
# ============================================================

def browser_screenshot(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Capture a screenshot of the currently running Daytona
    preview using the persistent Playwright browser session.
    """

    browser = get_browser(
        project_id
    )

    return browser.screenshot()


def browser_console(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Return console messages captured by the persistent
    Playwright browser session.
    """

    browser = get_browser(
        project_id
    )

    return browser.get_console()


def browser_click(
    selector: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Click an element in the running application using
    a CSS selector.
    """

    browser = get_browser(
        project_id
    )

    return browser.click(
        selector
    )


def browser_type(
    selector: str,
    text: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Fill an input or textarea in the running application
    using a CSS selector.
    """

    browser = get_browser(
        project_id
    )

    return browser.type(
        selector,
        text,
    )


def browser_keypress(
    key: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Press a keyboard key in the currently focused browser
    element.
    """

    browser = get_browser(
        project_id
    )

    return browser.keypress(
        key
    )


# ============================================================
# AI TOOL SCHEMAS
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit an existing file by replacing one exact old_text match. Prefer this to rewriting files, especially for partial file views. Preserves all other content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["filename", "old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Inspect the current project inside its "
                "isolated Daytona workspace. Use this once "
                "before making changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read an existing project file from the "
                "isolated Daytona workspace. For large files, use start_line/end_line to inspect a narrow range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                    "filename": {
                        "type": "string",
                        "description": (
                            "Path relative to the project root, "
                            "for example src/routes/build.tsx."
                        ),
                    },
                },
                "required": [
                    "filename"
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or update a file inside the isolated "
                "Daytona workspace. Write complete file contents. Use edit_file for existing large files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            "Path relative to the project root."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Complete contents of the file."
                        ),
                    },
                },
                "required": [
                    "filename",
                    "content",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_build",
            "description": (
                "Run npm run build inside the current "
                "project's isolated Daytona workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_preview",
            "description": (
                "Start or reuse the Vite development server "
                "inside the current project's isolated Daytona "
                "workspace and return a signed preview URL."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_preview",
            "description": (
                "Stop the Vite preview server for the current "
                "project."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": (
                "Capture a screenshot of the currently running "
                "application preview using Playwright."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_console",
            "description": (
                "Read console messages and page errors captured "
                "from the currently running application preview."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": (
                "Click an element in the currently running "
                "application using a CSS selector."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": (
                            "CSS selector for the element to click, "
                            "for example #start-game or button."
                        ),
                    },
                },
                "required": [
                    "selector"
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": (
                "Fill a text input or textarea in the currently "
                "running application using a specific CSS selector. "
                "Do NOT use the generic selector 'input' because it "
                "may match buttons or other non-editable inputs. "
                "Prefer selectors such as 'input[type=\"text\"]', "
                "'input[placeholder=\"...\"]', '#element-id', "
                "or 'textarea'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": (
                            "CSS selector for the input or "
                            "textarea."
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": (
                            "Text to enter into the field."
                        ),
                    },
                },
                "required": [
                    "selector",
                    "text",
                ],
                "additionalProperties": False,
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "browser_keypress",
            "description": (
                "Press a keyboard key in the currently focused "
                "browser element."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": (
                            "Keyboard key to press, for example "
                            "Enter, Escape, ArrowUp, or Space."
                        ),
                    },
                },
                "required": [
                    "key"
                ],
                "additionalProperties": False,
            },
        },
    },

    # ========================================================
    # M6.5 — PROJECT DIFF
    # ========================================================

    {
        "type": "function",
        "function": {
            "name": "get_project_diff",
            "description": (
                "Return the current Git diff for the project "
                "workspace. Use this to inspect exactly what "
                "source changes were made before completing "
                "a task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": (
                            "Project ID to inspect."
                        ),
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },

        {
        "type": "function",
        "function": {
            "name": "rollback_to_checkpoint",
            "description": (
                "Restore the project workspace to a specific "
                "GeneSys checkpoint. Use this only when an "
                "explicit checkpoint ID is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "checkpoint_id": {
                        "type": "string",
                        "description": (
                            "Exact GeneSys checkpoint ID to restore, "
                            "for example genesys-checkpoint-1234567890."
                        ),
                    },
                },
                "required": [
                    "checkpoint_id"
                ],
                "additionalProperties": False,
            },
        },
    },
]


# ============================================================
# AVAILABLE TOOL IMPLEMENTATIONS
# ============================================================

AVAILABLE_TOOLS = {
    "edit_file": edit_file,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "rollback_to_checkpoint": execute_rollback_to_checkpoint,

    "run_build": execute_build,
    "start_preview": execute_start_preview,
    "stop_preview": execute_stop_preview,

    "browser_screenshot": browser_screenshot,
    "browser_console": browser_console,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_keypress": browser_keypress,

    "get_project_diff": execute_get_project_diff,
}


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool(
    name: str,
    arguments: dict[str, Any],
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Execute one tool for the current project.

    project_id is injected by the orchestrator and does not
    need to be supplied by the model.
    """

    if name not in AVAILABLE_TOOLS:
        raise ValueError(
            f"Unknown tool: {name}"
        )

    function = AVAILABLE_TOOLS[
        name
    ]

    arguments = dict(arguments)

    arguments.pop(
        "project_id",
        None,
    )

    return function(
        project_id=project_id,
        **arguments,
    )
