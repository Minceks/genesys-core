import hashlib
import importlib
import logging
import shlex
from pathlib import PurePosixPath

from daytona import (
    CreateSandboxFromSnapshotParams,
    Daytona,
    SessionExecuteRequest,
)

from .config import load_settings

logger = logging.getLogger(__name__)

try:
    daytona = importlib.import_module("daytona")
    DAYTONA_AVAILABLE = True
except ModuleNotFoundError:
    daytona = None
    DAYTONA_AVAILABLE = False
    logger.warning(
        "Daytona SDK is not installed. Daytona workspace features are disabled."
    )


# ============================================================
# CONFIG
# ============================================================

settings = load_settings()

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
        if not settings.daytona_api_key:
            raise RuntimeError(
                "DAYTONA_API_KEY is missing from configuration."
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
    # ENSURE SANDBOX IS RUNNING
    # ========================================================

    def _ensure_sandbox_running(
        self,
    ) -> None:

        print(
            "🔥 ENSURE SANDBOX RUNNING CALLED"
        )

        self.sandbox = self.client.get(
            self.name
        )

        self.sandbox.refresh_data()

        state = str(
            getattr(
                self.sandbox,
                "state",
                "",
            )
        ).lower()

        print(
            "🔎 DAYTONA SANDBOX STATE:",
            state,
        )

        print(
            "🔎 DAYTONA SANDBOX ID:",
            self.sandbox.id,
        )

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
                print(
                    "🔄 RECOVERING DAYTONA SANDBOX..."
                )

                self.sandbox.recover(
                    timeout=60
                )

            else:
                print(
                    "▶️ STARTING DAYTONA SANDBOX..."
                )

                self.sandbox.start(
                    timeout=60
                )

        # Verify the lifecycle operation actually completed.
        self.sandbox.refresh_data()

        final_state = str(
            getattr(
                self.sandbox,
                "state",
                "",
            )
        ).lower()

        print(
            "🔎 DAYTONA FINAL SANDBOX STATE:",
            final_state,
        )

        if "started" not in final_state:
            raise RuntimeError(
                "Daytona sandbox failed to start. "
                f"Final state: {final_state}"
            )

        print(
            "✅ DAYTONA SANDBOX CONFIRMED RUNNING"
        )

# ========================================================
# GET OR CREATE SANDBOX
# ========================================================

    def _get_or_create(self):

        print(
            "🔎 GETTING DAYTONA SANDBOX:",
            self.name,
            flush=True,
        )

        try:
            sandbox = self.client.get(
                self.name
            )

            print(
                "📦 DAYTONA SANDBOX FOUND:",
                sandbox.id,
                flush=True,
            )

            try:
                sandbox.refresh_data()
            except Exception as error:
                print(
                    "⚠️ SANDBOX REFRESH FAILED:",
                    repr(error),
                    flush=True,
                )

            state = str(
                getattr(
                    sandbox,
                    "state",
                    "",
                )
            ).lower()

            print(
                "🔎 DAYTONA SANDBOX STATE:",
                state,
                flush=True,
            )

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
                        "🔄 RECOVERING DAYTONA SANDBOX:",
                        sandbox.id,
                        flush=True,
                    )

                    sandbox.recover(
                        timeout=60
                    )

                else:
                    print(
                        "▶️ STARTING DAYTONA SANDBOX:",
                        sandbox.id,
                        flush=True,
                    )

                    sandbox.start(
                        timeout=60
                    )

                sandbox.refresh_data()

            final_state = str(
                getattr(
                    sandbox,
                    "state",
                    "",
                )
            ).lower()

            print(
                "🔎 FINAL DAYTONA SANDBOX STATE:",
                final_state,
                flush=True,
            )

            if "started" not in final_state:
                raise RuntimeError(
                    "Daytona sandbox did not start. "
                    f"Final state: {final_state}"
                )

            print(
                "✅ DAYTONA SANDBOX READY:",
                sandbox.id,
                flush=True,
            )

            return sandbox

        except Exception as error:

            print(
                "ℹ️ DAYTONA GET FAILED — CREATING SANDBOX:",
                repr(error),
                flush=True,
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

            print(
                "📦 DAYTONA SANDBOX CREATED:",
                sandbox.id,
                flush=True,
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

            print(
                "🔎 NEW SANDBOX STATE:",
                state,
                flush=True,
            )

            if "started" not in state:

                print(
                    "▶️ STARTING NEW DAYTONA SANDBOX:",
                    sandbox.id,
                    flush=True,
                )

                sandbox.start(
                    timeout=60
                )

                sandbox.refresh_data()

            final_state = str(
                getattr(
                    sandbox,
                    "state",
                    "",
                )
            ).lower()

            print(
                "🔎 NEW SANDBOX FINAL STATE:",
                final_state,
                flush=True,
            )

            if "started" not in final_state:
                raise RuntimeError(
                    "New Daytona sandbox did not start. "
                    f"Final state: {final_state}"
                )

            print(
                "✅ NEW DAYTONA SANDBOX READY:",
                sandbox.id,
                flush=True,
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

        print(
            "🔥 CLONE PROJECT: ensuring sandbox is running"
        )

        try:
            sandbox.refresh_data()
        except Exception as error:
            print(
                "⚠️ CLONE PROJECT REFRESH FAILED:",
                repr(error),
            )

        state = str(
            getattr(
                sandbox,
                "state",
                "",
            )
        ).lower()

        print(
            "🔎 CLONE PROJECT SANDBOX STATE:",
            state,
        )

        if "started" not in state:

            print(
                "▶️ CLONE PROJECT: starting sandbox"
            )

            sandbox.start(
                timeout=60
            )

            sandbox.refresh_data()

        final_state = str(
            getattr(
                sandbox,
                "state",
                "",
            )
        ).lower()

        print(
            "🔎 CLONE PROJECT FINAL STATE:",
            final_state,
        )

        if "started" not in final_state:
            raise RuntimeError(
                "Daytona sandbox is not running "
                "after creation/start. "
                f"State: {final_state}"
            )

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

        clone_output = result.result or ""

        if result.exit_code != 0:
            raise RuntimeError(
                "Failed to clone GeneSys project:\n"
                f"{clone_output[-12000:]}"
            )

        install_result = sandbox.process.exec(
            "npm ci",
            cwd=REMOTE_PROJECT_ROOT,
            timeout=300,
        )

        install_output = (
            install_result.result or ""
        )

        if install_result.exit_code != 0:
            raise RuntimeError(
                "Failed to install project dependencies:\n"
                f"{install_output[-12000:]}"
            )
    # ========================================================
    # INFO
    # ========================================================

    def state(
        self,
    ) -> dict[str, Any]:
        """
        Return the current lifecycle state of the workspace.
        """

        try:
            self.sandbox.refresh_data()
        except Exception:
            pass

        raw_state = str(
            getattr(
                self.sandbox,
                "state",
                "",
            )
        ).lower()

        if "started" in raw_state:
            status = "running"
        elif "stopped" in raw_state:
            status = "stopped"
        elif "error" in raw_state:
            status = "error"
        else:
            status = raw_state or "unknown"

        return {
            "status": "success",
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "sandboxName": self.sandbox.name,
            "state": status,
            "rawState": raw_state,
            "recoverable": bool(
                getattr(
                    self.sandbox,
                    "recoverable",
                    False,
                )
            ),
            "projectRoot": REMOTE_PROJECT_ROOT,
        }

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

        self._ensure_sandbox_running()

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
    # M6.5 — PROJECT DIFF
    # ========================================================

    def get_diff(
        self,
    ) -> dict[str, Any]:
        result = self.sandbox.process.exec(
            "git diff -- . ':!package-lock.json'",
            cwd=REMOTE_PROJECT_ROOT,
            timeout=60,
        )

        output = result.result or ""

        if result.exit_code != 0:
            return {
                "status": "error",
                "success": False,
                "exitCode": result.exit_code,
                "output": output[-30000:],
                "projectId": self.project_id,
                "sandboxId": self.sandbox.id,
            }

        return {
            "status": "success",
            "success": True,
            "exitCode": 0,
            "diff": output[-50000:],
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }

    # ========================================================
    # RESET PROJECT
    # ========================================================

    def reset_project(
        self,
    ) -> dict[str, Any]:
        """
        Reset the project working tree to origin/main.

        The Daytona sandbox itself is preserved.
        Environment files are preserved.
        """

        command = (
            "git fetch origin main && "
            "git reset --hard origin/main && "
            "git clean -fd "
            "-e '.env' "
            "-e '.env.*'"
        )

        result = self.sandbox.process.exec(
            command,
            cwd=REMOTE_PROJECT_ROOT,
            timeout=120,
        )

        output = result.result or ""

        if result.exit_code != 0:
            return {
                "status": "error",
                "success": False,
                "exitCode": result.exit_code,
                "output": output[-30000:],
                "projectId": self.project_id,
                "sandboxId": self.sandbox.id,
            }

        return {
            "status": "success",
            "success": True,
            "exitCode": 0,
            "output": output[-30000:],
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
            "resetTo": "origin/main",
        }

    # ========================================================
    # M8 — VERSIONING / RECOVERY
    # ========================================================

    def create_checkpoint(
        self,
        description: str = "",
    ) -> dict[str, Any]:

        checkpoint_id = (
            f"genesys-checkpoint-{int(time.time())}"
        )

        safe_description = (
            description.strip()
            or "GeneSys autonomous checkpoint"
        )

        commands = [
            (
                "git config user.name "
                "'GeneSys Agent'"
            ),
            (
                "git config user.email "
                "'genesys@localhost'"
            ),
            "git add -A",
            (
                "git commit --allow-empty "
                f"-m {shlex.quote(safe_description)}"
            ),
        ]

        for command in commands:

            result = self.sandbox.process.exec(
                command,
                cwd=REMOTE_PROJECT_ROOT,
                timeout=120,
            )

            output = result.result or ""

            if result.exit_code != 0:
                return {
                    "status": "error",
                    "success": False,
                    "exitCode": result.exit_code,
                    "output": output[-30000:],
                    "projectId": self.project_id,
                    "sandboxId": self.sandbox.id,
                }

        tag_result = self.sandbox.process.exec(
            (
                "git tag -f "
                f"{shlex.quote(checkpoint_id)}"
            ),
            cwd=REMOTE_PROJECT_ROOT,
            timeout=30,
        )

        tag_output = tag_result.result or ""

        if tag_result.exit_code != 0:
            return {
                "status": "error",
                "success": False,
                "exitCode": tag_result.exit_code,
                "output": tag_output[-30000:],
                "projectId": self.project_id,
                "sandboxId": self.sandbox.id,
            }

        commit_result = self.sandbox.process.exec(
            "git rev-parse HEAD",
            cwd=REMOTE_PROJECT_ROOT,
            timeout=30,
        )

        commit_hash = (
            (commit_result.result or "")
            .strip()
        )

        return {
            "status": "success",
            "success": True,
            "checkpointId": checkpoint_id,
            "commit": commit_hash,
            "description": safe_description,
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }

    def list_checkpoints(
        self,
    ) -> dict[str, Any]:

        result = self.sandbox.process.exec(
            (
                "git tag --list "
                "'genesys-checkpoint-*' "
                "--sort=-creatordate"
            ),
            cwd=REMOTE_PROJECT_ROOT,
            timeout=10,
        )

        output = result.result or ""

        if result.exit_code != 0:
            return {
                "status": "error",
                "success": False,
                "exitCode": result.exit_code,
                "output": output[-30000:],
                "projectId": self.project_id,
                "sandboxId": self.sandbox.id,
            }

        checkpoints = [
            tag.strip()
            for tag in output.splitlines()
            if tag.strip()
        ]

        return {
            "status": "success",
            "success": True,
            "checkpoints": checkpoints,
            "count": len(checkpoints),
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }

    def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:

        if not checkpoint_id:
            return {
                "status": "error",
                "success": False,
                "message": (
                    "checkpoint_id is required."
                ),
            }

        command = (
            "git reset --hard "
            f"{shlex.quote(checkpoint_id)} && "
            "git clean -fd "
            "-e '.env' "
            "-e '.env.*'"
        )

        result = self.sandbox.process.exec(
            command,
            cwd=REMOTE_PROJECT_ROOT,
            timeout=120,
        )

        output = result.result or ""

        if result.exit_code != 0:
            return {
                "status": "error",
                "success": False,
                "exitCode": result.exit_code,
                "output": output[-30000:],
                "projectId": self.project_id,
                "sandboxId": self.sandbox.id,
            }

        return {
            "status": "success",
            "success": True,
            "checkpointId": checkpoint_id,
            "output": output[-30000:],
            "projectId": self.project_id,
            "sandboxId": self.sandbox.id,
        }
        
    # ========================================================
    # BUILD
    # ========================================================

    def run_build(
        self,
    ) -> dict[str, Any]:

        # Reused sandboxes may have lost node_modules. Install locked
        # dependencies only when Vite is missing, then capture install and
        # build errors together for logs and self-repair.
        result = self.sandbox.process.exec(
            (
                "if [ ! -x node_modules/.bin/vite ]; then "
                "echo 'Vite is missing; installing locked dependencies'; "
                "npm ci || exit $?; "
                "fi; "
                "npm run build 2>&1"
            ),
            cwd=REMOTE_PROJECT_ROOT,
            timeout=300,
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

print("🔧 Daytona workspace module loaded")

def get_workspace(
    project_id: str = "genesys-project",
) -> DaytonaWorkspace:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    print(
        "🔧 GET WORKSPACE:",
        key,
    )

    if key not in _workspaces:
        print(
            "🆕 CREATING WORKSPACE OBJECT:",
            key,
        )

        _workspaces[key] = (
            DaytonaWorkspace(
                key
            )
        )

    else:
        print(
            "♻️ REUSING WORKSPACE OBJECT:",
            key,
        )

    return _workspaces[key]
