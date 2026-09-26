import os
import socket
import subprocess
import time
from typing import Any

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BUILD_TIMEOUT_SECONDS = 120

PREVIEW_HOST = "127.0.0.1"
PREVIEW_PORT = 4173

_preview_process: subprocess.Popen | None = None


def run_build() -> dict[str, Any]:
    if os.name == "nt":
        command = ["npm.cmd", "run", "build"]
    else:
        command = ["npm", "run", "build"]

    try:
        process = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=BUILD_TIMEOUT_SECONDS,
            shell=False,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        output = "\n".join(
            part for part in [stdout, stderr]
            if part.strip()
        )

        return {
            "status": "success" if process.returncode == 0 else "error",
            "success": process.returncode == 0,
            "exitCode": process.returncode,
            "output": output[-30000:],
            "projectRoot": PROJECT_ROOT,
        }

    except subprocess.TimeoutExpired as error:
        stdout = (
            error.stdout.decode(
                "utf-8",
                errors="replace",
            )
            if isinstance(error.stdout, bytes)
            else (error.stdout or "")
        )

        stderr = (
            error.stderr.decode(
                "utf-8",
                errors="replace",
            )
            if isinstance(error.stderr, bytes)
            else (error.stderr or "")
        )

        return {
            "status": "error",
            "success": False,
            "exitCode": None,
            "timeout": True,
            "output": (
                stdout
                + "\n"
                + stderr
                + "\nBUILD TIMED OUT."
            )[-30000:],
            "projectRoot": PROJECT_ROOT,
        }

    except Exception as error:
        return {
            "status": "error",
            "success": False,
            "exitCode": None,
            "output": str(error),
            "projectRoot": PROJECT_ROOT,
        }


def _is_port_open(
    host: str,
    port: int,
) -> bool:
    """
    Check whether something is already listening on the port.
    """

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:
        sock.settimeout(0.25)

        try:
            return sock.connect_ex(
                (host, port)
            ) == 0
        except OSError:
            return False


def start_preview() -> dict[str, Any]:
    """
    Start the Vite development server for the local project.

    The server runs independently so the agent request can finish
    while the preview remains available.
    """

    global _preview_process

    preview_url = (
        f"http://{PREVIEW_HOST}:{PREVIEW_PORT}"
    )

    # If our existing process is still alive, reuse it.
    if (
        _preview_process is not None
        and _preview_process.poll() is None
    ):
        return {
            "status": "success",
            "running": True,
            "url": preview_url,
            "pid": _preview_process.pid,
            "message": "Preview server is already running.",
        }

    # If the port is already occupied, don't launch another server.
    if _is_port_open(
        PREVIEW_HOST,
        PREVIEW_PORT,
    ):
        return {
            "status": "success",
            "running": True,
            "url": preview_url,
            "pid": None,
            "message": (
                "Preview port is already in use. "
                "Using the existing server."
            ),
        }

    if os.name == "nt":
        command = [
            "npm.cmd",
            "run",
            "dev",
            "--",
            "--host",
            PREVIEW_HOST,
            "--port",
            str(PREVIEW_PORT),
        ]
    else:
        command = [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            PREVIEW_HOST,
            "--port",
            str(PREVIEW_PORT),
        ]

    try:
        popen_kwargs: dict[str, Any] = {
            "cwd": PROJECT_ROOT,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
        }

        if os.name == "nt":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            popen_kwargs["start_new_session"] = True

        _preview_process = subprocess.Popen(
            command,
            **popen_kwargs,
        )

        # Give Vite a moment to start.
        deadline = time.time() + 10

        while time.time() < deadline:
            if _preview_process.poll() is not None:
                return {
                    "status": "error",
                    "running": False,
                    "url": None,
                    "pid": _preview_process.pid,
                    "message": (
                        "Vite preview process exited "
                        "before the server became ready."
                    ),
                }

            if _is_port_open(
                PREVIEW_HOST,
                PREVIEW_PORT,
            ):
                return {
                    "status": "success",
                    "running": True,
                    "url": preview_url,
                    "pid": _preview_process.pid,
                    "message": "Preview server started.",
                }

            time.sleep(0.25)

        return {
            "status": "error",
            "running": False,
            "url": preview_url,
            "pid": _preview_process.pid,
            "message": (
                "Preview server started but did not "
                "become reachable within 10 seconds."
            ),
        }

    except Exception as error:
        _preview_process = None

        return {
            "status": "error",
            "running": False,
            "url": None,
            "pid": None,
            "message": str(error),
        }


def stop_preview() -> dict[str, Any]:
    """
    Stop the GeneSys-managed local preview server.
    """

    global _preview_process

    if _preview_process is None:
        return {
            "status": "success",
            "running": False,
            "message": "No GeneSys preview server is running.",
        }

    process = _preview_process

    try:
        if process.poll() is None:
            process.terminate()

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        pid = process.pid

        _preview_process = None

        return {
            "status": "success",
            "running": False,
            "pid": pid,
            "message": "Preview server stopped.",
        }

    except Exception as error:
        return {
            "status": "error",
            "running": True,
            "pid": process.pid,
            "message": str(error),
        }