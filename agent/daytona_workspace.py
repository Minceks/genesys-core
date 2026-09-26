import hashlib
import os
import shlex
import time
from pathlib import PurePosixPath
from typing import Any

from daytona import (
    Daytona,
    CreateSandboxFromSnapshotParams,
    SessionExecuteRequest,
)


# ============================================================
# CONFIG
# ============================================================

REPO_URL = (
    "https://github.com/Minceks/genesys-core.git"
)

REMOTE_PROJECT_ROOT = (
    "workspace/genesys-project"
)

PREVIEW_PORT = 4173

PREVIEW_SESSION_ID = (
    "genesys-preview"
)

SANDBOX_AUTO_STOP_MINUTES = 60
SANDBOX_AUTO_DELETE_MINUTES = 1440

MAX_READ_CHARS = 50000
MAX_WRITE_CHARS = 250000


# ============================================================
# DAYTONA CLIENT
# ============================================================

_daytona: Daytona | None = None


def get_daytona() -> Daytona:
    global _daytona

    if _daytona is None:
        if not os.getenv(
            "DAYTONA_API_KEY"
        ):
            raise RuntimeError(
                "DAYTONA_API_KEY is missing from the environment."
            )

        _daytona = Daytona()

    return _daytona


# ============================================================
# PROJECT → SANDBOX NAME
# ============================================================

def sandbox_name_for_project(
    project_id: str,
) -> str:
    """
    Convert a GeneSys project ID into a deterministic,
    safe Daytona sandbox name.

    The same project ID always maps to the same sandbox.
    """

    clean_id = (
        str(project_id).strip()
        or "genesys-project"
    )

    digest = hashlib.sha256(
        clean_id.encode("utf-8")
    ).hexdigest()[:16]

    return (
        f"genesys-project-{digest}"
    )


# ============================================================
# REMOTE PATH SECURITY
# ============================================================

def safe_remote_path(
    filename: str,
) -> str:
    """
    Keep all project paths inside:

        workspace/genesys-project
    """

    if not filename:
        raise ValueError(
            "Filename is required."
        )

    normalized = (
        str(filename)
        .strip()
        .replace("\\", "/")
    )

    while normalized.startswith("/"):
        normalized = normalized[1:]

    # Allow common prefixes without duplicating them.
    if normalized.startswith(
        "workspace/genesys-project/"
    ):
        normalized = normalized[
            len(
                "workspace/genesys-project/"
            ):
        ]

    elif normalized.startswith(
        "genesys-project/"
    ):
        normalized = normalized[
            len(
                "genesys-project/"
            ):
        ]

    path = PurePosixPath(
        normalized
    )

    if path.is_absolute():
        raise ValueError(
            "Absolute paths are not allowed."
        )

    if ".." in path.parts:
        raise ValueError(
            "Parent-directory paths are not allowed."
        )

    if not normalized:
        raise ValueError(
            "Filename is required."
        )

    return (
        f"{REMOTE_PROJECT_ROOT}/{path.as_posix()}"
    )


def relative_remote_path(
    remote_path: str,
) -> str:
    prefix = (
        REMOTE_PROJECT_ROOT + "/"
    )

    if not remote_path.startswith(
        prefix
    ):
        raise ValueError(
            "Path is outside the GeneSys project."
        )

    return remote_path[
        len(prefix):
    ]


# ============================================================
# DAYTONA WORKSPACE
# ============================================================

class DaytonaWorkspace:
    """
    Persistent Daytona-backed workspace for one GeneSys project.
    """

    def __init__(
        self,
        project_id: str,
    ) -> None:

        self.project_id = (
            str(project_id).strip()
            or "genesys-project"
        )

        self.name = (
            sandbox_name_for_project(
                self.project_id
            )
        )

        self.client = get_daytona()

        self.sandbox = (
            self._get_or_create()
        )

    # ========================================================
    # GET OR CREATE SANDBOX
    # ========================================================

    def _get_or_create(self):
        try:
            sandbox = self.client.get(
                self.name
            )

            print(
                "📦 Reusing Daytona sandbox: "
                f"{sandbox.id}"
            )

            try:
                sandbox.refresh_data()
            except Exception:
                pass

            state = str(
                getattr(
                    sandbox,
                    "state",
                    "",
                )
            ).lower()

            if "started" not in state:
                recoverable = bool(
                    getattr(
                        sandbox,
                        "recoverable",
                        False,
                    )
                )

                if (
                    "error" in state
                    and recoverable
                ):
                    print(
                        "🔄 Recovering Daytona sandbox..."
                    )

                    sandbox.recover(
                        timeout=60
                    )

                else:
                    print(
                        f"▶️ Starting sandbox "
                        f"(state={state})..."
                    )

                    sandbox.start(
                        timeout=60
                    )

            return sandbox

        except Exception:
            # If the named sandbox doesn't exist, create it.
            print(
                "🚀 Creating new Daytona sandbox..."
            )

        sandbox = self.client.create(
            CreateSandboxFromSnapshotParams(
                name=self.name,
                language="javascript",
                auto_stop_interval=(
                    SANDBOX_AUTO_STOP_MINUTES
                ),
                auto_delete_interval=(
                    SANDBOX_AUTO_DELETE_MINUTES
                ),
            ),
            timeout=120,
        )

        self._clone_project(
            sandbox
        )

        return sandbox

    # ========================================================
    # CLONE PROJECT
    # ========================================================

    def _clone_project(
        self,
        sandbox,
    ) -> None:

        command = (
            "mkdir -p workspace && "
            f"rm -rf "
            f"{shlex.quote(REMOTE_PROJECT_ROOT)} && "
            f"git clone --depth 1 --branch main "
            f"{shlex.quote(REPO_URL)} "
            f"{shlex.quote(REMOTE_PROJECT_ROOT)}"
        )

        result = sandbox.process.exec(
            command,
            timeout=180,
        )

        if result.exit_code != 0:
            raise RuntimeError(
                "Failed to clone GeneSys repository:\n"
                f"{result.result}"
            )

        install = sandbox.process.exec(
            "npm install",
            cwd=REMOTE_PROJECT_ROOT,
            timeout=300,
        )

        if install.exit_code != 0:
            raise RuntimeError(
                "npm install failed in Daytona sandbox:\n"
                f"{install.result}"
            )

    # ========================================================
    # INFO
    # ========================================================

    def info(
        self,
    ) -> dict[str, Any]:

        return {
            "status": "success",
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "sandboxName": self.sandbox.name,
            "projectRoot": REMOTE_PROJECT_ROOT,
        }

    # ========================================================
    # LIST FILES
    # ========================================================

    def list_files(
        self,
    ) -> dict[str, Any]:

        command = (
            "find "
            f"{shlex.quote(REMOTE_PROJECT_ROOT)} "
            "-type f "
            "-not -path '*/node_modules/*' "
            "-not -path '*/dist/*' "
            "-not -path '*/.git/*' "
            "-not -path '*/.cache/*' "
            "| sort"
        )

        result = self.sandbox.process.exec(
            command,
            timeout=60,
        )

        if result.exit_code != 0:
            raise RuntimeError(
                "Failed to list sandbox files:\n"
                f"{result.result}"
            )

        files: list[str] = []

        for line in (
            result.result or ""
        ).splitlines():

            remote_file = line.strip()

            if not remote_file:
                continue

            try:
                files.append(
                    relative_remote_path(
                        remote_file
                    )
                )
            except ValueError:
                continue

        files.sort()

        files = files[:3000]

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
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "files": files,
            "tree": {
                "routes": routes,
                "components": components,
            },
        }

    # ========================================================
    # READ FILE
    # ========================================================

    def read_file(
        self,
        filename: str,
    ) -> dict[str, Any]:

        remote_path = safe_remote_path(
            filename
        )

        # ----------------------------------------------------
        # Use the filesystem API without passing timeout.
        #
        # This is compatible with the installed SDK that
        # produced your previous error.
        # ----------------------------------------------------

        try:
            content = (
                self.sandbox.fs.download_file(
                    remote_path
                )
            )

        except Exception as error:
            raise FileNotFoundError(
                f"Unable to read {filename}: "
                f"{error}"
            ) from error

        text = content.decode(
            "utf-8",
            errors="replace",
        )

        truncated = False

        if len(text) > MAX_READ_CHARS:
            text = text[
                :MAX_READ_CHARS
            ]
            truncated = True

        return {
            "status": "success",
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "path": relative_remote_path(
                remote_path
            ),
            "content": text,
            "truncated": truncated,
        }

    # ========================================================
    # WRITE FILE
    # ========================================================

    def write_file(
        self,
        filename: str,
        content: str,
    ) -> dict[str, Any]:

        remote_path = safe_remote_path(
            filename
        )

        relative = (
            relative_remote_path(
                remote_path
            )
        )

        basename = (
            PurePosixPath(
                relative
            ).name
        )

        protected_files = {
            ".env",
            ".gitignore",
            "package-lock.json",
            "routeTree.gen.ts",
        }

        if (
            basename in protected_files
            or relative == ".env"
            or relative.startswith(
                ".env."
            )
        ):
            raise ValueError(
                "Protected file cannot be modified: "
                f"{relative}"
            )

        if content is None:
            raise ValueError(
                "File content is required."
            )

        content = str(content)

        if len(content) > MAX_WRITE_CHARS:
            raise ValueError(
                f"File exceeds "
                f"{MAX_WRITE_CHARS} characters."
            )

        # ----------------------------------------------------
        # Check whether the file exists using file metadata.
        # ----------------------------------------------------

        existed = False

        try:
            self.sandbox.fs.get_file_info(
                remote_path
            )

            existed = True

        except Exception:
            existed = False

        # ----------------------------------------------------
        # Create parent directory.
        # ----------------------------------------------------

        parent = str(
            PurePosixPath(
                remote_path
            ).parent
        )

        mkdir_result = (
            self.sandbox.process.exec(
                "mkdir -p "
                + shlex.quote(parent),
                timeout=30,
            )
        )

        if mkdir_result.exit_code != 0:
            raise RuntimeError(
                "Failed to create remote directory:\n"
                f"{mkdir_result.result}"
            )

        # ----------------------------------------------------
        # Upload complete file.
        # ----------------------------------------------------

        try:
            self.sandbox.fs.upload_file(
                content.encode(
                    "utf-8"
                ),
                remote_path,
                timeout=120,
            )

        except Exception as error:
            raise RuntimeError(
                f"Failed to write {relative}: "
                f"{error}"
            ) from error

        return {
            "status": "success",
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "action": (
                "UPDATED"
                if existed
                else "CREATED"
            ),
            "file": relative,
            "bytes": len(
                content.encode(
                    "utf-8"
                )
            ),
        }

    # ========================================================
    # BUILD
    # ========================================================

    def run_build(
        self,
    ) -> dict[str, Any]:

        result = self.sandbox.process.exec(
            "npm run build",
            cwd=REMOTE_PROJECT_ROOT,
            timeout=120,
        )

        output = (
            result.result or ""
        )

        return {
            "status": (
                "success"
                if result.exit_code == 0
                else "error"
            ),
            "success": (
                result.exit_code == 0
            ),
            "exitCode": result.exit_code,
            "output": output[-30000:],
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }

    # ========================================================
    # PREVIEW
    # ========================================================

    def start_preview(
        self,
    ) -> dict[str, Any]:

        # ----------------------------------------------------
        # Make sure sandbox is running.
        # ----------------------------------------------------

        try:
            self.sandbox.refresh_data()
        except Exception:
            pass

        state = str(
            getattr(
                self.sandbox,
                "state",
                "",
            )
        ).lower()

        if "started" not in state:

            recoverable = bool(
                getattr(
                    self.sandbox,
                    "recoverable",
                    False,
                )
            )

            if (
                "error" in state
                and recoverable
            ):
                self.sandbox.recover(
                    timeout=60
                )
            else:
                self.sandbox.start(
                    timeout=60
                )

        # ----------------------------------------------------
        # Check whether Vite is already running.
        # ----------------------------------------------------

        check = self.sandbox.process.exec(
            (
                "curl -I -s "
                "--max-time 2 "
                f"http://127.0.0.1:{PREVIEW_PORT}"
            ),
            timeout=5,
        )

        if check.exit_code != 0:

            # ------------------------------------------------
            # Remove stale preview session.
            # ------------------------------------------------

            try:
                self.sandbox.process.delete_session(
                    PREVIEW_SESSION_ID
                )
            except Exception:
                pass

            # ------------------------------------------------
            # Create fresh session.
            # ------------------------------------------------

            self.sandbox.process.create_session(
                PREVIEW_SESSION_ID
            )

            # ------------------------------------------------
            # Start Vite.
            # ------------------------------------------------

            preview_command = (
                f"cd "
                f"{shlex.quote(REMOTE_PROJECT_ROOT)} "
                "&& npm run dev -- "
                "--host 0.0.0.0 "
                f"--port {PREVIEW_PORT}"
            )

            request = SessionExecuteRequest(
                command=preview_command,
                run_async=True,
            )

            response = (
                self.sandbox.process.execute_session_command(
                    PREVIEW_SESSION_ID,
                    request,
                    timeout=30,
                )
            )

            command_id = getattr(
                response,
                "cmd_id",
                None,
            )

            if command_id:
                print(
                    "🌐 Vite command started: "
                    f"{command_id}"
                )

            # ------------------------------------------------
            # Wait for Vite.
            # ------------------------------------------------

            ready = False

            for attempt in range(30):

                time.sleep(1)

                check = (
                    self.sandbox.process.exec(
                        (
                            "curl -I -s "
                            "--max-time 2 "
                            f"http://127.0.0.1:{PREVIEW_PORT}"
                        ),
                        timeout=5,
                    )
                )

                if check.exit_code == 0:
                    ready = True
                    break

                print(
                    "   waiting for Vite... "
                    f"({attempt + 1}/30)"
                )

            if not ready:
                raise RuntimeError(
                    "Vite preview did not become ready "
                    "inside the Daytona sandbox."
                )

        else:
            print(
                "♻️ Reusing running Vite preview."
            )

        # ----------------------------------------------------
        # Signed external preview.
        # ----------------------------------------------------

        signed = (
            self.sandbox.create_signed_preview_url(
                PREVIEW_PORT,
                expires_in_seconds=3600,
            )
        )

        return {
            "status": "success",
            "running": True,
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "url": signed.url,
            "expiresInSeconds": 3600,
        }

    # ========================================================
    # STOP PREVIEW
    # ========================================================

    def stop_preview(
        self,
    ) -> dict[str, Any]:

        try:
            self.sandbox.process.delete_session(
                PREVIEW_SESSION_ID
            )
        except Exception:
            pass

        return {
            "status": "success",
            "running": False,
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }


# ============================================================
# WORKSPACE CACHE
# ============================================================

_workspaces: dict[
    str,
    DaytonaWorkspace,
] = {}


def get_workspace(
    project_id: str = "genesys-project",
) -> DaytonaWorkspace:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    if key not in _workspaces:
        _workspaces[key] = (
            DaytonaWorkspace(
                key
            )
        )

    return _workspaces[key]