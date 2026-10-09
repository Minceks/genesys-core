from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import re
import shlex
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from pathlib import PurePosixPath


GITHUB_API = "https://api.github.com"
MAX_PROMOTION_ARCHIVE_BYTES = 12 * 1024 * 1024
PROMOTION_PROOF_TTL_SECONDS = 15 * 60


def sign_verified_checkpoint(
    *,
    signing_key: str,
    project_id: str,
    checkpoint_id: str,
    checkpoint_commit: str,
) -> str:
    payload = {
        "checkpointId": checkpoint_id,
        "checkpointCommit": checkpoint_commit,
        "projectId": project_id,
        "expiresAt": int(time.time()) + PROMOTION_PROOF_TTL_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    signature = hmac.new(
        signing_key.encode("utf-8"), encoded, hashlib.sha256
    ).digest()
    return f"{encoded.decode('ascii')}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}"


def verify_checkpoint_promotion_token(
    token: str,
    *,
    signing_key: str,
    project_id: str,
    checkpoint_id: str,
) -> str | None:
    try:
        encoded, signature_text = token.split(".", 1)
        expected_signature = hmac.new(
            signing_key.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
        ).digest()
        supplied_signature = base64.urlsafe_b64decode(
            signature_text + "=" * (-len(signature_text) % 4)
        )
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return None
        payload_bytes = base64.urlsafe_b64decode(
            encoded + "=" * (-len(encoded) % 4)
        )
        payload = json.loads(payload_bytes.decode("utf-8"))
        valid = (
            payload.get("projectId") == project_id
            and payload.get("checkpointId") == checkpoint_id
            and isinstance(payload.get("checkpointCommit"), str)
            and re.fullmatch(r"[0-9a-f]{40,64}", payload["checkpointCommit"])
            and isinstance(payload.get("expiresAt"), int)
            and payload["expiresAt"] >= int(time.time())
        )
        return payload["checkpointCommit"] if valid else None
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return None


def promote_workspace_checkpoint(
    workspace,
    checkpoint_id: str,
    *,
    project_id: str,
    sandbox_id: str,
    project_root: str,
    github_token: str,
    repository: str,
    base_branch: str,
    expected_commit: str,
) -> dict[str, object]:
    """Export a verified Daytona commit and open a PR without exposing
    the GitHub credential to the sandbox.
    """
    if not re.fullmatch(r"genesys-checkpoint-\d+", checkpoint_id or ""):
        return _error("INVALID_CHECKPOINT", "A valid verified checkpoint ID is required.")
    if not github_token.strip():
        return _error("PROMOTION_NOT_CONFIGURED", "Set GENESYS_GITHUB_TOKEN in the Cloud Agent environment.")

    workspace._ensure_sandbox_running()
    commit_result = workspace.sandbox.process.exec(
        f"git rev-parse --verify {shlex.quote(checkpoint_id)}^{{commit}}",
        cwd=project_root,
        timeout=30,
    )
    commit_sha = (commit_result.result or "").strip()
    if commit_result.exit_code != 0 or not re.fullmatch(r"[0-9a-f]{40,64}", commit_sha):
        return _error("CHECKPOINT_NOT_FOUND", "The verified checkpoint is not present in this Daytona workspace.")
    if not hmac.compare_digest(commit_sha, expected_commit):
        return _error("CHECKPOINT_CHANGED", "The Daytona checkpoint no longer matches the verified commit. Run and verify the change again.")

    parent_result = workspace.sandbox.process.exec(
        f"git rev-list --parents -n 1 {shlex.quote(commit_sha)}",
        cwd=project_root,
        timeout=30,
    )
    parent_fields = (parent_result.result or "").split()
    if parent_result.exit_code != 0 or len(parent_fields) != 2:
        return _error("INVALID_CHECKPOINT", "The checkpoint does not have a single production base commit.")
    parent_sha = parent_fields[1]

    diff_result = workspace.sandbox.process.exec(
        "git diff-tree --raw --no-renames --no-abbrev -r "
        f"{shlex.quote(parent_sha)} {shlex.quote(commit_sha)}",
        cwd=project_root,
        timeout=30,
    )
    if diff_result.exit_code != 0:
        return _error("CHECKPOINT_DIFF_FAILED", "Could not inspect the verified checkpoint changes.")

    changes: list[dict[str, object]] = []
    archive_paths: list[str] = []
    for line in (diff_result.result or "").splitlines():
        metadata, separator, filename = line.partition("\t")
        fields = metadata.split()
        if not separator or len(fields) != 5:
            continue
        old_mode, new_mode, _old_sha, _new_sha, status = fields
        filename = filename.strip()
        path = PurePosixPath(filename)
        if (
            not filename
            or path.is_absolute()
            or ".." in path.parts
            or ".git" in path.parts
            or "\n" in filename
            or "\t" in filename
            or path.name == ".env"
            or path.name.startswith(".env.")
        ):
            return _error("UNSAFE_CHECKPOINT_PATH", "The verified checkpoint contains a protected or unsafe file path.")
        if status not in {"A", "M", "D"}:
            return _error("UNSUPPORTED_CHECKPOINT_CHANGE", "The checkpoint contains a file change type GeneSys cannot promote safely.")
        mode = new_mode if status != "D" else old_mode.lstrip(":")
        if mode not in {"100644", "100755"}:
            return _error("UNSUPPORTED_FILE_MODE", "The checkpoint contains a symlink or submodule, which GeneSys will not promote.")
        changes.append({"path": path.as_posix(), "status": status, "mode": mode})
        if status != "D":
            archive_paths.append(path.as_posix())

    if not changes:
        return _error("EMPTY_CHANGESET", "The verified checkpoint contains no project changes.")

    if archive_paths:
        archive_path = f"/tmp/genesys-checkpoint-{commit_sha}.tar"
        command = (
            "git archive --format=tar -o "
            f"{shlex.quote(archive_path)} {shlex.quote(commit_sha)} -- "
            + " ".join(shlex.quote(path) for path in archive_paths)
        )
        archive_result = workspace.sandbox.process.exec(
            command,
            cwd=project_root,
            timeout=60,
        )
        if archive_result.exit_code != 0:
            return _error("CHECKPOINT_EXPORT_FAILED", "Could not export the verified files from Daytona.")
        try:
            archive_bytes = workspace.sandbox.fs.download_file(archive_path)
        finally:
            workspace.sandbox.process.exec(
                f"rm -f {shlex.quote(archive_path)}",
                cwd=project_root,
                timeout=15,
            )
        if len(archive_bytes) > MAX_PROMOTION_ARCHIVE_BYTES:
            return _error("CHECKPOINT_TOO_LARGE", "The verified change is larger than the 12 MB production promotion limit.")
        try:
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
                archived_files: dict[str, bytes] = {}
                for member in archive.getmembers():
                    name = member.name.removeprefix("./")
                    if not member.isfile():
                        continue
                    stream = archive.extractfile(member)
                    if stream is not None:
                        archived_files[name] = stream.read()
        except (tarfile.TarError, OSError):
            return _error("CHECKPOINT_EXPORT_FAILED", "The Daytona checkpoint archive could not be read.")

        for change in changes:
            if change["status"] == "D":
                continue
            content = archived_files.get(str(change["path"]))
            if content is None:
                return _error("CHECKPOINT_EXPORT_INCOMPLETE", "A changed file was missing from the Daytona checkpoint archive.")
            change["contentBase64"] = base64.b64encode(content).decode("ascii")

    project_key = hashlib.sha256(
        project_id.encode("utf-8")
    ).hexdigest()[:10]
    pull_request = create_verified_pull_request(
        token=github_token,
        repository=repository,
        base=base_branch,
        checkpoint_id=checkpoint_id,
        parent_commit=parent_sha,
        project_key=project_key,
        changes=changes,
    )
    if pull_request.get("status") != "success":
        return {
            **pull_request,
            "success": False,
            "commit": commit_sha,
            "checkpointId": checkpoint_id,
            "projectId": project_id,
        }
    return {
        **pull_request,
        "success": True,
        "commit": commit_sha,
        "checkpointId": checkpoint_id,
        "projectId": project_id,
        "sandboxId": sandbox_id,
    }


def create_verified_pull_request(
    *,
    token: str,
    repository: str,
    base: str,
    checkpoint_id: str,
    parent_commit: str,
    project_key: str,
    changes: list[dict[str, object]],
) -> dict[str, object]:
    """Publish a verified snapshot as a branch and open a review PR.

    The GitHub credential stays in the Cloud Agent process. It is never
    copied into the untrusted Daytona sandbox.
    """

    owner, separator, repo = repository.strip().partition("/")
    if (
        not separator
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", owner)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", base)
    ):
        return _error(
            "INVALID_REPOSITORY",
            "GENESYS_GITHUB_REPOSITORY must be OWNER/REPOSITORY.",
        )
    if not token.strip():
        return _error(
            "PROMOTION_NOT_CONFIGURED",
            "Set GENESYS_GITHUB_TOKEN in the Cloud Agent environment.",
        )
    if not changes:
        return _error(
            "EMPTY_CHANGESET",
            "The verified checkpoint contains no project changes.",
        )

    api_root = f"{GITHUB_API}/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GeneSys-Cloud-Agent",
    }
    branch = f"genesys/verified/{project_key}/{checkpoint_id}"

    existing = _github_request(
        f"{api_root}/pulls?{urlencode({'state': 'open', 'head': f'{owner}:{branch}', 'base': base})}",
        headers=headers,
    )
    if existing["status"] != "success":
        return existing
    open_prs = existing["data"]

    base_ref = _github_request(
        f"{api_root}/git/ref/heads/{quote(base, safe='/')}",
        headers=headers,
    )
    if base_ref["status"] != "success":
        return base_ref
    base_sha = base_ref["data"].get("object", {}).get("sha")
    if base_sha != parent_commit:
        return _error(
            "STALE_CHECKPOINT",
            "Production changed after this preview was verified. Rebuild and verify against the latest production revision before promoting.",
        )

    if isinstance(open_prs, list) and open_prs:
        pr = open_prs[0]
        return {
            "status": "success",
            "created": False,
            "number": pr.get("number"),
            "url": pr.get("html_url"),
            "branch": branch,
            "checkpointId": checkpoint_id,
        }

    base_commit = _github_request(
        f"{api_root}/git/commits/{parent_commit}",
        headers=headers,
    )
    if base_commit["status"] != "success":
        return base_commit
    base_tree = base_commit["data"].get("tree", {}).get("sha")
    if not base_tree:
        return _error("GITHUB_API_ERROR", "GitHub did not return the production tree.")

    tree_entries: list[dict[str, object]] = []
    for change in changes:
        entry: dict[str, object] = {
            "path": change["path"],
            "mode": change["mode"],
            "type": "blob",
            "sha": None,
        }
        if change["status"] != "D":
            blob = _github_request(
                f"{api_root}/git/blobs",
                headers=headers,
                data=json.dumps(
                    {
                        "content": change["contentBase64"],
                        "encoding": "base64",
                    }
                ).encode("utf-8"),
                method="POST",
                success_code=201,
            )
            if blob["status"] != "success":
                return blob
            entry["sha"] = blob["data"].get("sha")
        tree_entries.append(entry)

    new_tree = _github_request(
        f"{api_root}/git/trees",
        headers=headers,
        data=json.dumps(
            {"base_tree": base_tree, "tree": tree_entries}
        ).encode("utf-8"),
        method="POST",
        success_code=201,
    )
    if new_tree["status"] != "success":
        return new_tree

    new_commit = _github_request(
        f"{api_root}/git/commits",
        headers=headers,
        data=json.dumps(
            {
                "message": f"GeneSys verified change ({checkpoint_id})",
                "tree": new_tree["data"].get("sha"),
                "parents": [parent_commit],
            }
        ).encode("utf-8"),
        method="POST",
        success_code=201,
    )
    if new_commit["status"] != "success":
        return new_commit
    new_commit_sha = new_commit["data"].get("sha")
    if not new_commit_sha:
        return _error("GITHUB_API_ERROR", "GitHub did not return the proposed commit.")

    created_ref = _github_request(
        f"{api_root}/git/refs",
        headers=headers,
        data=json.dumps(
            {
                "ref": f"refs/heads/{branch}",
                "sha": new_commit_sha,
            }
        ).encode("utf-8"),
        method="POST",
        success_code=201,
    )
    if created_ref["status"] != "success":
        return created_ref

    pr_result = _github_request(
        f"{api_root}/pulls",
        headers=headers,
        data=json.dumps(
            {
                "title": f"GeneSys verified change ({checkpoint_id})",
                "head": branch,
                "base": base,
                "body": (
                    "This change was built and browser-verified in a GeneSys "
                    "Daytona workspace. Review the diff and Vercel preview "
                    "before merging to production.\n\n"
                    f"Verified checkpoint: `{checkpoint_id}`."
                ),
            }
        ).encode("utf-8"),
        method="POST",
        success_code=201,
    )
    if pr_result["status"] != "success":
        return {
            **pr_result,
            "branch": branch,
            "commit": new_commit_sha,
            "checkpointId": checkpoint_id,
        }

    pr = pr_result["data"]
    return {
        "status": "success",
        "created": True,
        "number": pr.get("number"),
        "url": pr.get("html_url"),
        "branch": branch,
        "baseBranch": base,
        "commit": new_commit_sha,
        "checkpointId": checkpoint_id,
    }


def _error(code: str, message: str) -> dict[str, object]:
    return {"status": "error", "code": code, "message": message}


def _github_request(
    url: str,
    *,
    headers: dict[str, str],
    data: bytes | None = None,
    method: str = "GET",
    success_code: int = 200,
) -> dict[str, object]:
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if response.status != success_code:
                return _error("GITHUB_API_ERROR", "GitHub returned an unexpected response.")
            return {"status": "success", "data": payload}
    except HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (ValueError, OSError):
            payload = {}
        return {
            "status": "error",
            "code": "GITHUB_API_ERROR",
            "httpStatus": error.code,
            "message": str(payload.get("message") or "GitHub rejected the promotion operation."),
        }
    except (TimeoutError, URLError, ValueError, OSError):
        return _error("GITHUB_UNAVAILABLE", "Could not reach GitHub to create the production pull request.")
