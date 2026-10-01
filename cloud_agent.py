import logging
import hmac
import os
import time
import uuid

from dotenv import load_dotenv
from flask import (
    Flask,
    g,
    jsonify,
    request,
)
from flask_cors import CORS
from agent.logging_config import configure_logging, request_id_context
from agent.config import load_settings
from agent.orchestrator import run_agent
from agent.tools import list_files, read_file, write_file


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)

configure_logging()

settings = load_settings()

logger = logging.getLogger(__name__)


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__
)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                origin.strip()
                for origin in settings.cors_origins.split(",")
                if origin.strip()
            ],
            "allow_headers": [
                "Content-Type",
                "X-API-Key",
            ],
        }
    },
)


@app.before_request
def begin_request_logging():
    g.request_started_at = time.perf_counter()
    g.request_id_token = request_id_context.set(uuid.uuid4().hex)


@app.before_request
def require_api_key():
    if request.method == "OPTIONS" or request.path.rstrip("/") in {
        "/health",
        "/api/v1/health",
    }:
        return None

    expected_key = str(getattr(settings, "api_key", "") or "").strip()
    if not expected_key:
        logger.error("api_auth_not_configured")
        return jsonify(
            {
                "status": "error",
                "code": "API_AUTH_NOT_CONFIGURED",
                "message": "API authentication is not configured.",
                "requestId": request_id_context.get(),
            }
        ), 503

    supplied_key = request.headers.get("X-API-Key", "")
    keys_match = hmac.compare_digest(
        supplied_key.encode("utf-8"),
        expected_key.encode("utf-8"),
    )
    if not supplied_key or not keys_match:
        logger.warning(
            "api_request_rejected method=%s path=%s",
            request.method,
            request.path,
        )
        return jsonify(
            {
                "status": "error",
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key.",
                "requestId": request_id_context.get(),
            }
        ), 401

    return None


@app.after_request
def finish_request_logging(response):
    request_id = request_id_context.get()
    started_at = g.get("request_started_at", time.perf_counter())
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.path,
        response.status_code,
        duration_ms,
    )
    token = g.pop("request_id_token", None)
    if token is not None:
        request_id_context.reset(token)
    return response


# ============================================================
# HELPERS
# ============================================================

def get_project_id() -> str:
    """
    Accept projectId from:
    - JSON body
    - query string

    Defaults to the first GeneSys project.
    """

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    project_id = (
        data.get("projectId")
        or request.args.get(
            "projectId"
        )
        or "genesys-project"
    )

    return (
        str(project_id).strip()
        or "genesys-project"
    )


def get_json_body() -> dict:
    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    return data


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():
    return jsonify(
        {
            "status": (
                "Genesys Cloud Bridge is Online"
            ),
            "agent": True,
            "daytona": bool(
                os.getenv(
                    "DAYTONA_API_KEY"
                )
            ),
            "groq": bool(
                os.getenv(
                    "GROQ_API_KEY"
                )
            ),
        }
    )


# ============================================================
# LIST FILES
# ============================================================

@app.route(
    "/list-files",
    methods=["GET"],
)
def files():
    try:
        project_id = get_project_id()

        result = list_files(
            project_id=project_id
        )

        return jsonify(
            result
        )

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# READ FILE
# ============================================================

@app.route(
    "/read-file",
    methods=["GET", "POST"],
)
def read():
    try:
        data = get_json_body()

        filename = (
            data.get("filename")
            or request.args.get(
                "filename"
            )
        )

        if not filename:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "filename is required."
                    ),
                }
            ), 400

        project_id = (
            data.get("projectId")
            or request.args.get(
                "projectId"
            )
            or "genesys-project"
        )

        result = read_file(
            filename=str(
                filename
            ),
            project_id=str(
                project_id
            ),
        )

        return jsonify(
            result
        )

    except FileNotFoundError as error:
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 404

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# WRITE FILE
# ============================================================

@app.route(
    "/write-file",
    methods=["POST"],
)
def write():
    try:
        data = get_json_body()

        filename = data.get(
            "filename"
        )

        content = data.get(
            "content"
        )

        if not filename:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "filename is required."
                    ),
                }
            ), 400

        if content is None:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "content is required."
                    ),
                }
            ), 400

        project_id = (
            data.get(
                "projectId"
            )
            or "genesys-project"
        )

        result = write_file(
            filename=str(
                filename
            ),
            content=str(
                content
            ),
            project_id=str(
                project_id
            ),
        )

        return jsonify(
            result
        )

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# AGENT RUN
# ============================================================

@app.route(
    "/agent/run",
    methods=["POST"],
)
def agent_run():
    try:
        data = get_json_body()

        prompt = data.get(
            "prompt"
        )

        if not prompt or not str(
            prompt
        ).strip():
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "prompt is required."
                    ),
                }
            ), 400

        project_id = (
            data.get(
                "projectId"
            )
            or "genesys-project"
        )

        project_id = (
            str(project_id).strip()
            or "genesys-project"
        )

        logger.info(
            "agent_run_started project_id=%s",
            project_id,
        )

        result = run_agent(
            prompt=str(
                prompt
            ),
            project_id=project_id,
        )

        return jsonify(
            result
        )

    except Exception as error:
        logger.exception("agent_run_failed")

        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# ROOT
# ============================================================

@app.route(
    "/",
    methods=["GET"],
)
def root():
    return jsonify(
        {
            "name": "GeneSys Cloud Agent",
            "status": "online",
            "endpoints": {
                "health": "/health",
                "listFiles": "/list-files",
                "readFile": "/read-file",
                "writeFile": "/write-file",
                "agentRun": "/agent/run",
            },
        }
    )


# ============================================================
# BROWSER CONSOLE
# ============================================================

MAX_BROWSER_LOG_LENGTH = 20000


@app.route(
    "/browser-console",
    methods=["POST", "OPTIONS"],
)
def browser_console():
    if request.method == "OPTIONS":
        return ("", 204)

    data = get_json_body()

    level = str(
        data.get("level", "error")
    ).lower()

    message = str(
        data.get("message", "")
    )

    if len(message) > MAX_BROWSER_LOG_LENGTH:
        message = (
            message[:MAX_BROWSER_LOG_LENGTH]
            + "..."
        )

    logger.info(
        "browser_console_event level=%s message_length=%s",
        level.upper(),
        len(message),
    )

    return jsonify(
        {
            "status": "ok",
        }
    )

# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":
    host = os.getenv(
        "HOST",
        "127.0.0.1",
    )

    port = int(
        os.getenv(
            "PORT",
            "5000",
        )
    )

    print()
    print(
        "🚀 GeneSys Execution Agent"
    )

    print(
        f"📁 PROJECT ROOT: {PROJECT_ROOT}"
    )

    print(
        "🤖 MODEL: "
        + os.getenv(
            "GENESYS_MODEL",
            "openai/gpt-oss-120b",
        )
    )

    print(
        "🔑 GROQ KEY LOADED: "
        + str(
            bool(
                os.getenv(
                    "GROQ_API_KEY"
                )
            )
        )
    )

    print(
        "🔑 DAYTONA KEY LOADED: "
        + str(
            bool(
                os.getenv(
                    "DAYTONA_API_KEY"
                )
            )
        )
    )

    print(
        f"🌐 Server: http://{host}:{port}"
    )

    print()

    app.run(
        host=host,
        port=port,
        debug=False,
    )
