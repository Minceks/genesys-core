from typing import Any

from .daytona_workspace import get_workspace
from .runner import (
    run_build,
    start_preview,
    stop_preview,
)


# ============================================================
# LIST FILES
# ============================================================

def list_files(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    workspace = get_workspace(
        project_id
    )

    return workspace.list_files()


# ============================================================
# READ FILE
# ============================================================

def read_file(
    filename: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    workspace = get_workspace(
        project_id
    )

    return workspace.read_file(
        filename
    )


# ============================================================
# WRITE FILE
# ============================================================

def write_file(
    filename: str,
    content: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    workspace = get_workspace(
        project_id
    )

    return workspace.write_file(
        filename,
        content,
    )


# ============================================================
# BUILD
# ============================================================

def execute_build(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return run_build(
        project_id=project_id
    )


# ============================================================
# START PREVIEW
# ============================================================

def execute_start_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return start_preview(
        project_id=project_id
    )


# ============================================================
# STOP PREVIEW
# ============================================================

def execute_stop_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    return stop_preview(
        project_id=project_id
    )


# ============================================================
# GROQ TOOLS
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Inspect the current project inside its isolated "
                "Daytona workspace. Use this once before making changes."
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
                "Read an existing project file from the isolated "
                "Daytona workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            "Path relative to the project root, "
                            "for example src/routes/build.tsx."
                        ),
                    }
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
                "Daytona workspace. Write complete file contents."
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
                "Run npm run build inside the current project's "
                "isolated Daytona workspace."
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
                "Start or reuse the Vite development server inside "
                "the current project's isolated Daytona workspace "
                "and return a signed preview URL."
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
                "Stop the Vite preview server for the current project."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


# ============================================================
# TOOL DISPATCH
# ============================================================

AVAILABLE_TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_build": execute_build,
    "start_preview": execute_start_preview,
    "stop_preview": execute_stop_preview,
}


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Execute one Daytona-backed tool for the current project.

    project_id is injected by the orchestrator and does not need
    to be supplied by the model.
    """

    if name not in AVAILABLE_TOOLS:
        raise ValueError(
            f"Unknown tool: {name}"
        )

    function = AVAILABLE_TOOLS[
        name
    ]

    return function(
        project_id=project_id,
        **arguments,
    )