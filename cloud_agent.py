import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from github import Github
from github import GithubException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

# override=True ensures the .env value is used
load_dotenv(ENV_FILE, override=True)

print("ENV FILE:", ENV_FILE)
print("ENV FILE EXISTS:", os.path.exists(ENV_FILE))
print("GITHUB_TOKEN LOADED:", bool(os.getenv("GITHUB_TOKEN")))

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPO", "Minceks/genesys-core")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

def get_repo():
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is missing. Check the .env file."
        )

    github = Github(GITHUB_TOKEN)
    return github.get_repo(REPO_NAME)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "Genesys Cloud Bridge is Online"
    }), 200


@app.route("/write-file", methods=["POST"])
def write_to_github():
    try:
        # Make sure JSON was supplied
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body must contain JSON."
            }), 400

        filename = data.get("filename")
        code = data.get("code")

        if not filename:
            return jsonify({
                "status": "error",
                "message": "Missing 'filename'."
            }), 400

        if code is None:
            return jsonify({
                "status": "error",
                "message": "Missing 'code'."
            }), 400

        # Clean the incoming path
        path = filename.strip()

        # Remove common project prefixes
        if path.startswith("genesys-pro/"):
            path = path[len("genesys-pro/"):]

        if path.startswith("/"):
            path = path[1:]

        if not path:
            return jsonify({
                "status": "error",
                "message": "Invalid filename."
            }), 400

        repo = get_repo()

        # Check whether the file already exists
        try:
            contents = repo.get_contents(
                path,
                ref=GITHUB_BRANCH
            )

            # Existing file -> update
            repo.update_file(
                path=contents.path,
                message=f"AI Edit: {path}",
                content=code,
                sha=contents.sha,
                branch=GITHUB_BRANCH
            )

            action = "UPDATED"

        except GithubException as e:
            # GitHub returns 404 when the file doesn't exist
            if e.status == 404:
                repo.create_file(
                    path=path,
                    message=f"AI Create: {path}",
                    content=code,
                    branch=GITHUB_BRANCH
                )

                action = "CREATED"

            else:
                raise

        print(f"✅ CLOUD PUSH: {action} {path}")

        return jsonify({
            "status": "success",
            "action": action,
            "file": path
        }), 200

    except Exception as e:
        print(f"❌ CLOUD ERROR: {e}")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )