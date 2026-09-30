from __future__ import annotations

import json
import posixpath
import re
from typing import Any


IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    ".vite",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
}


SOURCE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".vue",
    ".svelte",
    ".css",
    ".scss",
    ".html",
}


def _tool_ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return False

    return (
        result.get("status") == "success"
        or result.get("success") is True
    )


def _tool_text(result: Any) -> str:
    if isinstance(result, dict):
        for key in (
            "output",
            "content",
            "text",
            "result",
        ):
            value = result.get(key)

            if value is not None:
                return str(value)

    return str(result)


def _read_file(
    workspace: Any,
    path: str,
) -> str | None:
    try:
        result = workspace.read_file(path)
    except Exception:
        return None

    if not _tool_ok(result):
        return None

    return _tool_text(result)


def _list_files(
    workspace: Any,
) -> list[str]:
    try:
        result = workspace.list_files()
    except Exception:
        return []

    if not _tool_ok(result):
        return []

    raw = result.get("files")

    if isinstance(raw, list):
        return [
            str(item)
            for item in raw
            if isinstance(
                item,
                (str, int, float),
            )
        ]

    text = _tool_text(result)

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def _normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    path = path.strip()

    while path.startswith("./"):
        path = path[2:]

    return posixpath.normpath(path)


def _is_ignored(path: str) -> bool:
    parts = _normalize_path(path).split("/")

    return any(
        part in IGNORED_DIRECTORIES
        for part in parts
    )


def _looks_like_file(path: str) -> bool:
    normalized = _normalize_path(path)

    if not normalized:
        return False

    if normalized in {".", ".."}:
        return False

    if _is_ignored(normalized):
        return False

    filename = posixpath.basename(normalized)

    if not filename:
        return False

    if filename in {
        "-",
        "_",
        "import",
    }:
        return False

    return True


def _clean_files(
    files: list[str],
) -> list[str]:
    cleaned: set[str] = set()

    for file in files:
        normalized = _normalize_path(file)

        if not _looks_like_file(normalized):
            continue

        cleaned.add(normalized)

    return sorted(cleaned)


def _find_existing(
    files: list[str],
    candidates: list[str],
) -> str | None:
    file_set = set(files)

    for candidate in candidates:
        if candidate in file_set:
            return candidate

    return None


def _parse_package_json(
    content: str | None,
) -> dict[str, Any] | None:
    if not content:
        return None

    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            return parsed

    except Exception:
        pass

    return None


def _dependency_names(
    package_json: dict[str, Any] | None,
) -> set[str]:
    if not package_json:
        return set()

    names: set[str] = set()

    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
    ):
        dependencies = package_json.get(
            section,
            {},
        )

        if isinstance(
            dependencies,
            dict,
        ):
            names.update(
                str(name).lower()
                for name in dependencies
            )

    return names


def _detect_framework(
    files: list[str],
    package_json: dict[str, Any] | None,
) -> str | None:
    dependencies = _dependency_names(
        package_json
    )

    if "next" in dependencies:
        return "Next.js"

    if "react" in dependencies:
        return "React"

    if "vue" in dependencies:
        return "Vue"

    if "svelte" in dependencies:
        return "Svelte"

    if "angular" in dependencies:
        return "Angular"

    if "solid-js" in dependencies:
        return "SolidJS"

    if "astro" in dependencies:
        return "Astro"

    if "express" in dependencies:
        return "Express"

    if "fastapi" in dependencies:
        return "FastAPI"

    if "flask" in dependencies:
        return "Flask"

    return None


def _detect_build_tool(
    files: list[str],
    package_json: dict[str, Any] | None,
) -> str | None:
    if _find_existing(
        files,
        [
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.cjs",
        ],
    ):
        return "Vite"

    if _find_existing(
        files,
        [
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
        ],
    ):
        return "Next.js"

    if _find_existing(
        files,
        [
            "webpack.config.js",
            "webpack.config.ts",
        ],
    ):
        return "Webpack"

    if _find_existing(
        files,
        [
            "rollup.config.js",
            "rollup.config.ts",
        ],
    ):
        return "Rollup"

    if package_json:
        scripts = package_json.get(
            "scripts",
            {},
        )

        if isinstance(
            scripts,
            dict,
        ):
            script_text = json.dumps(
                scripts
            ).lower()

            if "vite" in script_text:
                return "Vite"

            if "next" in script_text:
                return "Next.js"

    return None


def _detect_language(
    files: list[str],
) -> str | None:
    extension_map = {
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".py": "Python",
        ".vue": "Vue",
        ".svelte": "Svelte",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
        ".cs": "C#",
        ".cpp": "C++",
        ".c": "C",
    }

    counts: dict[str, int] = {}

    for path in files:
        lower = path.lower()

        for extension, language in extension_map.items():
            if lower.endswith(extension):
                counts[language] = (
                    counts.get(language, 0) + 1
                )
                break

    if not counts:
        return None

    return max(
        counts,
        key=counts.get,
    )


def _detect_package_manager(
    files: list[str],
) -> str | None:
    if "pnpm-lock.yaml" in files:
        return "pnpm"

    if "yarn.lock" in files:
        return "yarn"

    if (
        "package-lock.json" in files
        or "npm-shrinkwrap.json" in files
    ):
        return "npm"

    if (
        "bun.lockb" in files
        or "bun.lock" in files
    ):
        return "bun"

    return None


def _extract_script_src(
    html: str,
) -> str | None:
    """
    Find the first JavaScript/TypeScript module
    referenced by index.html.

    Example:

        <script type="module" src="/src/main.jsx">

    returns:

        src/main.jsx
    """

    patterns = [
        r'<script[^>]+type=["\']module["\'][^>]+src=["\']([^"\']+)["\']',
        r'<script[^>]+src=["\']([^"\']+)["\'][^>]+type=["\']module["\']',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            html,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        src = match.group(1)

        if src.startswith("/"):
            src = src[1:]

        return _normalize_path(src)

    return None


def _resolve_import_path(
    importer: str,
    import_path: str,
    files: set[str],
) -> str | None:
    """
    Resolve a local JavaScript/TypeScript import.

    Example:

        src/main.jsx
        import App from "./App"

    resolves to:

        src/App.jsx
    """

    if not import_path.startswith("."):
        return None

    importer_dir = posixpath.dirname(
        importer
    )

    base = _normalize_path(
        posixpath.join(
            importer_dir,
            import_path,
        )
    )

    candidates = [
        base,
        f"{base}.tsx",
        f"{base}.ts",
        f"{base}.jsx",
        f"{base}.js",
        f"{base}.vue",
        f"{base}.svelte",
        f"{base}/index.tsx",
        f"{base}/index.ts",
        f"{base}/index.jsx",
        f"{base}/index.js",
    ]

    for candidate in candidates:
        if candidate in files:
            return candidate

    return None


def _extract_local_imports(
    content: str,
) -> list[str]:
    """
    Extract relative imports from JS/TS source.
    """

    patterns = [
        r'import\s+(?:[^"\']+\s+from\s+)?["\']([^"\']+)["\']',
        r'import\(\s*["\']([^"\']+)["\']\s*\)',
        r'require\(\s*["\']([^"\']+)["\']\s*\)',
    ]

    imports: list[str] = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            content,
            flags=re.MULTILINE,
        )

        for value in matches:
            if value.startswith("."):
                imports.append(value)

    return imports


def _detect_entry_chain(
    workspace: Any,
    files: list[str],
    framework: str | None,
) -> list[str]:
    """
    Detect the actual application entry chain.

    For Vite React projects:

        index.html
            ↓
        src/main.jsx
            ↓
        src/App.jsx
    """

    file_set = set(files)

    # --------------------------------------------------
    # VITE / HTML ENTRY
    # --------------------------------------------------

    if (
        "index.html" in file_set
        and framework in {
            "React",
            "Vue",
            "Svelte",
        }
    ):
        html = _read_file(
            workspace,
            "index.html",
        )

        if html:
            script_entry = _extract_script_src(
                html
            )

            if (
                script_entry
                and script_entry in file_set
            ):
                chain = [
                    "index.html",
                    script_entry,
                ]

                current = script_entry

                for _ in range(3):
                    content = _read_file(
                        workspace,
                        current,
                    )

                    if not content:
                        break

                    imports = _extract_local_imports(
                        content
                    )

                    resolved = None

                    for import_path in imports:
                        candidate = (
                            _resolve_import_path(
                                current,
                                import_path,
                                file_set,
                            )
                        )

                        if candidate:
                            resolved = candidate
                            break

                    if not resolved:
                        break

                    if resolved in chain:
                        break

                    chain.append(resolved)

                    current = resolved

                return chain

    # --------------------------------------------------
    # NEXT.JS
    # --------------------------------------------------

    if framework == "Next.js":
        candidates = [
            "app/page.tsx",
            "app/page.jsx",
            "pages/index.tsx",
            "pages/index.jsx",
        ]

        for candidate in candidates:
            if candidate in file_set:
                return [candidate]

    # --------------------------------------------------
    # GENERIC FALLBACK
    # --------------------------------------------------

    return _detect_entry_points(
        files,
        framework,
    )


def _detect_entry_points(
    files: list[str],
    framework: str | None,
) -> list[str]:
    file_set = set(files)

    if framework == "React":
        preferred = [
            "src/main.tsx",
            "src/main.jsx",
            "src/index.tsx",
            "src/index.jsx",
        ]

        found = [
            path
            for path in preferred
            if path in file_set
        ]

        if found:
            return found[:2]

        candidates = [
            "src/App.tsx",
            "src/App.jsx",
        ]

        return [
            path
            for path in candidates
            if path in file_set
        ][:2]

    if framework == "Vue":
        candidates = [
            "src/main.ts",
            "src/main.js",
        ]

        return [
            path
            for path in candidates
            if path in file_set
        ][:2]

    if framework == "Svelte":
        candidates = [
            "src/main.ts",
            "src/main.js",
        ]

        return [
            path
            for path in candidates
            if path in file_set
        ][:2]

    if framework == "Next.js":
        candidates = [
            "app/page.tsx",
            "app/page.jsx",
            "pages/index.tsx",
            "pages/index.jsx",
        ]

        return [
            path
            for path in candidates
            if path in file_set
        ][:2]

    candidates = [
        "index.html",
        "main.py",
        "app.py",
        "server.py",
    ]

    return [
        path
        for path in candidates
        if path in file_set
    ][:2]


def _detect_directories(
    files: list[str],
) -> list[str]:
    directories: set[str] = set()

    for path in files:
        parts = path.split("/")

        if len(parts) <= 1:
            continue

        for index in range(
            1,
            len(parts),
        ):
            directory = "/".join(
                parts[:index]
            )

            if (
                directory
                and not _is_ignored(directory)
            ):
                directories.add(directory)

    return sorted(directories)


def _source_files(
    files: list[str],
) -> list[str]:
    result: list[str] = []

    for path in files:
        lower = path.lower()

        if any(
            lower.endswith(extension)
            for extension in SOURCE_EXTENSIONS
        ):
            result.append(path)

    return sorted(result)


def scan_project(
    workspace: Any,
) -> dict[str, Any]:
    """
    Scan the current project and return normalized
    project intelligence including the real entry chain.
    """

    files = _clean_files(
        _list_files(workspace)
    )

    package_json_content = None

    if "package.json" in files:
        package_json_content = _read_file(
            workspace,
            "package.json",
        )

    package_json = _parse_package_json(
        package_json_content
    )

    framework = _detect_framework(
        files,
        package_json,
    )

    build_tool = _detect_build_tool(
        files,
        package_json,
    )

    language = _detect_language(files)

    package_manager = (
        _detect_package_manager(files)
    )

    entry_points = _detect_entry_points(
        files,
        framework,
    )

    entry_chain = _detect_entry_chain(
        workspace,
        files,
        framework,
    )

    directories = _detect_directories(
        files
    )

    scripts: dict[str, str] = {}

    if package_json:
        package_scripts = package_json.get(
            "scripts",
            {},
        )

        if isinstance(
            package_scripts,
            dict,
        ):
            scripts = {
                str(key): str(value)
                for key, value
                in package_scripts.items()
            }

    dependencies: dict[str, str] = {}

    if package_json:
        for section in (
            "dependencies",
            "devDependencies",
        ):
            values = package_json.get(
                section,
                {},
            )

            if isinstance(values, dict):
                dependencies.update(
                    {
                        str(key): str(value)
                        for key, value
                        in values.items()
                    }
                )

    source_files = _source_files(files)

    return {
        "status": "success",
        "project": {
            "framework": framework,
            "buildTool": build_tool,
            "language": language,
            "packageManager": package_manager,
        },
        "entryPoints": entry_points,
        "entryChain": entry_chain,
        "directories": directories,
        "sourceFiles": source_files,
        "files": files,
        "fileCount": len(files),
        "sourceFileCount": len(source_files),
        "scripts": scripts,
        "dependencies": dependencies,
    }

def build_project_context(scan_result: dict[str, Any]) -> str:
    project = scan_result.get("project", {})
    entry_chain = scan_result.get("entryChain", [])
    source_files = scan_result.get("sourceFiles", [])
    scripts = scan_result.get("scripts", {})
    directories = scan_result.get("directories", [])

    lines = [
        "PROJECT CONTEXT",
        "",
        f"Framework: {project.get('framework') or 'Unknown'}",
        f"Build tool: {project.get('buildTool') or 'Unknown'}",
        f"Language: {project.get('language') or 'Unknown'}",
        f"Package manager: {project.get('packageManager') or 'Unknown'}",
        "",
        "Entry chain:",
    ]

    if entry_chain:
        for index, path in enumerate(entry_chain):
            prefix = "→ " if index > 0 else ""
            lines.append(f"{prefix}{path}")
    else:
        lines.append("Unknown")

    lines.extend([
        "",
        "High-priority files:",
    ])

    priority_files: list[str] = []

    for path in entry_chain:
        if path not in priority_files:
            priority_files.append(path)

    for path in source_files:
        if path.startswith("src/routes/") and path not in priority_files:
            priority_files.append(path)

    for path in source_files:
        if path.startswith("src/App.") and path not in priority_files:
            priority_files.append(path)

        if path.startswith("src/main.") and path not in priority_files:
            priority_files.append(path)

    for path in source_files:
        if (
            path.startswith("src/components/")
            and path not in priority_files
        ):
            priority_files.append(path)

    if priority_files:
        for path in priority_files[:20]:
            lines.append(f"- {path}")
    else:
        lines.append("- None detected")

    lines.extend([
        "",
        "Important directories:",
    ])

    important_directories = []

    for directory in directories:
        if directory.startswith("src/"):
            important_directories.append(directory)

    if important_directories:
        for directory in important_directories[:15]:
            lines.append(f"- {directory}")
    else:
        lines.append("- None detected")

    lines.extend([
        "",
        "Scripts:",
    ])

    if scripts:
        for name, command in scripts.items():
            lines.append(f"- {name}: {command}")
    else:
        lines.append("- None detected")

    lines.extend([
        "",
        "Agent guidance:",
        "- Prefer high-priority files when investigating the application.",
        "- Follow the entry chain before making architectural changes.",
        "- Inspect the relevant route/component before modifying it.",
        "- Avoid changing unrelated files.",
        "- Preserve the existing framework and build setup.",
    ])

    return "\n".join(lines)
def target_project_files(
    prompt: str,
    scan_result: dict[str, Any],
    limit: int = 8,
) -> list[str]:
    """
    Rank project files by relevance to the user's task.
    Returns the most likely files to inspect first.
    """

    prompt_lower = (prompt or "").lower()

    source_files = scan_result.get("sourceFiles", [])
    entry_chain = scan_result.get("entryChain", [])

    scored: list[tuple[int, str]] = []

    # Common task concepts that often map to filenames.
    keyword_groups = {
        "pricing": {
            "pricing",
            "price",
            "prices",
            "plan",
            "plans",
            "subscription",
            "billing",
        },
        "dashboard": {
            "dashboard",
            "chart",
            "analytics",
            "metrics",
            "statistics",
        },
        "navbar": {
            "navbar",
            "navigation",
            "nav",
            "menu",
            "header",
            "logo",
        },
        "hero": {
            "hero",
            "headline",
            "landing",
            "banner",
        },
        "store": {
            "store",
            "shop",
            "product",
            "products",
            "cart",
        },
        "auth": {
            "login",
            "logout",
            "signin",
            "signup",
            "register",
            "authentication",
            "auth",
            "password",
        },
        "settings": {
            "settings",
            "preferences",
            "configuration",
            "config",
        },
        "profile": {
            "profile",
            "account",
            "user",
        },
        "terms": {
            "terms",
            "legal",
            "privacy",
            "policy",
        },
    }

    prompt_words = {
        word.strip(".,!?;:\"'()[]{}").lower()
        for word in prompt_lower.split()
        if len(word.strip(".,!?;:\"'()[]{}")) >= 3
    }

    detected_groups: set[str] = set()

    for group_name, keywords in keyword_groups.items():
        if prompt_words.intersection(keywords):
            detected_groups.add(group_name)

    for path in source_files:
        path_lower = path.lower()
        score = 0

        path_words = set(
            path_lower
            .replace("/", " ")
            .replace(".", " ")
            .replace("-", " ")
            .replace("_", " ")
            .split()
        )

        # ----------------------------------------------------
        # 1. Direct filename / prompt matches
        # ----------------------------------------------------

        for word in prompt_words:
            if word in path_words:
                score += 25

        # ----------------------------------------------------
        # 2. Semantic task groups
        # ----------------------------------------------------

        for group_name in detected_groups:
            group_keywords = keyword_groups[group_name]

            if path_words.intersection(group_keywords):
                score += 35

        # ----------------------------------------------------
        # 3. Specific application locations
        # ----------------------------------------------------

        if "/routes/" in path_lower:
            score += 5

        if "/components/" in path_lower:
            score += 5

        # ----------------------------------------------------
        # 4. Entry-chain files
        #
        # Useful for architecture, but don't let them outrank
        # task-specific files.
        # ----------------------------------------------------

        if path in entry_chain:
            score += 8

        # ----------------------------------------------------
        # 5. App entry files
        #
        # Keep them relevant, but low priority unless the task
        # specifically points toward application bootstrapping.
        # ----------------------------------------------------

        if path_lower.endswith("app.tsx"):
            score += 3

        if path_lower.endswith("app.jsx"):
            score += 3

        if path_lower.endswith("main.tsx"):
            score += 1

        if path_lower.endswith("main.jsx"):
            score += 1

        # ----------------------------------------------------
        # 6. Generic source relevance
        # ----------------------------------------------------

        if path_lower.startswith("src/"):
            score += 2

        if score > 0:
            scored.append((score, path))

    # Highest score first.
    scored.sort(
        key=lambda item: (-item[0], item[1])
    )

    return [
        path
        for _, path in scored[:limit]
    ]
    """
    Rank project files by relevance to the user's task.
    Returns the most likely files to inspect first.
    """

    prompt_lower = (prompt or "").lower()

    source_files = scan_result.get("sourceFiles", [])
    entry_chain = scan_result.get("entryChain", [])

    scored: list[tuple[int, str]] = []

    for path in source_files:
        path_lower = path.lower()
        score = 0

        # ----------------------------------------------------
        # Entry-chain relevance
        # ----------------------------------------------------

        if path in entry_chain:
            score += 30

        # ----------------------------------------------------
        # Exact words from the user's prompt
        # ----------------------------------------------------

        path_parts = (
            path_lower
            .replace("/", " ")
            .replace(".", " ")
            .replace("-", " ")
            .replace("_", " ")
            .split()
        )

        for word in prompt_lower.split():
            clean_word = (
                word
                .strip(".,!?;:\"'()[]{}")
                .lower()
            )

            if len(clean_word) < 3:
                continue

            if clean_word in path_parts:
                score += 25

        # ----------------------------------------------------
        # Route/component relevance
        # ----------------------------------------------------

        if "/routes/" in path_lower:
            score += 8

        if "/components/" in path_lower:
            score += 6

        # ----------------------------------------------------
        # Common application entry files
        # ----------------------------------------------------

        if path_lower.endswith("app.tsx"):
            score += 8

        if path_lower.endswith("app.jsx"):
            score += 8

        if path_lower.endswith("main.tsx"):
            score += 5

        if path_lower.endswith("main.jsx"):
            score += 5

        # ----------------------------------------------------
        # Generic source relevance
        # ----------------------------------------------------

        if path_lower.startswith("src/"):
            score += 3

        if score > 0:
            scored.append((score, path))

    # Highest score first.
    scored.sort(
        key=lambda item: (-item[0], item[1])
    )

    return [
        path
        for _, path in scored[:limit]
    ]