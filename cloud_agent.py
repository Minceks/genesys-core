import os

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from github import Github
from github import GithubException

load_dotenv()

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv(
    "GITHUB_REPO",
    "Minceks/genesys-core"
)
GITHUB_BRANCH = os.getenv(
    "GITHUB_BRANCH",
    "main"
)


def get_repo():
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is missing. Configure it in Railway Variables."
        )

    github = Github(GITHUB_TOKEN)

    return github.get_repo(REPO_NAME)


def clean_path(filename):
    if not filename:
        raise ValueError("Filename is required.")

    path = filename.strip().replace("\\", "/")

    while path.startswith("/"):
        path = path[1:]

    if path.startswith("genesys-pro/"):
        path = path[len("genesys-pro/"):]

    parts = path.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid file path.")

    return "/".join(parts)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "Genesys Cloud Bridge is Online"
    }), 200


@app.route("/list-files", methods=["GET"])
def list_files():
    try:
        repo = get_repo()

        routes = []
        components = []

        def walk(path=""):
            items = repo.get_contents(
                path,
                ref=GITHUB_BRANCH
            )

            for item in items:
                if item.type == "dir":
                    # Don't walk huge dependency/build folders.
                    if item.name in {
                        "node_modules",
                        "dist",
                        ".git"
                    }:
                        continue

                    yield from walk(item.path)

                elif item.type == "file":
                    yield item.path

        files = list(walk())

        for path in files:
            if path.startswith("src/routes/"):
                routes.append(path)

            elif path.startswith("src/components/"):
                components.append(path)

        return jsonify({
            "status": "success",
            "tree": {
                "routes": sorted(routes),
                "components": sorted(components)
            }
        }), 200

    except Exception as e:
        print(f"❌ LIST ERROR: {e}")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/read-file", methods=["POST"])
def read_file():
    try:
        data = request.get_json(silent=True) or {}

        path = clean_path(
            data.get("filename")
        )

        repo = get_repo()

        contents = repo.get_contents(
            path,
            ref=GITHUB_BRANCH
        )

        if isinstance(contents, list):
            return jsonify({
                "status": "error",
                "message": "Path is a directory, not a file."
            }), 400

        content = contents.decoded_content.decode(
            "utf-8",
            errors="replace"
        )

        return jsonify({
            "status": "success",
            "filename": path,
            "content": content
        }), 200

    except GithubException as e:
        status = getattr(e, "status", 500)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), status

    except Exception as e:
        print(f"❌ READ ERROR: {e}")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/write-file", methods=["POST"])
def write_to_github():
    try:
        data = request.get_json(silent=True) or {}

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

        path = clean_path(filename)

        repo = get_repo()

        # Existing file
        try:
            contents = repo.get_contents(
                path,
                ref=GITHUB_BRANCH
            )

            if isinstance(contents, list):
                raise RuntimeError(
                    f"{path} is a directory."
                )

            repo.update_file(
                path=contents.path,
                message=f"AI Edit: {path}",
                content=code,
                sha=contents.sha,
                branch=GITHUB_BRANCH
            )

            action = "UPDATED"

        # New file
        except GithubException as e:
            if e.status != 404:
                raise

            repo.create_file(
                path=path,
                message=f"AI Create: {path}",
                content=code,
                branch=GITHUB_BRANCH
            )

            action = "CREATED"

        print(
            f"✅ CLOUD PUSH: {action} {path}"
        )

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
    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )