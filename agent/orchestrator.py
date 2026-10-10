from __future__ import annotations
from .progress import report_progress

import json
import os
import re
import time
from typing import Any

from .ai_provider import (
    AIResponse,
    GeminiProvider,
    GroqProvider,
)
from .config import load_settings
from .daytona_workspace import get_workspace
from .design_guidance import project_design_guidance
from .project_intelligence import (
    scan_project,
    build_project_context,
    target_project_files,
)

from .browser import (
    BrowserSession,
    get_browser,
    stop_browser,
)
from .tools import TOOLS, execute_tool


# ============================================================
# CONFIGURATION
# ============================================================

settings = load_settings()

MODEL = settings.genesys_model
GEMINI_MODEL = settings.genesys_gemini_model
PROVIDER_NAME = settings.provider_name
FALLBACK_PROVIDER = settings.fallback_provider

MAX_STEPS = 18
VERIFICATION_STEP_RESERVE = 6
TOTAL_MAX_STEPS = MAX_STEPS + VERIFICATION_STEP_RESERVE

MAX_COMPLETION_TOKENS = 3200

PROJECT_ID_DEFAULT = "genesys-project"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are GeneSys, an autonomous software engineering agent.

Your job is to modify a real software project inside a Daytona workspace.

You MUST follow this workflow:

1. Inspect the project before making changes.
2. Use list_files first when beginning a task.
3. Use read_file before modifying an existing file. Prefer edit_file for exact targeted changes. Partial or compacted file views must never be reconstructed with write_file.
4. Never invent file paths.
5. Make the smallest correct changes needed for the user's request.
6. When writing a file, provide its complete intended contents.
7. Before the first edit, read only files directly relevant to the task. After four file reads, begin implementation; inspect more files later only if needed.
8. After modifying files, the orchestrator will run the build.
9. Do NOT call run_build yourself.
10. Do NOT call start_preview yourself.
11. The orchestrator controls build and preview lifecycle.
12. Browser tools MUST actually be used to verify the running application.
13. If the build fails, inspect the error and repair the code.
14. Do not claim success merely because files were written.
15. Runtime/UI verification is required when the application can be launched.
16. Do not make unnecessary changes to unrelated files.
17. Finish all files needed for the requested application, including its styles and interactions,
before ending your implementation turn. When implementation or a repair is complete, respond
without tool calls; the orchestrator will then run mandatory verification. A single file edit
does not mean the application is finished.

IMPORTANT TOOL LIMITATION:

There is NO "search" tool available.

Never call a tool named:
- search
- grep
- ripgrep
- find

To locate code or text in the project:
1. Use list_files to inspect available files.
2. Use read_file to inspect the relevant file contents.
3. Do not invent or request tools that are not explicitly provided.

Available browser verification tools may include:

- browser_screenshot
- browser_console
- browser_click
- browser_type
- browser_keypress

IMPORTANT:
The orchestrator controls:
- build
- preview
- browser verification

You control:
- inspection
- reasoning
- file edits
- repairs

Do not fabricate tool results.
Do not claim a task is complete without verification.
"""

# ============================================================
# M6 TASK UNDERSTANDING
# ============================================================

def _build_task_understanding(
    prompt: str,
) -> dict[str, Any]:
    """
    Build a lightweight structured representation of the user's task.

    This is intentionally deterministic for M6.1.
    The AI agent still performs the actual reasoning and editing.
    """

    text = (prompt or "").strip()
    lower = text.lower()

    intent = "modify_project"

    if any(
        word in lower
        for word in (
            "fix",
            "bug",
            "error",
            "broken",
            "crash",
            "doesn't work",
            "not working",
        )
    ):
        intent = "fix_bug"

    elif any(
        word in lower
        for word in (
            "add",
            "create",
            "implement",
            "introduce",
        )
    ):
        intent = "add_feature"

    elif any(
        word in lower
        for word in (
            "remove",
            "delete",
        )
    ):
        intent = "remove_feature"

    elif any(
        word in lower
        for word in (
            "rename",
            "change",
            "update",
            "replace",
            "modify",
        )
    ):
        intent = "modify_project"

    scope = "project"

    if any(
        word in lower
        for word in (
            "page",
            "screen",
            "route",
        )
    ):
        scope = "page"

    if any(
        word in lower
        for word in (
            "component",
            "button",
            "navbar",
            "navigation",
            "header",
            "footer",
            "hero",
            "card",
        )
    ):
        scope = "component"

    if any(
        word in lower
        for word in (
            "text",
            "headline",
            "title",
            "label",
            "copy",
            "wording",
            "content",
        )
    ):
        change_type = "content"

    elif any(
        word in lower
        for word in (
            "style",
            "color",
            "font",
            "spacing",
            "layout",
            "design",
            "ui",
            "visual",
        )
    ):
        change_type = "visual"

    elif any(
        word in lower
        for word in (
            "api",
            "database",
            "backend",
            "server",
            "request",
            "fetch",
        )
    ):
        change_type = "backend"

    else:
        change_type = "code"

    risk = "low"

    if change_type in {
        "backend",
        "code",
    }:
        risk = "medium"

    if any(
        word in lower
        for word in (
            "database",
            "migration",
            "authentication",
            "auth",
            "security",
            "payment",
            "billing",
        )
    ):
        risk = "high"

    return {
        "intent": intent,
        "changeType": change_type,
        "scope": scope,
        "risk": risk,
        "request": text,
    }


_BUILD_REQUEST_START = re.compile(
    r"^(?:(?:please|okay|ok|sure|now)[,\s]+)*(?:build|create|make|add|implement|design|develop|code|write|generate|fix|update|change|modify|remove|delete|replace|refactor|integrate|convert|improve|restyle|rewrite|rename)\b",
    re.IGNORECASE,
)
_REQUEST_TO_BUILD = re.compile(
    r"^(?:(?:please|okay|ok|hey)[,\s]+)*(?:can|could|would)\s+you\s+(?:(?:please|also|just)\s+)*(?:build|create|make|add|implement|design|develop|code|write|generate|fix|update|change|modify|remove|delete|replace|refactor|integrate|convert|improve|restyle|rewrite|rename)\b",
    re.IGNORECASE,
)
_REQUEST_HELP_BUILD = re.compile(
    r"^(?:can|could|would)\s+you\s+(?:please\s+)?help\s+me\s+(?:to\s+)?(?:build|create|make|add|implement|design|develop|fix|update|change|modify)\b",
    re.IGNORECASE,
)
_GENERAL_CAPABILITY_QUESTION = re.compile(
    r"^(?:can|could|would)\s+you\s+(?:build|create|make|design|develop|fix|write|code)\s+(?:websites?|apps?|applications?|software|projects?|anything|all\s+that)(?:\s+for\s+me)?\s*\??$",
    re.IGNORECASE,
)
_QUESTION_OR_CHAT_START = re.compile(
    r"^(?:hi\b|hello\b|hey\b|thanks\b|thank\s+you\b|ok\b|okay\b|sure\b|got\s+it\b|sounds\s+good\b|makes\s+sense\b|great\b|perfect\b|what\b|why\b|when\b|where\b|who\b|which\b|how\b|is\b|are\b|do\b|does\b|did\b|can\b|could\b|would\b|should\b|will\b|any\b|tell\s+me\b|explain\b|describe\b|show\s+me\b|what's\b)",
    re.IGNORECASE,
)


def classify_request_type(prompt: str) -> str:
    """Separate clear chat questions from requests that should edit a project.

    Ambiguous statements default to build so existing task behavior is preserved.
    """
    text = (prompt or "").strip()
    if not text:
        return "chat"
    if _GENERAL_CAPABILITY_QUESTION.fullmatch(text):
        return "chat"
    if (
        _BUILD_REQUEST_START.match(text)
        or _REQUEST_TO_BUILD.match(text)
        or _REQUEST_HELP_BUILD.match(text)
        or re.match(r"^(?:i|we)\s+(?:want|need)\s+(?:you\s+to\s+)?(?:build|create|make|add|implement|design|develop|fix|update|change|modify)\b", text, re.IGNORECASE)
        or re.match(r"^let'?s\s+(?:build|create|make|add|implement|design|develop|fix|update|change|modify)\b", text, re.IGNORECASE)
    ):
        return "build"
    if _QUESTION_OR_CHAT_START.match(text) or text.endswith("?"):
        return "chat"
    return "build"


def _answer_chat_question(
    prompt: str,
    project_id: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Answer a conversational question without opening a project workspace."""
    provider = get_provider()
    chat_messages = [
        {
            "role": "system",
            "content": (
                "You are GeneSys, a helpful assistant for a website and app "
                "building agent. Answer the user's question directly and "
                "concisely. Do not call tools, claim you inspected project "
                "files, or say you changed, built, or deployed anything. "
                "If a question asks about the user's specific project and "
                "you do not have its details, say so and invite them to ask "
                "GeneSys to inspect or change it."
            ),
        },
    ]
    for turn in (conversation_history or [])[-10:]:
        role = turn.get("role")
        content = str(turn.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            chat_messages.append(
                {
                    "role": role,
                    "content": content[:2000],
                }
            )
    chat_messages.append({"role": "user", "content": prompt})
    try:
        response = provider.generate(chat_messages, [])
    except Exception:
        if settings.provider_name != "groq" or FALLBACK_PROVIDER != "gemini":
            raise
        response = GeminiProvider(model=GEMINI_MODEL).generate(
            chat_messages,
            [],
        )
    answer = (response.text or "").strip()
    if not answer:
        answer = "I couldn't generate an answer just now. Please try again."
    return {
        "status": "success",
        "requestType": "chat",
        "intent": "question",
        "text": answer,
        "agent": "GeneSys Assistant",
        "steps": [],
        "modifiedFiles": [],
        "buildAttempted": False,
        "buildPassed": False,
        "browserVerified": False,
        "previewStarted": False,
        "previewUrl": None,
        "checkpoint": None,
        "projectId": project_id,
    }

# ============================================================
# TOOL / MESSAGE HELPERS
# ============================================================

def _safe_json(value: Any) -> str:
    """
    Convert a value into compact JSON for model tool messages.
    """
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return str(value)


def _build_assistant_tool_message(
    response: AIResponse,
) -> dict[str, Any]:
    """
    Convert normalized AIResponse tool calls into the internal
    OpenAI-compatible message representation used by the
    orchestrator's message history.

    GroqProvider understands this representation directly.
    GeminiProvider will later serialize it into Gemini's format.
    """

    tool_calls = []

    for call in response.tool_calls:
        tool_call = {
            "id": call.id,
            "type": "function",
            "function": {
                "name": call.name,
                "arguments": _safe_json(
                    call.arguments
                ),
            },
        }

        if getattr(
            call,
            "thought_signature",
            None,
        ) is not None:
            tool_call[
                "thought_signature"
            ] = call.thought_signature

        tool_calls.append(
            tool_call
        )

    return {
        "role": "assistant",
        "content": response.text or "",
        "tool_calls": tool_calls,
    }


def _compact_messages(
    messages: list[dict[str, Any]],
    max_messages: int = 40,
) -> list[dict[str, Any]]:
    """
    Prevent conversation history from growing without bound.

    Preserve:
    - system messages
    - assistant tool-call messages together with their tool results
    - recent conversation

    Tool-call / tool-result pairs must never be split because
    Gemini requires function responses to immediately follow
    the corresponding function call turn.
    """

    if len(messages) <= max_messages:
        return messages

    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
    ]

    non_system = [
        message
        for message in messages
        if message.get("role") != "system"
    ]

    keep_count = max_messages - len(system_messages)

    if keep_count <= 0:
        return system_messages[:1]

    # Build recent history while keeping assistant tool calls
    # together with their following tool responses.
    recent: list[dict[str, Any]] = []

    index = len(non_system) - 1

    while index >= 0 and len(recent) < keep_count:
        message = non_system[index]
        role = message.get("role")

        if role == "tool":
            tool_message = message

            if index > 0:
                previous = non_system[index - 1]

                if (
                    previous.get("role") == "assistant"
                    and previous.get("tool_calls")
                ):
                    recent.insert(0, tool_message)
                    recent.insert(0, previous)
                    index -= 2
                    continue

        recent.insert(0, message)
        index -= 1

    # Never start the retained history with a tool response.
    while recent and recent[0].get("role") == "tool":
        recent.pop(0)

    return system_messages[:1] + recent


# ============================================================
# PROVIDER
# ============================================================

def get_provider():
    """
    Select the configured AI provider.

    Default:
        Groq

    Supported:
        groq
        gemini
    """

    provider_name = settings.provider_name

    if provider_name == "groq":
        return GroqProvider(
            model=MODEL,
        )

    if provider_name == "gemini":
        return GeminiProvider(
            model=GEMINI_MODEL,
        )

    raise RuntimeError(
        f"Unsupported GENESYS_PROVIDER={provider_name!r}. "
        f"Expected 'groq' or 'gemini'."
    )


# ============================================================
# TOOL EXECUTION
# ============================================================

def _execute_agent_tool(
    tool_name: str,
    arguments: dict[str, Any],
    project_id: str,
) -> Any:
    """
    Execute a model-requested tool through the existing GeneSys
    tool system.

    The existing tools.py remains the source of truth for actual
    filesystem/browser operations.
    """

    if not isinstance(arguments, dict):
        arguments = {}

    try:
        return execute_tool(
            tool_name,
            arguments,
            project_id=project_id,
        )
    except TypeError:
        # Compatibility fallback for an execute_tool implementation
        # that does not accept project_id as a keyword.
        try:
            return execute_tool(
                tool_name,
                arguments,
                project_id,
            )
        except TypeError:
            return execute_tool(
                tool_name,
                arguments,
            )


# ============================================================
# RESULT HELPERS
# ============================================================

def _tool_result_text(result: Any) -> str:
    """
    Convert tool output into a model-readable string.
    """

    if isinstance(result, str):
        return result

    try:
        return json.dumps(
            result,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return str(result)


def _result_status(result: Any) -> str:
    """
    Safely extract status from a tool result.
    """

    if isinstance(result, dict):
        return str(
            result.get("status", "")
        ).lower()

    return ""

# ============================================================
# M6.2 CHANGE PLANNING
# ============================================================

def _build_change_plan(
    task: dict[str, Any],
    targeted_files: list[str],
    project_scan: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a deterministic change plan from the normalized task
    and project intelligence.

    The plan guides the AI agent before it edits files.
    """

    intent = task.get(
        "intent",
        "modify_project",
    )

    change_type = task.get(
        "changeType",
        "code",
    )

    scope = task.get(
        "scope",
        "project",
    )

    risk = task.get(
        "risk",
        "medium",
    )

    request = task.get(
        "request",
        "",
    )

    entry_chain = project_scan.get(
        "entryChain",
        [],
    )

    steps: list[str] = []

    steps.append(
        "Inspect the most relevant existing files before editing."
    )

    if targeted_files:
        steps.append(
            "Prioritize the targeted files identified by "
            "project intelligence."
        )

    if entry_chain:
        steps.append(
            "Use the detected application entry chain to "
            "understand how the requested area is connected."
        )

    if intent == "add_feature":
        steps.append(
            "Implement the requested feature using the "
            "existing project structure."
        )

    elif intent == "remove_feature":
        steps.append(
            "Remove only the requested functionality and "
            "preserve unrelated behavior."
        )

    elif intent == "fix_bug":
        steps.append(
            "Identify the smallest relevant code path and "
            "repair the underlying issue."
        )

    else:
        steps.append(
            "Make the smallest change that satisfies the "
            "user's request."
        )

    if change_type == "content":
        steps.append(
            "Prefer changing the source of the requested "
            "content rather than generated or derived files."
        )

    elif change_type == "visual":
        steps.append(
            "Prefer the existing component or page responsible "
            "for the requested visual change."
        )

    elif change_type == "backend":
        steps.append(
            "Preserve existing frontend contracts while changing "
            "the relevant backend or data flow."
        )

    steps.append(
        "Do not modify generated files, unrelated files, or "
        "project infrastructure unless required."
    )

    steps.append(
        "After editing, allow the orchestrator to run the "
        "mandatory build and runtime verification."
    )

    return {
        "intent": intent,
        "changeType": change_type,
        "scope": scope,
        "risk": risk,
        "request": request,
        "targetedFiles": targeted_files,
        "entryChain": entry_chain,
        "steps": steps,
    }

# ============================================================
# M6.3 CHANGE PLAN VALIDATION
# ============================================================

def _validate_change_plan(
    plan: dict[str, Any],
    project_scan: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate a deterministic change plan before execution.
    """

    issues: list[str] = []
    warnings: list[str] = []

    valid_intents = {
        "modify_project",
        "add_feature",
        "remove_feature",
        "fix_bug",
    }

    valid_change_types = {
        "visual",
        "content",
        "backend",
        "code",
    }

    valid_scopes = {
        "project",
        "page",
        "component",
    }

    valid_risks = {
        "low",
        "medium",
        "high",
    }

    intent = plan.get("intent")
    change_type = plan.get("changeType")
    scope = plan.get("scope")
    risk = plan.get("risk")
    request = str(
        plan.get("request", "")
    ).strip()

    targeted_files = plan.get(
        "targetedFiles",
        [],
    )

    steps = plan.get(
        "steps",
        [],
    )

    source_files = set(
        project_scan.get(
            "sourceFiles",
            [],
        )
    )

    if intent not in valid_intents:
        issues.append(
            f"Invalid intent: {intent}"
        )

    if change_type not in valid_change_types:
        issues.append(
            f"Invalid change type: {change_type}"
        )

    if scope not in valid_scopes:
        issues.append(
            f"Invalid scope: {scope}"
        )

    if risk not in valid_risks:
        issues.append(
            f"Invalid risk: {risk}"
        )

    if not request:
        issues.append(
            "Change plan does not contain a user request."
        )

    if not isinstance(
        targeted_files,
        list,
    ):
        issues.append(
            "Targeted files must be a list."
        )
        targeted_files = []

    if not isinstance(
        steps,
        list,
    ):
        issues.append(
            "Plan steps must be a list."
        )
        steps = []

    if not steps:
        issues.append(
            "Change plan contains no execution steps."
        )

    missing_files = [
        path
        for path in targeted_files
        if path not in source_files
    ]

    if missing_files:
        warnings.append(
            "Some targeted files were not found in "
            "the scanned source files: "
            + ", ".join(
                missing_files
            )
        )

    protected_files = [
        path
        for path in targeted_files
        if (
            "routeTree.gen" in path
            or path.endswith(".gen.ts")
            or path.endswith(".gen.tsx")
        )
    ]

    if protected_files:
        warnings.append(
            "Protected/generated files were targeted: "
            + ", ".join(
                protected_files
            )
            + ". These files should not be modified."
        )

    if risk == "high":
        warnings.append(
            "High-risk change detected. "
            "The agent should minimize scope and "
            "avoid unrelated modifications."
        )

    if (
        change_type == "backend"
        and scope == "component"
    ):
        warnings.append(
            "Backend change classified at component scope. "
            "Verify that the affected data flow is correct."
        )

    if (
        change_type == "content"
        and scope == "project"
    ):
        warnings.append(
            "Content change has project-wide scope. "
            "Verify that the broader scope is intentional."
        )

    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "targetedFilesChecked": len(
            targeted_files
        ),
        "stepsChecked": len(
            steps
        ),
        "protectedFiles": protected_files,
    }

def _validate_execution(
    change_plan: dict[str, Any],
    modified_files: list[str],
) -> dict[str, Any]:
    """
    Validate that the agent's actual file changes stayed within
    the approved change plan.
    """

    issues: list[str] = []
    warnings: list[str] = []

    targeted_files = set(
        change_plan.get(
            "targetedFiles",
            [],
        )
    )

    modified = set(
        modified_files or []
    )

    protected_files = {
        path
        for path in modified
        if (
            "routeTree.gen" in path
            or path.endswith(".gen.ts")
            or path.endswith(".gen.tsx")
        )
    }

    unexpected_files = sorted(
        modified - targeted_files
    )

    if protected_files:
        issues.append(
            "Protected/generated files were modified: "
            + ", ".join(
                sorted(protected_files)
            )
        )

    if unexpected_files:
        warnings.append(
            "Files outside the targeted set were modified: "
            + ", ".join(
                unexpected_files
            )
        )

    if not modified:
        issues.append(
            "No project files were modified."
        )

    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "modifiedFiles": sorted(modified),
        "targetedFiles": sorted(targeted_files),
        "unexpectedFiles": unexpected_files,
        "protectedFiles": sorted(protected_files),
    }

def _summarize_diff(
    diff_text: str,
) -> dict[str, Any]:
    """
    Summarize a Git diff deterministically.

    This does not use an LLM. It extracts changed files and
    approximate added/removed line counts directly from the diff.
    """

    changed_files: list[str] = []
    added_lines = 0
    removed_lines = 0

    current_file: str | None = None

    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()

            if len(parts) >= 4:
                current_file = parts[2][2:]

                if current_file not in changed_files:
                    changed_files.append(current_file)

        elif line.startswith("+++ ") or line.startswith("--- "):
            # File header lines are metadata, not actual changes.
            continue

        elif line.startswith("+"):
            added_lines += 1

        elif line.startswith("-"):
            removed_lines += 1

    return {
        "filesChanged": len(changed_files),
        "changedFiles": changed_files,
        "linesAdded": added_lines,
        "linesRemoved": removed_lines,
    }
def _classify_diff_changes(
    diff_text: str,
) -> dict[str, Any]:
    """
    Classify changed Git diff lines deterministically.

    This is a heuristic layer used for verification, not
    as a replacement for semantic understanding.
    """

    content_keywords = {
        "headline",
        "title",
        "label",
        "description",
        "text",
        "copy",
        "content",
        "heading",
        "paragraph",
    }

    visual_keywords = {
        "className",
        "style",
        "color",
        "font",
        "spacing",
        "padding",
        "margin",
        "width",
        "height",
        "grid",
        "flex",
        "border",
        "shadow",
        "background",
    }

    changed_lines: list[str] = []
    categories: set[str] = set()

    for line in (diff_text or "").splitlines():
        if not line.startswith(("+", "-")):
            continue

        if line.startswith(("+++", "---")):
            continue

        content = line[1:].strip()

        if not content:
            continue

        changed_lines.append(content)

        lower = content.lower()

        if any(
            keyword.lower() in lower
            for keyword in content_keywords
        ):
            categories.add("content")

        if any(
            keyword.lower() in lower
            for keyword in visual_keywords
        ):
            categories.add("visual")

        if not any(
            keyword.lower() in lower
            for keyword in content_keywords
        ) and not any(
            keyword.lower() in lower
            for keyword in visual_keywords
        ):
            categories.add("code")

    return {
        "categories": sorted(categories),
        "changedLines": changed_lines,
    }

def _validate_diff(
    diff_summary: dict[str, Any],
    change_plan: dict[str, Any],
    diff_classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate the actual Git diff against the approved change plan.
    """

    issues: list[str] = []
    warnings: list[str] = []

    diff_classification = (
        diff_classification
        or {}
    )

    detected_categories = set(
        diff_classification.get(
            "categories",
            [],
        )
    )

    expected_change_type = change_plan.get(
        "changeType",
        "code",
    )

    changed_files = set(
        diff_summary.get(
            "changedFiles",
            [],
        )
    )

    targeted_files = set(
        change_plan.get(
            "targetedFiles",
            [],
        )
    )

    protected_files = {
        path
        for path in changed_files
        if (
            "routeTree.gen" in path
            or path.endswith(".gen.ts")
            or path.endswith(".gen.tsx")
        )
    }

    unexpected_files = sorted(
        changed_files - targeted_files
    )

    if protected_files:
        issues.append(
            "Protected/generated files were modified: "
            + ", ".join(
                sorted(protected_files)
            )
        )

    if unexpected_files:
        warnings.append(
            "Files outside the targeted set were modified: "
            + ", ".join(
                unexpected_files
            )
        )

    if not changed_files:
        warnings.append(
            "Git diff contains no changed files."
        )
    
    if (
        expected_change_type != "code"
        and detected_categories
        and expected_change_type not in detected_categories
    ):
        warnings.append(
            "Diff categories do not clearly match "
            f"the planned change type "
            f"'{expected_change_type}': "
            + ", ".join(
                sorted(detected_categories)
            )
        )

    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "changedFiles": sorted(changed_files),
        "targetedFiles": sorted(targeted_files),
        "unexpectedFiles": unexpected_files,
        "protectedFiles": sorted(protected_files),
        "linesAdded": diff_summary.get(
            "linesAdded",
            0,
        ),
        "linesRemoved": diff_summary.get(
            "linesRemoved",
            0,
        ),
    }
def _classify_failure(
    failure_result: dict[str, Any] | None,
    failure_context: str = "",
) -> dict[str, Any]:
    """
    Classify an agent failure deterministically.

    This function does not use an LLM. It inspects the failure
    context and result to determine which recovery category
    should handle the failure.
    """

    result = failure_result or {}

    error_text = " ".join(
        str(
            value
        )
        for value in (
            result.get("error", ""),
            result.get("output", ""),
            result.get("message", ""),
            failure_context,
        )
        if value
    ).lower()

    if any(
        keyword in error_text
        for keyword in (
            "build",
            "tsc",
            "typescript",
            "vite",
            "compile",
            "compilation",
            "syntaxerror",
            "syntax error",
        )
    ):
        failure_type = "build"

    elif any(
        keyword in error_text
        for keyword in (
            "preview",
            "server",
            "connection refused",
            "econnrefused",
            "port",
        )
    ):
        failure_type = "preview"

    elif any(
        keyword in error_text
        for keyword in (
            "browser",
            "playwright",
            "page",
            "console",
            "screenshot",
            "navigation",
        )
    ):
        failure_type = "browser"

    elif any(
        keyword in error_text
        for keyword in (
            "diff",
            "git diff",
            "changed files",
            "protected/generated",
        )
    ):
        failure_type = "diff"

    elif any(
        keyword in error_text
        for keyword in (
            "execution",
            "tool",
            "write_file",
            "read_file",
            "list_files",
        )
    ):
        failure_type = "execution"

    else:
        failure_type = "unknown"

    return {
        "failureType": failure_type,
        "message": (
            str(
                result.get(
                    "error",
                    result.get(
                        "message",
                        "",
                    ),
                )
            )
        ),
        "context": failure_context,
    }
def _build_recovery_strategy(
    failure: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a deterministic recovery strategy from a classified
    failure.

    This function does not use an LLM. It decides which recovery
    actions are appropriate for the failure category.
    """

    failure_type = failure.get(
        "failureType",
        "unknown",
    )

    strategies: dict[str, dict[str, Any]] = {
        "build": {
            "strategy": "repair_build",
            "description": (
                "Inspect the build failure, identify the affected "
                "source code, make the smallest repair, and rebuild."
            ),
            "actions": [
                "Inspect the build error output.",
                "Identify the relevant source file.",
                "Make the smallest necessary repair.",
                "Run the mandatory build again.",
            ],
            "retryable": True,
        },
        "preview": {
            "strategy": "recover_preview",
            "description": (
                "Recover the preview environment and verify that "
                "the application starts correctly."
            ),
            "actions": [
                "Inspect the preview failure.",
                "Check whether the preview process is running.",
                "Restart or recover the preview if necessary.",
                "Verify the preview again.",
            ],
            "retryable": True,
        },
        "browser": {
            "strategy": "repair_runtime",
            "description": (
                "Inspect browser/runtime failures and repair the "
                "affected application behavior."
            ),
            "actions": [
                "Inspect browser verification output.",
                "Inspect browser console errors.",
                "Identify the affected source code.",
                "Make the smallest necessary repair.",
                "Run browser verification again.",
            ],
            "retryable": True,
        },
        "diff": {
            "strategy": "repair_scope",
            "description": (
                "Correct changes that fall outside the approved "
                "change plan."
            ),
            "actions": [
                "Inspect the Git diff.",
                "Identify unexpected or protected files.",
                "Revert unrelated changes.",
                "Re-check the Git diff.",
            ],
            "retryable": True,
        },
        "execution": {
            "strategy": "retry_execution",
            "description": (
                "Recover from an agent tool or execution failure."
            ),
            "actions": [
                "Inspect the failed tool result.",
                "Determine whether the operation can be retried.",
                "Retry the operation with the smallest valid input.",
            ],
            "retryable": True,
        },
        "unknown": {
            "strategy": "inspect_failure",
            "description": (
                "Inspect the failure before attempting recovery."
            ),
            "actions": [
                "Inspect the failure details.",
                "Determine the affected subsystem.",
                "Avoid making speculative changes.",
            ],
            "retryable": False,
        },
    }

    strategy = strategies.get(
        failure_type,
        strategies["unknown"],
    )

    return {
        "failureType": failure_type,
        "strategy": strategy["strategy"],
        "description": strategy["description"],
        "actions": strategy["actions"],
        "retryable": strategy["retryable"],
    }
def _build_recovery_context(
    failure: dict[str, Any],
    strategy: dict[str, Any],
    task_understanding: dict[str, Any] | None = None,
    change_plan: dict[str, Any] | None = None,
    failure_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a compact, structured context for a recovery attempt.

    This keeps recovery deterministic and gives the repairing agent
    the evidence it needs without dumping unrelated state.
    """

    task_understanding = (
        task_understanding
        or {}
    )

    change_plan = (
        change_plan
        or {}
    )

    failure_result = (
        failure_result
        or {}
    )

    failure_type = failure.get(
        "failureType",
        "unknown",
    )

    message = failure.get(
        "message",
        "",
    )

    raw_output = failure_result.get(
        "output",
        "",
    )

    if not raw_output:
        raw_output = failure_result.get(
            "error",
            "",
        )

    if not raw_output:
        raw_output = failure_result.get(
            "message",
            "",
        )

    # Keep recovery context bounded.
    output = str(
        raw_output or ""
    )[-12000:]

    return {
        "failureType": failure_type,
        "strategy": strategy.get(
            "strategy",
            "inspect_failure",
        ),
        "retryable": strategy.get(
            "retryable",
            False,
        ),
        "failureMessage": message,
        "failureOutput": output,
        "recoveryActions": strategy.get(
            "actions",
            [],
        ),
        "task": {
            "intent": task_understanding.get(
                "intent",
            ),
            "changeType": task_understanding.get(
                "changeType",
            ),
            "scope": task_understanding.get(
                "scope",
            ),
            "request": task_understanding.get(
                "request",
            ),
        },
        "changePlan": {
            "targetedFiles": change_plan.get(
                "targetedFiles",
                [],
            ),
            "changeType": change_plan.get(
                "changeType",
            ),
            "scope": change_plan.get(
                "scope",
            ),
        },
    }

def _should_rollback_for_recovery(
    strategy: dict[str, Any],
    recovery_checkpoint_id: str | None,
) -> bool:
    """
    Determine whether recovery should restore the latest
    known-good checkpoint before attempting another repair.
    """

    if not recovery_checkpoint_id:
        return False

    if not strategy.get("retryable", False):
        return False

    return True

def _can_attempt_recovery(
    recovery_attempts: int,
    max_recovery_attempts: int,
    strategy: dict[str, Any],
) -> bool:
    """
    Determine whether another recovery attempt is allowed.
    """

    if not strategy.get(
        "retryable",
        False,
    ):
        return False

    if recovery_attempts >= max_recovery_attempts:
        return False

    return True


def _build_recovery_prompt(
    recovery_context: dict[str, Any],
) -> str:
    """
    Convert structured recovery context into a focused repair
    instruction for the agent.
    """

    failure_type = recovery_context.get(
        "failureType",
        "unknown",
    )

    strategy = recovery_context.get(
        "strategy",
        "inspect_failure",
    )

    failure_message = recovery_context.get(
        "failureMessage",
        "",
    )

    failure_output = recovery_context.get(
        "failureOutput",
        "",
    )

    actions = recovery_context.get(
        "recoveryActions",
        [],
    )

    task = recovery_context.get(
        "task",
        {},
    )

    change_plan = recovery_context.get(
        "changePlan",
        {},
    )

    action_text = "\n".join(
        f"- {action}"
        for action in actions
    )

    targeted_files = "\n".join(
        f"- {path}"
        for path in change_plan.get(
            "targetedFiles",
            [],
        )
    )

    return f"""
RECOVERY ATTEMPT

A previous execution step failed.

Failure type:
{failure_type}

Recovery strategy:
{strategy}

Original request:
{task.get("request", "")}

Failure message:
{failure_message}

Failure output:
{failure_output}

Approved targeted files:
{targeted_files}

Recovery actions:
{action_text}

Instructions:
- Fix the underlying failure.
- Make the smallest necessary change.
- Do not modify unrelated files.
- Do not modify generated files.
- Do not change the user's requested behavior.
- After repairing the issue, stop and allow the orchestrator
  to perform verification again.
""".strip()

def _validate_recovery(
    failure_type: str,
    verification_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Determine whether a recovery attempt successfully resolved
    the original failure.

    This function is deterministic and does not use an LLM.
    """

    result = verification_result or {}

    status = _result_status(
        result
    )

    if failure_type == "build":
        passed = (
            status == "success"
            and result.get(
                "success",
                True,
            )
        )

    elif failure_type == "preview":
        passed = (
            status == "success"
            and result.get(
                "success",
                True,
            )
        )

    elif failure_type == "browser":
        passed = (
            status == "success"
            and result.get(
                "success",
                True,
            )
        )

    elif failure_type == "diff":
        passed = (
            status == "success"
            and result.get(
                "valid",
                False,
            )
        )

    elif failure_type == "execution":
        passed = (
            status == "success"
        )

    else:
        passed = (
            status == "success"
        )

    return {
        "failureType": failure_type,
        "validated": passed,
        "status": status,
    }

def _build_recovery_limits(
    recovery_attempts: int,
    max_recovery_attempts: int = 2,
) -> dict[str, Any]:
    """
    Build deterministic recovery retry-limit information.
    """

    if max_recovery_attempts < 0:
        max_recovery_attempts = 0

    if recovery_attempts < 0:
        recovery_attempts = 0

    exhausted = (
        recovery_attempts
        >= max_recovery_attempts
    )

    remaining = max(
        0,
        max_recovery_attempts
        - recovery_attempts,
    )

    return {
        "attempts": recovery_attempts,
        "maxAttempts": max_recovery_attempts,
        "remainingAttempts": remaining,
        "exhausted": exhausted,
    }

def _build_recovery_report(
    attempted: bool,
    recovery_attempts: int,
    failure: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    limits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a compact structured recovery report.
    """

    failure = failure or {}
    strategy = strategy or {}
    validation = validation or {}
    limits = limits or {}

    return {
        "attempted": attempted,
        "attempts": recovery_attempts,
        "failureType": failure.get(
            "failureType",
            "unknown",
        ),
        "strategy": strategy.get(
            "strategy",
            "none",
        ),
        "validated": validation.get(
            "validated",
            False,
        ),
        "remainingAttempts": limits.get(
            "remainingAttempts",
            0,
        ),
        "exhausted": limits.get(
            "exhausted",
            False,
        ),
    }

# ============================================================
# MAIN AGENT
# ============================================================

def run_agent(
    prompt: str,
    project_id: str = PROJECT_ID_DEFAULT,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:

    prompt = (prompt or "").strip()

    if not prompt:
        return {
            "status": "error",
            "message": "Prompt is required.",
            "text": "Please provide a task.",
            "agent": "genesys",
            "steps": 0,
            "modifiedFiles": [],
            "buildAttempted": False,
            "buildPassed": False,
        }

    report_progress("Understanding request")
    request_type = classify_request_type(prompt)
    if request_type == "chat":
        try:
            report_progress("Answering your question")
            return _answer_chat_question(
                prompt,
                project_id,
                conversation_history,
            )
        except Exception:
            return {
                "status": "error",
                "requestType": "chat",
                "intent": "question",
                "message": "GeneSys couldn't answer just now. Please try again.",
                "text": "GeneSys couldn't answer just now. Please try again.",
                "agent": "GeneSys Assistant",
                "steps": [],
                "modifiedFiles": [],
                "buildAttempted": False,
                "buildPassed": False,
                "browserVerified": False,
                "previewStarted": False,
                "previewUrl": None,
                "checkpoint": None,
            }

    report_progress("Preparing workspace")
    agent_deadline = time.monotonic() + min(
        settings.agent_timeout_seconds,
        240,
    )

    print()
    print("=" * 40)
    print("🤖 AGENT REQUEST:", prompt)
    print("📦 PROJECT:", project_id)
    print("=" * 40)

    # --------------------------------------------------------
    # M6 TASK UNDERSTANDING
    # --------------------------------------------------------

    task_understanding = _build_task_understanding(
        prompt
    )

    print("🧠 Task understanding:")
    print(
        json.dumps(
            task_understanding,
            indent=2,
            ensure_ascii=False,
        )
    )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    provider = get_provider()

    active_provider_name = settings.provider_name

    workspace = get_workspace(
        project_id
    )

    browser = BrowserSession(
        project_id=project_id
    )

    recovery_checkpoint_id = None

    # Checkpoint discovery is helpful for rollback, but it must not prevent
    # a new task from starting when Daytona's process API is temporarily slow.
    try:
        checkpoint_list = (
            workspace.list_checkpoints()
            if hasattr(workspace, "list_checkpoints")
            else {}
        )
    except Exception as exc:
        print(
            "⚠️ Checkpoint lookup failed; continuing without a recovery checkpoint:",
            exc,
        )
        checkpoint_list = {}

    checkpoints = checkpoint_list.get(
        "checkpoints",
        []
    ) if checkpoint_list.get("status") == "success" else []

    if checkpoints:
        first_checkpoint = checkpoints[0]

        if isinstance(first_checkpoint, dict):
            recovery_checkpoint_id = first_checkpoint.get(
                "checkpointId"
            )
        elif isinstance(first_checkpoint, str):
            recovery_checkpoint_id = first_checkpoint

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + (
                "\nThis is an independent user application, not the GeneSys platform. "
                "Read PROJECT.md if present. The requested application MUST appear at /, "
                "the preview entry page. Prefer src/App.jsx for the clean React starter. "
                "If recovered/ exists, inspect relevant preserved generated files and adapt "
                "their functionality into this application. recovered/ is reference-only backup source: "
                "NEVER import or re-export a file from recovered/. Write standalone components under src/. "
                "Remove old createRoute/Route/rootRoute wrappers, platform navigation and @/ platform imports. "
                "Reimplement needed components using this project's actual dependencies. "
                "Do not merely create an unreachable route."
                + project_design_guidance(project_id)
                if project_id != PROJECT_ID_DEFAULT else ""
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    modified_files: list[str] = []

    inspected = False
    build_attempted = False
    build_passed = False
    preview_started = False
    browser_verified = False
    verification_complete = False

    changed_since_build = False

    implementation_ready = False

    recovery_attempts = 0
    max_recovery_attempts = 2
    recovery_report = None
    last_recovery_prompt = None
    recovery_failure_type: str | None = None
    recovery_strategy: dict[str, Any] | None = None
    recovery_waiting_for_model = False
    checkpoint_result: dict[str, Any] | None = None

    def _agent_timeout_result() -> dict[str, Any]:
        try:
            stop_browser(project_id)
        except Exception:
            pass

        message = (
            "Agent execution reached its time limit before all "
            "required build and browser checks completed."
        )
        print("⏱️", message)

        return {
            "status": "error",
            "message": message,
            "text": (
                last_answer
                or "The agent reached its execution time limit."
            ),
            "agent": "genesys",
            "provider": active_provider_name,
            "model": (
                GEMINI_MODEL
                if active_provider_name == "gemini"
                else MODEL
            ),
            "steps": steps_used,
            "modifiedFiles": modified_files,
            "buildAttempted": build_attempted,
            "buildPassed": build_passed,
            "previewStarted": preview_started,
            "browserVerified": browser_verified,
            "previewUrl": preview_url,
            "errorType": "agent_timeout",
        }

    def _create_success_checkpoint() -> dict[str, Any]:
        nonlocal checkpoint_result

        report_progress("Saving verified checkpoint")
        checkpoint_result = workspace.create_checkpoint(
            "Successful autonomous task completion"
        )

        if checkpoint_result.get("status") != "success":
            print(
                "❌ CHECKPOINT CREATION FAILED:"
            )
            print(
                checkpoint_result
            )

            raise RuntimeError(
                "Task verification succeeded, "
                "but automatic checkpoint creation failed."
            )

        print(
            "📦 CHECKPOINT CREATED:"
        )
        print(
            checkpoint_result
        )

        return checkpoint_result

    changed_since_build = False

    preview_url: str | None = None

    last_answer = ""

    steps_used = 0

    last_tool_signature: tuple[str, str] | None = None
    repeated_tool_count = 0
    pre_edit_read_count = 0
    PRE_EDIT_READ_LIMIT = 8

    MAX_REPAIR_ATTEMPTS = 3
    repair_attempts = 0
    self_healing_attempted = False
    last_failure_type: str | None = None

    # --------------------------------------------------------
    # MANDATORY INITIAL INSPECTION
    # --------------------------------------------------------

    print("🔎 Performing mandatory project inspection...")
    print("🔧 TOOL: list_files")

    try:
        inspection_result = _execute_agent_tool(
            "list_files",
            {},
            project_id,
        )

        print("✅ TOOL COMPLETE: list_files")

        if recovery_waiting_for_model:
            recovery_waiting_for_model = False

    except Exception as exc:
        print(
            "❌ INITIAL INSPECTION FAILED:",
            exc,
        )

        return {
            "status": "error",
            "message": (
                "Initial project inspection failed."
            ),
            "text": (
                f"Unable to inspect project: {exc}"
            ),
            "agent": "genesys",
            "steps": 0,
            "modifiedFiles": [],
            "buildAttempted": False,
            "buildPassed": False,
        }

    inspected = True
    
    # --------------------------------------------------------
    # M5 WORKSPACE CONTEXT
    # --------------------------------------------------------

    try:
        workspace_context = workspace.state()

        workspace_context_text = (
            "WORKSPACE CONTEXT\n\n"
            f"Project ID: "
            f"{workspace_context.get('projectId')}\n"
            f"Sandbox ID: "
            f"{workspace_context.get('sandboxId')}\n"
            f"Sandbox Name: "
            f"{workspace_context.get('sandboxName')}\n"
            f"State: "
            f"{workspace_context.get('state')}\n"
            f"Recoverable: "
            f"{workspace_context.get('recoverable')}\n"
            f"Project Root: "
            f"{workspace_context.get('projectRoot')}"
        )

        print("🧩 Workspace context:")
        print(workspace_context_text)

    except Exception as exc:
        workspace_context_text = (
            "WORKSPACE CONTEXT\n\n"
            "Workspace state could not be determined."
        )

        print(
            "⚠️ WORKSPACE CONTEXT FAILED:",
            exc,
        )

    messages.append(
        {
            "role": "system",
            "content": workspace_context_text,
        }
    )

    messages.append(
        {
        "role": "system",
        "content": (
            "MANDATORY PROJECT INSPECTION\n\n"
            "The agent has already performed the mandatory "
            "list_files inspection.\n\n"
            "Inspection result:\n"
            + _tool_result_text(
                inspection_result
            )
        ),
    }
)

    print("🔎 Project inspection complete.")

    # --------------------------------------------------------
    # M4 PROJECT INTELLIGENCE
    # --------------------------------------------------------

    print("🧠 Running project intelligence scan...")

    try:
        project_scan = scan_project(workspace)

        project_context = build_project_context(
            project_scan
        )

        targeted_files = target_project_files(
            prompt,
            project_scan,
        )

        print("🎯 Targeted files:")

        if targeted_files:
            for path in targeted_files:
                print(f"   - {path}")
        else:
            print("   - None detected")

        print("✅ Project intelligence complete.")
        print(project_context)

    except Exception as exc:
        project_scan = {
            "status": "error",
            "message": str(exc),
        }

        project_context = (
            "PROJECT CONTEXT\n\n"
            "Project intelligence scan failed. "
            "Continue using normal project inspection."
        )

        targeted_files = []

        print(
            "⚠️ PROJECT INTELLIGENCE FAILED:",
            exc,
        )

    messages.append(
        {
            "role": "system",
            "content": project_context,
        }
    )

    if targeted_files:
            targeting_context = (
            "TARGETED FILES\n\n"
            "These files are the most relevant starting points "
            "for the user's task. Inspect them first when "
            "appropriate. Do not assume they must be modified.\n\n"
            + "\n".join(
                f"- {path}"
                for path in targeted_files
            )
        )

            messages.append(
            {
                "role": "system",
                "content": targeting_context,
            }
        )

    # --------------------------------------------------------
    # M6.2 CHANGE PLAN
    # --------------------------------------------------------

    change_plan = _build_change_plan(
        task_understanding,
        targeted_files,
        project_scan,
    )

    print("📋 Change plan:")
    print(
        json.dumps(
            change_plan,
            indent=2,
            ensure_ascii=False,
        )
    )

    messages.append(
        {
            "role": "system",
            "content": (
                "CHANGE PLAN\n\n"
                "Before editing the project, follow this "
                "structured change plan.\n\n"
                + _safe_json(
                    change_plan
                )
                + "\n\n"
                "IMPORTANT:\n"
                "- Treat this as an execution plan, not permission "
                "to modify every listed file.\n"
                "- Inspect relevant files before editing.\n"
                "- Prefer the smallest correct change.\n"
                "- NEVER modify protected or generated files such as "
                "routeTree.gen.ts, *.gen.ts, or *.gen.tsx.\n"
                "- Do not modify unrelated files.\n"
                "- The orchestrator controls build and runtime "
                "verification."
            ),
        }
    )

    # --------------------------------------------------------
    # M6.3 CHANGE PLAN VALIDATION
    # --------------------------------------------------------

    plan_validation = _validate_change_plan(
        change_plan,
        project_scan,
    )

    print("🔍 Change plan validation:")
    print(
        json.dumps(
            plan_validation,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not plan_validation["valid"]:
        print(
            "❌ CHANGE PLAN INVALID:"
        )

        return {
            "status": "error",
            "message": (
                "Generated change plan failed validation."
            ),
            "planValidation": plan_validation,
            "taskUnderstanding": task_understanding,
            "changePlan": change_plan,
            "agent": "genesys",
            "steps": 0,
            "modifiedFiles": [],
            "buildAttempted": False,
            "buildPassed": False,
        }

        # --------------------------------------------------------
    # AGENT LOOP
    # --------------------------------------------------------

    for step in range(1, TOTAL_MAX_STEPS + 1):

        steps_used = step

        if time.monotonic() >= agent_deadline:
            return _agent_timeout_result()

        if verification_complete:
            print(
                "✅ Verification complete. Ending agent loop."
            )
            break

        # ----------------------------------------------------
        # COMPACTION
        # ----------------------------------------------------

        messages = _compact_messages(
            messages
        )

        print(
            f"🤖 Agent step {step}/{TOTAL_MAX_STEPS}"
        )

        # ----------------------------------------------------
        # FORCE BUILD AFTER FILE CHANGES
        # ----------------------------------------------------

        if changed_since_build and implementation_ready and not recovery_waiting_for_model:
            print(
                "📝 Files changed. "
                "Next action will be the mandatory build."
            )

            # --------------------------------------------------------
            # M6.4 EXECUTION VALIDATION
            # --------------------------------------------------------

            execution_validation = _validate_execution(
                change_plan,
                modified_files,
            )

            print("🛡️ Execution validation:")
            print(
                json.dumps(
                    execution_validation,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            if not execution_validation["valid"]:
                print(
                    "❌ EXECUTION VALIDATION FAILED:"
                )

                return {
                    "status": "error",
                    "message": (
                        "Agent execution failed "
                        "plan validation."
                    ),
                    "executionValidation": execution_validation,
                    "taskUnderstanding": task_understanding,
                    "changePlan": change_plan,
                    "planValidation": plan_validation,
                    "agent": "genesys",
                    "steps": steps_used,
                    "modifiedFiles": modified_files,
                    "buildAttempted": False,
                    "buildPassed": False,
                }

            # --------------------------------------------------------
            # M6.5 DIFF VERIFICATION
            # --------------------------------------------------------

            print(
                "🔎 Collecting Git diff..."
            )

            try:
                diff_result = workspace.get_diff()
            except Exception as exc:
                diff_result = {
                    "status": "error",
                    "success": False,
                    "error": str(exc),
                }

            diff_status = _result_status(
                diff_result
            )

            if diff_status != "success":
                print(
                    "❌ DIFF COLLECTION FAILED:"
                )

                return {
                    "status": "error",
                    "message": (
                        "Agent execution completed, "
                        "but Git diff collection failed."
                    ),
                    "diffResult": diff_result,
                    "taskUnderstanding": task_understanding,
                    "changePlan": change_plan,
                    "planValidation": plan_validation,
                    "executionValidation": execution_validation,
                    "agent": "genesys",
                    "steps": steps_used,
                    "modifiedFiles": modified_files,
                    "buildAttempted": False,
                    "buildPassed": False,
                }

            diff_summary = _summarize_diff(
                diff_result.get(
                    "diff",
                    "",
                )
            )

            diff_classification = _classify_diff_changes(
                diff_result.get(
                    "diff",
                    "",
                )
            )

            print(
                "🧭 Diff classification:"
            )

            print(
                json.dumps(
                    diff_classification,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            print(
                "📊 Diff summary:"
            )

            print(
                json.dumps(
                    diff_summary,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            diff_validation = _validate_diff(
                diff_summary,
                change_plan,
                diff_classification,
            )

            print(
                "🔍 Diff validation:"
            )

            print(
                json.dumps(
                    diff_validation,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            if not diff_validation["valid"]:
                print(
                    "❌ DIFF VALIDATION FAILED:"
                )

                return {
                    "status": "error",
                    "message": (
                        "Actual Git diff failed "
                        "change plan validation."
                    ),
                    "diffSummary": diff_summary,
                    "diffValidation": diff_validation,
                    "taskUnderstanding": task_understanding,
                    "changePlan": change_plan,
                    "planValidation": plan_validation,
                    "executionValidation": execution_validation,
                    "agent": "genesys",
                    "steps": steps_used,
                    "modifiedFiles": modified_files,
                    "buildAttempted": False,
                    "buildPassed": False,
                }

            print(
                "✅ DIFF VALIDATION PASSED"
            )

            print(
                "🏗️ Running mandatory build..."
            )

            print(
                "🔧 TOOL: run_build"
            )

            report_progress("Building application")
            build_attempted = True

            try:
                build_result = (
                    workspace.run_build()
                )

            except Exception as exc:
                build_result = {
                    "status": "error",
                    "error": str(exc),
                }

            print(
                "🏗️ BUILD RESULT:"
            )

            print(
                _tool_result_text(
                    build_result
                )
            )

            build_status = _result_status(
                build_result
            )

            # ------------------------------------------------
            # BUILD SUCCESS
            # ------------------------------------------------

            if build_status == "success":

                build_passed = True
                changed_since_build = False

                print(
                    "🏗️ BUILD PASSED"
                )

                validation = _validate_recovery(  
                    recovery_failure_type,
                    build_result,
                )

                recovery_report = _build_recovery_report(
                    attempted=True,
                    recovery_attempts=recovery_attempts,
                    failure={
                        "failureType": recovery_failure_type,
                    },
                    strategy=recovery_strategy,
                    validation=validation,
                    limits=_build_recovery_limits(
                        recovery_attempts,
                        max_recovery_attempts,
                    ),
                )

                print(
                    "♻️ Recovery validation:"
                )
                print(
                    validation
                )

                recovery_failure_type = None
                recovery_strategy = None    

            # ------------------------------------------------
            # BUILD FAILURE / SELF-HEALING
            # ------------------------------------------------

            else:

                build_passed = False

                print(
                    "❌ BUILD FAILED"
                )

                failure = _classify_failure(
                    build_result,
                    "mandatory build",
                )

                strategy = (
                    _build_recovery_strategy(
                        failure
                    )
                )

                limits = (
                    _build_recovery_limits(
                        recovery_attempts=recovery_attempts,
                        max_recovery_attempts=max_recovery_attempts,
                    )
                )

                if not _can_attempt_recovery(
                    recovery_attempts=recovery_attempts,
                    max_recovery_attempts=max_recovery_attempts,
                    strategy=strategy,
                ):

                    recovery_report = (
                        _build_recovery_report(
                            attempted=False,
                            recovery_attempts=recovery_attempts,
                            failure=failure,
                            strategy=strategy,
                            limits=limits,
                        )
                    )

                    return {
                        "status": "error",
                        "message": (
                            "Build failed and recovery "
                            "attempts are exhausted."
                        ),
                        "recovery": recovery_report,
                        "buildResult": build_result,
                    }

                should_rollback = (
                    _should_rollback_for_recovery(
                        strategy=strategy,
                        recovery_checkpoint_id=recovery_checkpoint_id,
                    )
                )

                rollback_result = None

                if should_rollback:
                    rollback_result = (
                        workspace.rollback_to_checkpoint(
                            recovery_checkpoint_id
                        )
                    )

                    if rollback_result.get("status") != "success":
                        return {
                            "status": "error",
                            "message": (
                                "Recovery could not start because "
                                "rollback to the known-good checkpoint "
                                "failed."
                            ),
                            "recovery": recovery_report,
                            "buildResult": build_result,
                            "rollback": rollback_result,
                        }

                    print(
                        "↩️ Rolled back to recovery checkpoint:"
                    )
                    print(
                        recovery_checkpoint_id
                    )

                recovery_attempts += 1

                recovery_failure_type = failure.get(
                    "failureType",
                    "unknown",
                )

                recovery_strategy = strategy

                recovery_context = (
                    _build_recovery_context(
                        failure=failure,
                        strategy=strategy,
                        task_understanding=task_understanding,
                        change_plan=change_plan,
                        failure_result=build_result,
                    )
                )

                last_recovery_prompt = (
                    _build_recovery_prompt(
                        recovery_context
                    )
                )
                recovery_waiting_for_model = True

                recovery_report = (
                    _build_recovery_report(
                        attempted=True,
                        recovery_attempts=recovery_attempts,
                        failure=failure,
                        strategy=strategy,
                        limits=_build_recovery_limits(
                            recovery_attempts,
                            max_recovery_attempts,
                        ),
                    )
                )
                if recovery_report["exhausted"]:
                        return {
                            "status": "error",
                            "message": (
                                "Build failed and recovery "
                                "attempts are exhausted."
                            ),
                            "recovery": recovery_report,
                            "buildResult": build_result,
                        }

                print(
                    "♻️ Recovery prepared:"
                )

                print(
                    json.dumps(
                        recovery_report,
                        indent=2,
                        ensure_ascii=False,
                    )
                )

                print(
                    "\n🛠️ Recovery Prompt:\n"
                )

                print(
                    last_recovery_prompt
                )

                # --------------------------------------------
                # MAX REPAIR ATTEMPTS REACHED
                # --------------------------------------------

                if (
                    repair_attempts
                    >= MAX_REPAIR_ATTEMPTS
                ):

                    print(
                        "❌ MAX SELF-HEALING "
                        "ATTEMPTS REACHED"
                    )

                    return {
                        "status": "error",
                        "message": (
                            "Build failed after maximum "
                            "self-healing attempts."
                        ),
                        "text": (
                            last_answer
                            or (
                                "Build could not be "
                                "repaired."
                            )
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "previewUrl": preview_url,
                        "errorType": "build",
                        "repairAttempts": repair_attempts,
                        "maxRepairAttempts": (
                            MAX_REPAIR_ATTEMPTS
                        ),
                        "selfHealing": {
                            "attempted": (
                                self_healing_attempted
                            ),
                            "attempts": (
                                repair_attempts
                            ),
                            "maxAttempts": (
                                MAX_REPAIR_ATTEMPTS
                            ),
                            "recovered": False,
                            "failureType": (
                                last_failure_type
                            ),
                        },
                    }

                # --------------------------------------------
                # SEND BUILD FAILURE TO MODEL
                # --------------------------------------------

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The mandatory build failed.\n\n"
                            f"SELF-HEALING ATTEMPT: "
                            f"{repair_attempts}/"
                            f"{MAX_REPAIR_ATTEMPTS}\n\n"
                            "FAILURE TYPE: BUILD\n\n"
                            "BUILD RESULT:\n"
                            + _tool_result_text(
                                build_result
                            )
                            + "\n\n"
                            "Inspect the build error and "
                            "repair the project. After "
                            "repairing the files, the "
                            "orchestrator will automatically "
                            "rebuild the application."
                        ),
                    }
                )

                continue

        # ----------------------------------------------------
        # START PREVIEW AFTER SUCCESSFUL BUILD
        # ----------------------------------------------------

        if (
            build_attempted
            and build_passed
            and not preview_started
            and not recovery_waiting_for_model
        ):

            print(
                "🌐 Starting mandatory application preview..."
            )

            print(
                "🔧 TOOL: start_preview"
            )

            try:

                report_progress("Starting preview")
                preview_result = (
                    workspace.start_preview()
                )

            except Exception as exc:

                preview_result = {
                    "status": "error",
                    "error": str(exc),
                }

            print(
                "🌐 PREVIEW RESULT:"
            )

            print(
                _tool_result_text(
                    preview_result
                )
            )

            preview_status = _result_status(
                preview_result
            )

            # ------------------------------------------------
            # PREVIEW SUCCESS
            # ------------------------------------------------

            if preview_status == "success":

                preview_started = True

                preview_url = (
                    preview_result.get("url")
                    if isinstance(
                        preview_result,
                        dict,
                    )
                    else None
                )

                print(
                    "🌐 PREVIEW STARTED"
                )

            # ------------------------------------------------
            # PREVIEW FAILURE / SELF-HEALING
            # ------------------------------------------------

            else:

                print(
                    "❌ PREVIEW FAILED"
                )

                repair_attempts += 1
                self_healing_attempted = True
                last_failure_type = "preview"

                print(
                    f"🔧 SELF-HEALING ATTEMPT "
                    f"{repair_attempts}/"
                    f"{MAX_REPAIR_ATTEMPTS}"
                )

                # --------------------------------------------
                # MAX REPAIR ATTEMPTS REACHED
                # --------------------------------------------

                if (
                    repair_attempts
                    >= MAX_REPAIR_ATTEMPTS
                ):

                    print(
                        "❌ MAX SELF-HEALING "
                        "ATTEMPTS REACHED"
                    )

                    return {
                        "status": "error",
                        "message": (
                            "Application preview failed "
                            "after maximum self-healing "
                            "attempts."
                        ),
                        "text": (
                            last_answer
                            or (
                                "Application preview "
                                "could not be started."
                            )
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "previewUrl": preview_url,
                        "errorType": "preview",
                        "repairAttempts": repair_attempts,
                        "maxRepairAttempts": (
                            MAX_REPAIR_ATTEMPTS
                        ),
                        "selfHealing": {
                            "attempted": (
                                self_healing_attempted
                            ),
                            "attempts": (
                                repair_attempts
                            ),
                            "maxAttempts": (
                                MAX_REPAIR_ATTEMPTS
                            ),
                            "recovered": False,
                            "failureType": (
                                last_failure_type
                            ),
                        },
                    }

                # --------------------------------------------
                # RESET PREVIEW STATE
                # --------------------------------------------

                preview_started = False
                preview_url = None
                browser_verified = False

                try:
                    stop_browser(project_id)
                except Exception:
                    pass

                # --------------------------------------------
                # SEND PREVIEW FAILURE TO MODEL
                # --------------------------------------------

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The application build passed, "
                            "but the application preview "
                            "failed to start.\n\n"
                            f"SELF-HEALING ATTEMPT: "
                            f"{repair_attempts}/"
                            f"{MAX_REPAIR_ATTEMPTS}\n\n"
                            "FAILURE TYPE: PREVIEW\n\n"
                            "PREVIEW RESULT:\n"
                            + _tool_result_text(
                                preview_result
                            )
                            + "\n\n"
                            "Inspect the project and repair "
                            "the application startup or "
                            "runtime problem. After repairing "
                            "the files, the orchestrator will "
                            "rebuild and attempt the preview "
                            "again."
                        ),
                    }
                )

                continue

        # ----------------------------------------------------
        # BROWSER VERIFICATION
        # ----------------------------------------------------

        if (
            preview_started
            and not browser_verified
            and preview_url
            and not recovery_waiting_for_model
        ):

            print(
                "🧪 Running browser verification..."
            )

            report_progress("Verifying in browser")
            screenshot_result = None
            console_result = None

            try:
                print(
                    "🔧 TOOL: browser_screenshot"
                )

                screenshot_result = execute_tool(
                    "browser_screenshot",
                    {},
                    project_id=project_id,
                )

                print(
                    "✅ TOOL COMPLETE: browser_screenshot"
                )

                print(
                    "🔧 TOOL: browser_console"
                )

                console_result = execute_tool(
                    "browser_console",
                    {},
                    project_id=project_id,
                )

                print(
                    "✅ TOOL COMPLETE: browser_console"
                )

                runtime_errors = False

                if isinstance(
                    console_result,
                    dict,
                ):
                    runtime_errors = bool(
                        console_result.get(
                            "hasRuntimeErrors",
                            False,
                        )
                    )

                if runtime_errors:

                    page_errors = []
                    console_errors = []
                    network_errors = []

                    if isinstance(
                        console_result,
                        dict,
                    ):
                        page_errors = (
                            console_result.get(
                                "pageErrors",
                                [],
                            )
                        )

                        console_errors = (
                            console_result.get(
                                "consoleErrors",
                                [],
                            )
                        )

                        network_errors = (
                            console_result.get(
                                "networkErrors",
                                [],
                            )
                        )

                    raise RuntimeError(
                        "Browser runtime errors detected.\n\n"
                        "PAGE ERRORS:\n"
                        + json.dumps(
                            page_errors,
                            indent=2,
                            ensure_ascii=False,
                        )
                        + "\n\n"
                        "CONSOLE ERRORS:\n"
                        + json.dumps(
                            console_errors,
                            indent=2,
                            ensure_ascii=False,
                        )
                        + "\n\n"
                        "NETWORK ERRORS:\n"
                        + json.dumps(
                            network_errors,
                            indent=2,
                            ensure_ascii=False,
                        )
                    )

                if project_id != PROJECT_ID_DEFAULT:
                    report_progress("Checking visual layout")
                    quality = get_browser(project_id).visual_quality(
                        allow_unstyled=bool(re.search(r"\b(unstyled|browser[- ]default|no css|plain html)\b", prompt, re.I))
                    )
                    if quality['status'] != 'success':
                        raise RuntimeError(
                            "Visual quality verification failed. Keep the requested behavior and theme; "
                            "repair the application stylesheet and layout before completing.\n"
                            + json.dumps(quality, ensure_ascii=False)
                        )

                browser_verified = True
                verification_complete = True

                print(
                    "🧪 BROWSER VERIFICATION PASSED"
                )

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Browser verification "
                            "completed successfully.\n\n"
                            "SCREENSHOT RESULT:\n"
                            + _tool_result_text(
                                screenshot_result
                            )
                            + "\n\n"
                            "CONSOLE RESULT:\n"
                            + _tool_result_text(
                                console_result
                            )
                        ),
                    }
                )

                if verification_complete:

                    _create_success_checkpoint()

                print(
                        "🤖 AGENT RESULT: success"
                    )

                return {
                        "status": "success",
                        "message": (
                            "Agent completed the requested change "
                            "and verification successfully."
                        ),
                        "text": (
                            last_answer
                            or "Agent completed the requested change."
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "previewUrl": preview_url,
                        "checkpoint": checkpoint_result,
                }

            except Exception as exc:

                repair_attempts += 1
                self_healing_attempted = True
                last_failure_type = (
                    "browser_runtime"
                )
                recovery_waiting_for_model = True

                browser_verified = False

                print(
                    "❌ BROWSER VERIFICATION FAILED:",
                    exc,
                )

                print(
                    f"🔧 SELF-HEALING ATTEMPT "
                    f"{repair_attempts}/"
                    f"{MAX_REPAIR_ATTEMPTS}"
                )

                # --------------------------------------------
                # MAX REPAIR ATTEMPTS
                # --------------------------------------------

                if (
                    repair_attempts
                    >= MAX_REPAIR_ATTEMPTS
                ):

                    print(
                        "❌ MAX SELF-HEALING "
                        "ATTEMPTS REACHED"
                    )

                    return {
                        "status": "error",
                        "message": (
                            "Browser verification failed "
                            "after maximum self-healing "
                            "attempts."
                        ),
                        "text": (
                            last_answer
                            or (
                                "Browser verification "
                                "could not be repaired."
                            )
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "previewUrl": preview_url,
                        "errorType": "browser_runtime",
                        "repairAttempts": repair_attempts,
                        "maxRepairAttempts": (
                            MAX_REPAIR_ATTEMPTS
                        ),
                        "selfHealing": {
                            "attempted": (
                                self_healing_attempted
                            ),
                            "attempts": (
                                repair_attempts
                            ),
                            "maxAttempts": (
                                MAX_REPAIR_ATTEMPTS
                            ),
                            "recovered": False,
                            "failureType": (
                                last_failure_type
                            ),
                        },
                    }

                # --------------------------------------------
                # RESET BROWSER / PREVIEW STATE
                # --------------------------------------------

                preview_started = False
                preview_url = None
                browser_verified = False

                try:
                    stop_browser(project_id)
                except Exception:
                    pass

                # --------------------------------------------
                # SEND FAILURE BACK TO MODEL
                # --------------------------------------------

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Browser verification failed.\n\n"
                            f"SELF-HEALING ATTEMPT: "
                            f"{repair_attempts}/"
                            f"{MAX_REPAIR_ATTEMPTS}\n\n"
                            "FAILURE TYPE: "
                            "BROWSER_RUNTIME\n\n"
                            "ERROR:\n"
                            + str(exc)
                            + "\n\n"
                            "SCREENSHOT RESULT:\n"
                            + _tool_result_text(
                                screenshot_result
                            )
                            + "\n\n"
                            "CONSOLE RESULT:\n"
                            + _tool_result_text(
                                console_result
                            )
                            + "\n\n"
                            "Inspect the application and "
                            "repair the runtime or UI problem. "
                            "After repairing the files, the "
                            "orchestrator will automatically "
                            "rebuild, restart the preview, "
                            "and run browser verification again."
                        ),
                    }
                )

                continue

        # ----------------------------------------------------
        # RESERVE THE LAST STEPS FOR MANDATORY VERIFICATION AND REPAIR.
        # The model must not spend this reserve on new exploration after its
        # normal implementation budget has ended.
        if step > MAX_STEPS and changed_since_build and not implementation_ready and not recovery_waiting_for_model:
            return {
                "status": "error",
                "message": "Implementation did not finish within the step budget. Your partial files are saved; retry to finish the application.",
                "modifiedFiles": modified_files,
                "buildPassed": False,
                "browserVerified": False,
                "steps": steps_used,
            }

        if (
            step > MAX_STEPS
            and not changed_since_build
            and not recovery_waiting_for_model
            and not last_failure_type
        ):
            print(
                "⏹️ Implementation step budget ended; "
                "no pending changes or recovery remain."
            )
            break

        # SUCCESS CONDITION
        # ----------------------------------------------------

        if (
            inspected
            and build_attempted
            and build_passed
            and preview_started
            and browser_verified
        ):

            _create_success_checkpoint()

            print(
                 "🤖 AGENT RESULT: success"
            )

            return {
                "status": "success",
                "message": (
                    "Task completed successfully."
                ),
                "text": (
                    last_answer
                    or "Task completed successfully."
                ),
                "agent": "genesys",
                "provider": active_provider_name,
                "model": (
                    GEMINI_MODEL
                    if active_provider_name == "gemini"
                    else MODEL
                ),
                "steps": steps_used,
                "modifiedFiles": modified_files,
                "buildAttempted": build_attempted,
                "buildPassed": build_passed,
                "previewStarted": preview_started,
                "browserVerified": browser_verified,
                "previewUrl": preview_url,
                "checkpoint": checkpoint_result,
            }

        # ----------------------------------------------------
        # M7 RECOVERY PROMPT INJECTION
        # ----------------------------------------------------

        if last_recovery_prompt:

            print(
                "♻️ Injecting recovery prompt..."
            )

            messages.append(
                {
                    "role": "system",
                    "content": (
                        last_recovery_prompt
                    ),
                }
            )

            last_recovery_prompt = None

        # ----------------------------------------------------
        # ASK AI PROVIDER FOR NEXT ACTION
        # ----------------------------------------------------

        try:

            response = provider.generate(
                messages,
                TOOLS,
            )

        except Exception as exc:

            error_text = str(exc)

            print(
                "❌ AI REQUEST FAILED:"
            )
            print(
                error_text
            )

            import traceback

            traceback.print_exc()

            # ------------------------------------------------
            # PROVIDER FALLBACK: GROQ <-> GEMINI
            # ------------------------------------------------

            if active_provider_name == "groq":

                print(
                    "⚠️ Groq failed. Falling back to Gemini..."
                )

                try:

                    fallback_provider = GeminiProvider(
                        model=GEMINI_MODEL,
                    )

                    # The previous provider may have produced function calls
                    # that do not contain Gemini 3 thought signatures.
                    # Do not replay those provider-specific tool turns into
                    # Gemini. Preserve normal conversation text and let Gemini
                    # issue fresh tool calls with its own signatures.
                    fallback_messages = []

                    for message in messages:
                        role = message.get(
                            "role"
                        )

                        if role == "tool":
                            continue

                        if role == "assistant":
                            cleaned_message = dict(
                                message
                            )

                            cleaned_message.pop(
                                "tool_calls",
                                None,
                            )

                            fallback_messages.append(
                                cleaned_message
                            )
                            continue

                        fallback_messages.append(
                            dict(message)
                        )

                    if time.monotonic() >= agent_deadline:
                        return _agent_timeout_result()

                    response = fallback_provider.generate(
                        fallback_messages,
                        TOOLS,
                    )

                    print(
                        "✅ Gemini fallback succeeded; using Gemini for the rest of this run."
                    )
                    # Keep subsequent Gemini calls on Gemini-compatible history.
                    messages = fallback_messages
                    provider = fallback_provider
                    active_provider_name = FALLBACK_PROVIDER

                except Exception as fallback_exc:

                    fallback_error = str(
                        fallback_exc
                    )

                    print(
                        "❌ Gemini fallback also failed:"
                    )
                    print(
                        fallback_error
                    )

                    return {
                        "status": "error",
                        "message": (
                            "AI provider request failed."
                        ),
                        "text": (
                            f"Groq failed: {error_text}\n"
                            f"Gemini fallback failed: "
                            f"{fallback_error}"
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "errorType": "ai_request",
                    }

            else:

                print(
                    "⚠️ Gemini failed. Falling back to Groq..."
                )

                try:
                    fallback_provider = GroqProvider(
                        model=MODEL,
                    )

                    if time.monotonic() >= agent_deadline:
                        return _agent_timeout_result()

                    response = fallback_provider.generate(
                        messages,
                        TOOLS,
                    )

                    provider = fallback_provider
                    active_provider_name = "groq"

                    print(
                        "✅ Groq fallback succeeded; using Groq for the rest of this run."
                    )

                except Exception as fallback_exc:
                    fallback_error = str(fallback_exc)

                    print(
                        "❌ Groq fallback also failed:"
                    )
                    print(fallback_error)

                    return {
                        "status": "error",
                        "message": (
                            "AI provider request failed."
                        ),
                        "text": (
                            f"Gemini failed: {error_text}\n"
                            f"Groq fallback failed: {fallback_error}"
                        ),
                        "agent": "genesys",
                        "provider": active_provider_name,
                        "model": (
                            GEMINI_MODEL
                            if active_provider_name == "gemini"
                            else MODEL
                        ),
                        "steps": steps_used,
                        "modifiedFiles": modified_files,
                        "buildAttempted": build_attempted,
                        "buildPassed": build_passed,
                        "previewStarted": preview_started,
                        "browserVerified": browser_verified,
                        "errorType": "ai_request",
                    }

        # ----------------------------------------------------
        if time.monotonic() >= agent_deadline:
            return _agent_timeout_result()

        # NORMALIZED RESPONSE
        # ----------------------------------------------------

        last_answer = (
            response.text
            if response.text
            else last_answer
        )

        tool_calls = (
            response.tool_calls
            or []
        )

        # ----------------------------------------------------
        # NO TOOL CALL
        # ----------------------------------------------------

        if not tool_calls:

            if changed_since_build:
                implementation_ready = True
                recovery_waiting_for_model = False
                continue

            # If the application has already passed all
            # mandatory checks, return success.
            if (
                build_attempted
                and build_passed
                and preview_started
                and browser_verified
            ):

                _create_success_checkpoint()

                print(
                    "🤖 AGENT RESULT: success"
                )

                return {
                    "status": "success",
                    "message": (
                        "Task completed successfully."
                    ),
                    "text": (
                        last_answer
                        or "Task completed successfully."
                    ),
                    "agent": "genesys",
                    "provider": active_provider_name,
                    "model": (
                        GEMINI_MODEL
                        if active_provider_name == "gemini"
                        else MODEL
                    ),
                    "steps": steps_used,
                    "modifiedFiles": modified_files,
                    "buildAttempted": build_attempted,
                    "buildPassed": build_passed,
                    "previewStarted": preview_started,
                    "browserVerified": browser_verified,
                    "previewUrl": preview_url,
                    "checkpoint": checkpoint_result,
                }

            # Otherwise the model stopped before completing
            # the required workflow.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Continue the task. "
                        "You have not yet completed the "
                        "required implementation and "
                        "verification workflow."
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # ASSISTANT TOOL MESSAGE
        # ----------------------------------------------------

        assistant_message = (
            _build_assistant_tool_message(
                response
            )
        )

        messages.append(
            assistant_message
        )

        # ----------------------------------------------------
        # EXECUTE TOOL CALLS
        # ----------------------------------------------------

        loop_warning: str | None = None

        for tool_call in tool_calls:

            if time.monotonic() >= agent_deadline:
                return _agent_timeout_result()

            tool_name = tool_call.name

            arguments = (
                tool_call.arguments
                if isinstance(
                    tool_call.arguments,
                    dict,
                )
                else {}
            )

            # ----------------------------------------------
            # REPETITION DETECTION
            # ----------------------------------------------

            tool_signature = (
                tool_name,
                json.dumps(
                    arguments,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                ),
            )

            if tool_signature == last_tool_signature:
                repeated_tool_count += 1
            else:
                last_tool_signature = tool_signature
                repeated_tool_count = 1

            if repeated_tool_count >= 3:
                print(
                    "⚠️ Repeated tool call detected: "
                    f"{tool_name} ({repeated_tool_count} times)"
                )
                loop_warning = (
                    f"You repeated the same {tool_name} call. "
                    "Use the result already in the conversation and "
                    "continue with implementation or verification. "
                    "Do not make the identical call again."
                )
                repeated_tool_count = 0

            # ----------------------------------------------
            # LIFECYCLE TOOLS ARE ORCHESTRATOR CONTROLLED
            # ----------------------------------------------

            inspection_limit_hit = False
            if tool_name == "read_file" and not modified_files:
                pre_edit_read_count += 1
                if pre_edit_read_count == 4:
                    loop_warning = (
                        "You have inspected four files. Stop exploring and "
                        "make the first implementation change now. You can "
                        "inspect another file later if the edit requires it."
                    )
                elif pre_edit_read_count > PRE_EDIT_READ_LIMIT:
                    inspection_limit_hit = True
                    loop_warning = (
                        "The pre-edit inspection limit has been reached. "
                        "Use the information already available and make "
                        "the first implementation change now."
                    )
                    result = {
                        "status": "error",
                        "error": (
                            "Pre-edit inspection limit reached. "
                            "Begin implementation with the files already read."
                        ),
                        "tool": tool_name,
                    }

            if inspection_limit_hit:
                print(
                    "⚠️ Blocked additional pre-edit file read; "
                    "inspection limit reached."
                )
            elif tool_name in {
                "run_build",
                "start_preview",
                "stop_preview",
            }:

                result = {
                    "status": "error",
                    "error": (
                        f"{tool_name} is controlled by "
                        "the GeneSys orchestrator and "
                        "must not be called by the model."
                    ),
                }

            else:

                print(
                    f"🔧 TOOL: {tool_name}"
                )

                try:

                    report_progress("Editing files" if tool_name in {"edit_file", "write_file"} else "Inspecting project")
                    result = _execute_agent_tool(
                        tool_name,
                        arguments,
                        project_id,
                    )

                    print(
                        "✅ TOOL COMPLETE:",
                        tool_name,
                    )

                    if recovery_waiting_for_model and tool_name in {"edit_file", "write_file", "create_file"} and isinstance(result, dict) and result.get("status") == "success":
                        recovery_waiting_for_model = False

                except Exception as exc:

                    print(
                        "❌ TOOL FAILED:",
                        tool_name,
                        exc,
                    )

                    result = {
                        "status": "error",
                        "error": str(exc),
                        "tool": tool_name,
                    }

            # ----------------------------------------------
            # TRACK MODIFIED FILES
            # ----------------------------------------------

            if tool_name in {
                "write_file",
                "create_file",
                "edit_file",
            } and isinstance(result, dict) and result.get("status") == "success":

                changed_since_build = True
                implementation_ready = False

                # Any file change invalidates the previous
                # build, preview, and browser verification.
                build_passed = False
                preview_started = False
                preview_url = None
                browser_verified = False

                # Force a fresh Playwright session after
                # a repair so stale pages and console errors
                # cannot affect the next verification cycle.
                try:
                    stop_browser(project_id)
                except Exception:
                    pass

                file_path = (
                    arguments.get("path")
                    or arguments.get("file_path")
                    or arguments.get("filename")
                )

            # ----------------------------------------------
            # TRACK MODIFIED FILES
            # ----------------------------------------------

            if tool_name in {
                "write_file",
                "create_file",
                "edit_file",
            } and isinstance(result, dict) and result.get("status") == "success":

                changed_since_build = True

                file_path = (
                    arguments.get("path")
                    or arguments.get("file_path")
                    or arguments.get("filename")
                )

                if file_path:
                    if (
                        file_path
                        not in modified_files
                    ):
                        modified_files.append(
                            file_path
                        )

                # If a tool reports changed files,
                # collect those too.
                if isinstance(
                    result,
                    dict,
                ):

                    changed = (
                        result.get(
                            "modifiedFiles"
                        )
                        or result.get(
                            "modified_files"
                        )
                        or []
                    )

                    if isinstance(
                        changed,
                        list,
                    ):
                        for path in changed:
                            if (
                                path
                                not in modified_files
                            ):
                                modified_files.append(
                                    path
                                )

            # ----------------------------------------------
            # ADD TOOL RESULT TO HISTORY
            # ----------------------------------------------

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": _tool_result_text(
                        result
                    ),
                }
            )

        # ----------------------------------------------------
        # LOOP WARNING AFTER TOOL RESULTS
        # ----------------------------------------------------

        if loop_warning:
            messages.append(
                {
                    "role": "user",
                    "content": loop_warning,
                }
            )

        # ----------------------------------------------------
        # COMPACT AFTER TOOL EXECUTION
        # ----------------------------------------------------

        messages = _compact_messages(
            messages
        )

    # ========================================================
    # VERIFICATION COMPLETE
    # ========================================================

    if verification_complete:
        _create_success_checkpoint()

        print(
            "🤖 AGENT RESULT: success"
        )

        return {
            "status": "success",
            "message": (
                "Agent completed the requested change "
                "and verification successfully."
            ),
            "text": (
                last_answer
                or "Agent completed the requested change."
            ),
            "agent": "genesys",
            "provider": active_provider_name,
            "model": (
                GEMINI_MODEL
                if active_provider_name == "gemini"
                else MODEL
            ),
            "steps": steps_used,
            "modifiedFiles": modified_files,
            "buildAttempted": build_attempted,
            "buildPassed": build_passed,
            "previewStarted": preview_started,
            "browserVerified": browser_verified,
            "previewUrl": preview_url,
        }

    # ========================================================
    # MAX STEPS REACHED
    # ========================================================

    print(
        "🤖 AGENT RESULT: max_steps_reached"
    )

    return {
        "status": "error",
        "message": (
            "Agent reached the maximum number "
            "of steps before completing verification."
        ),
        "text": (
            last_answer
            or "Agent reached the maximum step limit."
        ),
        "agent": "genesys",
        "provider": active_provider_name,
        "model": (
            GEMINI_MODEL
            if active_provider_name == "gemini"
            else MODEL
        ),
        "steps": steps_used,
        "modifiedFiles": modified_files,
        "buildAttempted": build_attempted,
        "buildPassed": build_passed,
        "previewStarted": preview_started,
        "browserVerified": browser_verified,
        "previewUrl": preview_url,
    }
