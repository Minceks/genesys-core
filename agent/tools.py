import os
from pathlib import Path
from typing import Any

from .runner import (
    PROJECT_ROOT,
    run_build,
    start_preview,
    stop_preview,
)


# =========================================================
# LIMITS
# =========================================================

MAX_READ_CHARS = 50000
MAX_WRITE_CHARS = 250000

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    ".cache",
    ".vite",
    "coverage",
    ".venv",
    "venv",
}


# Files that the agent should never modify directly.
PROTECTED_FILES = {
    ".env",
    ".gitignore",
    "package-lock.json",
    "routeTree.gen.ts",
}


# =========================================================
# PATH SAFETY
# =========================================================

def safe_path(filename: str) -> Path:
    if not filename:
        raise ValueError(
            "Filename is required."
        )

    filename = str(filename).strip()

    filename = filename.replace(
        "\\",
        "/",
    )

    while filename.startswith("/"):
        filename = filename[1:]

    if filename.startswith(
        "genesys-pro/"
    ):
        filename = filename[
            len("genesys-pro/"):
        ]

    root = Path(
        PROJECT_ROOT
    ).resolve()

    target = (
        root / filename
    ).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(
            "Invalid path. "
            "The file must stay inside the project."
        )

    return target


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(
        Path(PROJECT_ROOT).resolve()
    ).as_posix()


# =========================================================
# LIST FILES
# =========================================================

def list_files() -> dict[str, Any]:

    root = Path(PROJECT_ROOT)

    files: list[str] = []

    for current_root, dirs, filenames in os.walk(
        root
    ):

        # Prevent traversal into ignored directories.
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRECTORIES
        ]

        current = Path(
            current_root
        )

        for filename in filenames:

            path = current / filename

            try:
                files.append(
                    relative_path(path)
                )
            except ValueError:
                continue

    files.sort()

    routes = [
        path
        for path in files
        if path.startswith(
            "src/routes/"
        )
    ]

    components = [
        path
        for path in files
        if path.startswith(
            "src/components/"
        )
    ]

    return {
        "status": "success",
        "projectRoot": PROJECT_ROOT,
        "files": files[:3000],
        "tree": {
            "routes": routes,
            "components": components,
        },
    }


# =========================================================
# READ FILE
# =========================================================

def read_file(
    filename: str,
) -> dict[str, Any]:

    path = safe_path(
        filename
    )

    if not path.exists():
        raise FileNotFoundError(
            f"File does not exist: {filename}"
        )

    if not path.is_file():
        raise ValueError(
            f"Not a file: {filename}"
        )

    content = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    truncated = False

    if len(content) > MAX_READ_CHARS:
        content = content[
            :MAX_READ_CHARS
        ]
        truncated = True

    return {
        "status": "success",
        "path": relative_path(path),
        "content": content,
        "truncated": truncated,
    }


# =========================================================
# WRITE FILE
# =========================================================

def write_file(
    filename: str,
    content: str,
) -> dict[str, Any]:

    path = safe_path(
        filename
    )

    relative = relative_path(
        path
    )

    # Never allow agent to modify secrets.
    basename = path.name

    if (
        basename in PROTECTED_FILES
        or relative == ".env"
        or relative.startswith(".env.")
    ):
        raise ValueError(
            f"Protected file cannot be modified by the agent: "
            f"{relative}"
        )

    if content is None:
        raise ValueError(
            "File content is required."
        )

    content = str(content)

    if len(content) > MAX_WRITE_CHARS:
        raise ValueError(
            f"File exceeds {MAX_WRITE_CHARS} characters."
        )

    existed = path.exists()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    return {
        "status": "success",
        "action": "UPDATED"
        if existed
        else "CREATED",
        "file": relative,
        "bytes": len(
            content.encode("utf-8")
        ),
    }


# =========================================================
# BUILD
# =========================================================

def execute_build() -> dict[str, Any]:
    return run_build()


def execute_start_preview() -> dict[str, Any]:
    return start_preview()


def execute_stop_preview() -> dict[str, Any]:
    return stop_preview()

# =========================================================
# TOOL DEFINITIONS FOR GROQ
# =========================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Inspect the local GeneSys project and list its files. "
                "Use this before changing the project."
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
            "Start the local Vite development server so the "
            "user can interact with the current application."
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
            "Stop the GeneSys-managed local Vite preview server."
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
                "Read an existing project file. "
                "Use this before changing an existing file."
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
                "required": ["filename"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or update a project file in the local "
                "workspace. Write the complete file contents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            "Path relative to project root."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Complete file contents."
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
                "Run the project's production build using "
                "npm run build. Use this after code changes "
                "to detect TypeScript, Vite, and compilation errors."
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


# =========================================================
# TOOL DISPATCH
# =========================================================

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
) -> dict[str, Any]:

    if name not in AVAILABLE_TOOLS:
        raise ValueError(
            f"Unknown tool: {name}"
        )

    function = AVAILABLE_TOOLS[
        name
    ]

    return function(
        **arguments
    )