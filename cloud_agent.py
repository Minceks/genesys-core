import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    request,
)
from flask_cors import CORS


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
# BROWSER CONSOLE STORAGE
# ============================================================

MAX_LOGS_PER_PROJECT = 500
browser_logs = defaultdict(list)


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
                "browserConsole": "/browser-console",
                "getBrowserLogs": "/browser-logs",
                "clearBrowserLogs": "/browser-logs/clear",
            },
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
        f"🌐 Server: http://{host}:{port}"
    )

    print()

    app.run(
        host=host,
        port=port,
        debug=False,
    )

# ============================================================
# BROWSER CONSOLE LOGGING
# ============================================================

MAX_BROWSER_LOG_LENGTH = 20000


@app.route(
    "/browser-console",
    methods=["POST", "OPTIONS"],
)
def browser_console():
    """
    Endpoint to receive browser console logs from client-side script.
    
    Expected JSON:
    {
        "level": "error|warn|log|info|debug",
        "message": "log message",
        "url": "page url",
        "userAgent": "browser user agent",
        "timestamp": "ISO timestamp",
        "projectId": "optional project id"
    }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = get_json_body()
    project_id = (
        data.get("projectId")
        or "genesys-project"
    )

    level = str(
        data.get("level", "log")
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

    # Store the log
    log_entry = {
        "level": level,
        "message": message,
        "url": url,
        "userAgent": user_agent,
        "timestamp": timestamp,
        "receivedAt": datetime.utcnow().isoformat(),
    }

    browser_logs[project_id].append(log_entry)

    # Keep only recent logs
    if len(browser_logs[project_id]) > MAX_LOGS_PER_PROJECT:
        browser_logs[project_id] = (
            browser_logs[project_id][-MAX_LOGS_PER_PROJECT:]
        )

    # Log to server console
    app.logger.warning(
        "[BROWSER:%s] %s | url=%s | timestamp=%s",
        level.upper(),
        message,
        url,
        timestamp,
    )

    return jsonify(
        {
            "status": "ok",
            "projectId": project_id,
        }
    )


@app.route(
    "/browser-logs",
    methods=["GET"],
)
def get_browser_logs():
    """
    Get stored browser console logs for a project.
    
    Query params:
    - projectId: optional, defaults to 'genesys-project'
    - limit: optional, number of recent logs to return (default: 50)
    - level: optional, filter by log level (error, warn, log, etc)
    """
    project_id = get_project_id()
    limit = int(
        request.args.get("limit", 50)
    )
    level_filter = (
        request.args.get("level", "").lower()
    )

    logs = browser_logs.get(project_id, [])

    # Filter by level if specified
    if level_filter:
        logs = [
            log for log in logs
            if log["level"] == level_filter
        ]

    # Return recent logs
    recent_logs = logs[-limit:]

    return jsonify(
        {
            "status": "success",
            "projectId": project_id,
            "total": len(logs),
            "returned": len(recent_logs),
            "logs": recent_logs,
        }
    )


@app.route(
    "/browser-logs/clear",
    methods=["POST"],
)
def clear_browser_logs():
    """
    Clear stored browser console logs for a project.
    """
    project_id = get_project_id()

    if project_id in browser_logs:
        del browser_logs[project_id]

    return jsonify(
        {
            "status": "success",
            "projectId": project_id,
            "message": "Logs cleared",
        }
    )

