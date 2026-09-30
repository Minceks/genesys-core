import os

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    request,
)
from flask_cors import CORS

from agent.orchestrator import (
    run_agent,
)

from agent.tools import (
    list_files,
    read_file,
    write_file,
)


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
            "origins": "*",
        }
    },
)


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

        print()
        print(
            "========================================"
        )

        print(
            "🤖 AGENT REQUEST: "
            + str(prompt)
        )

        print(
            f"📦 PROJECT: {project_id}"
        )

        print(
            "========================================"
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
        print(
            f"❌ AGENT HTTP ERROR: {error}"
        )

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

    url = str(
        data.get("url", "")
    )

    user_agent = str(
        data.get("userAgent", "")
    )

    timestamp = str(
        data.get("timestamp", "")
    )

    app.logger.warning(
        "[BROWSER:%s] %s | url=%s | userAgent=%s | timestamp=%s",
        level.upper(),
        message,
        url,
        user_agent,
        timestamp,
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