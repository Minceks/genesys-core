import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from agent.orchestrator import run_agent
from agent.tools import (
    list_files,
    read_file,
    write_file,
)


# =========================================================
# ENVIRONMENT
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env"
    ),
    override=True,
)


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "status":
            "Genesys Cloud Bridge is Online",

        "agent":
            True,
    }), 200


# =========================================================
# PROJECT FILES
# =========================================================

@app.route(
    "/list-files",
    methods=["GET"]
)
def http_list_files():

    try:

        return jsonify(
            list_files()
        ), 200

    except Exception as error:

        return jsonify({
            "status":
                "error",

            "message":
                str(error),
        }), 500


@app.route(
    "/read-file",
    methods=["POST"]
)
def http_read_file():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        result = read_file(
            data.get(
                "filename"
            )
        )

        return jsonify(
            result
        ), 200

    except Exception as error:

        return jsonify({
            "status":
                "error",

            "message":
                str(error),
        }), 500


@app.route(
    "/write-file",
    methods=["POST"]
)
def http_write_file():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        result = write_file(
            data.get(
                "filename"
            ),
            data.get(
                "code"
            ),
        )

        return jsonify(
            result
        ), 200

    except Exception as error:

        return jsonify({
            "status":
                "error",

            "message":
                str(error),
        }), 500


# =========================================================
# AUTONOMOUS AGENT
# =========================================================

@app.route(
    "/agent/run",
    methods=["POST"]
)
def agent_run():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        prompt = (
            data.get(
                "prompt"
            )
            or ""
        ).strip()

        project_id = data.get(
            "projectId"
        )

        if not prompt:

            return jsonify({
                "status":
                    "error",

                "message":
                    "Missing prompt.",
            }), 400

        print(
            "========================================"
        )

        print(
            f"🤖 AGENT REQUEST: {prompt}"
        )

        result = run_agent(
            prompt,
            project_id,
        )

        print(
            f"🤖 AGENT RESULT: "
            f"{result.get('status')}"
        )

        print(
            "========================================"
        )

        return jsonify(
            result
        ), 200

    except Exception as error:

        print(
            f"❌ AGENT ERROR: {error}"
        )

        return jsonify({
            "status":
                "error",

            "message":
                str(error),
        }), 500


# =========================================================
# LOCAL SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print(
        "========================================"
    )

    print(
        "🚀 GeneSys Execution Agent"
    )

    print(
        "📁 Workspace:"
    )

    print(
        BASE_DIR
    )

    print(
        f"🤖 Model: "
        f"openai/gpt-oss-120b"
    )

    print(
        f"🔐 Groq key loaded: "
        f"{bool(os.getenv('GROQ_API_KEY'))}"
    )

    print(
        "========================================"
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )