import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from .tools import TOOLS, execute_tool


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL = os.getenv(
    "GENESYS_MODEL",
    "openai/gpt-oss-120b",
)

MAX_STEPS = 18

# Moderate output budget so there is room for conversation,
# tool schemas, and generated file contents under the current
# organization TPM limit.
MAX_COMPLETION_TOKENS = 3200

MAX_GROQ_RETRIES = 4


# ============================================================
# CONTEXT COMPACTION
# ============================================================

SYSTEM_MAX_CHARS = 6000
USER_MAX_CHARS = 3500

READ_FILE_MAX_CHARS = 3000
BUILD_OUTPUT_MAX_CHARS = 4500
LIST_FILES_MAX_CHARS = 2200
GENERIC_TOOL_MAX_CHARS = 1800

TOOL_ARGUMENT_MAX_CHARS = 1400

MAX_CONVERSATION_CHARS = 10000


# ============================================================
# TOOL INDEX
# ============================================================

TOOL_BY_NAME: dict[
    str,
    dict[str, Any],
] = {
    tool["function"]["name"]: tool
    for tool in TOOLS
}


# ============================================================
# GROQ CLIENT
# ============================================================

def get_client() -> Groq:
    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from the environment."
        )

    return Groq(
        api_key=api_key
    )


# ============================================================
# TEXT COMPACTION
# ============================================================

def compact_text(
    value: Any,
    max_chars: int,
) -> str:
    text = (
        value
        if isinstance(value, str)
        else str(value)
    )

    if len(text) <= max_chars:
        return text

    if max_chars <= 100:
        return text[:max_chars]

    head = max_chars // 2
    tail = max_chars - head

    return (
        text[:head]
        + "\n\n[... GeneSys context compacted ...]\n\n"
        + text[-tail:]
    )


# ============================================================
# TOOL RESULT COMPACTION
# ============================================================

def compact_tool_result(
    content: str,
) -> str:
    try:
        data = json.loads(
            content
        )
    except Exception:
        return compact_text(
            content,
            GENERIC_TOOL_MAX_CHARS,
        )

    if not isinstance(
        data,
        dict,
    ):
        return compact_text(
            content,
            GENERIC_TOOL_MAX_CHARS,
        )

    # --------------------------------------------------------
    # read_file
    # --------------------------------------------------------

    if (
        "content" in data
        and "path" in data
    ):
        result = dict(data)

        result["content"] = compact_text(
            data.get(
                "content",
                "",
            ),
            READ_FILE_MAX_CHARS,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # list_files
    # --------------------------------------------------------

    if "files" in data:
        result = dict(data)

        files = data.get(
            "files",
            [],
        )

        if isinstance(
            files,
            list,
        ):
            result["files"] = files[:140]

        tree = data.get(
            "tree"
        )

        if isinstance(
            tree,
            dict,
        ):
            tree_copy = dict(
                tree
            )

            if isinstance(
                tree_copy.get("routes"),
                list,
            ):
                tree_copy["routes"] = (
                    tree_copy["routes"][:70]
                )

            if isinstance(
                tree_copy.get("components"),
                list,
            ):
                tree_copy["components"] = (
                    tree_copy["components"][:70]
                )

            result["tree"] = tree_copy

        return compact_text(
            json.dumps(
                result,
                ensure_ascii=False,
            ),
            LIST_FILES_MAX_CHARS,
        )

    # --------------------------------------------------------
    # run_build
    # --------------------------------------------------------

    if "output" in data:
        result = dict(data)

        result["output"] = compact_text(
            data.get(
                "output",
                "",
            ),
            BUILD_OUTPUT_MAX_CHARS,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # generic
    # --------------------------------------------------------

    return compact_text(
        json.dumps(
            data,
            ensure_ascii=False,
        ),
        GENERIC_TOOL_MAX_CHARS,
    )


# ============================================================
# ASSISTANT TOOL MESSAGE
# ============================================================

def build_assistant_tool_message(
    message: Any,
) -> dict[str, Any]:
    """
    Explicitly reconstruct the assistant tool-call message.

    Do not use model_dump() because SDK responses can contain
    extra fields that should not be replayed to Groq.
    """

    tool_calls = (
        getattr(
            message,
            "tool_calls",
            None,
        )
        or []
    )

    return {
        "role": "assistant",
        "content": (
            message.content
            if message.content
            else ""
        ),
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in tool_calls
        ],
    }


# ============================================================
# ASSISTANT TOOL COMPACTION
# ============================================================

def compact_assistant_message(
    message: dict[str, Any],
) -> dict[str, Any]:
    result = dict(
        message
    )

    tool_calls = result.get(
        "tool_calls"
    )

    if not isinstance(
        tool_calls,
        list,
    ):
        return result

    compacted_calls = []

    for call in tool_calls:
        call_copy = dict(
            call
        )

        function = call.get(
            "function"
        )

        if isinstance(
            function,
            dict,
        ):
            function_copy = dict(
                function
            )

            name = function.get(
                "name"
            )

            arguments = function.get(
                "arguments",
                "{}",
            )

            # write_file can contain thousands of characters.
            if name == "write_file":
                try:
                    parsed = json.loads(
                        arguments
                    )

                    if isinstance(
                        parsed,
                        dict,
                    ):
                        function_copy[
                            "arguments"
                        ] = json.dumps(
                            {
                                "filename": parsed.get(
                                    "filename"
                                ),
                                "content": (
                                    "[file contents omitted "
                                    "after execution]"
                                ),
                            },
                            ensure_ascii=False,
                        )
                    else:
                        function_copy[
                            "arguments"
                        ] = compact_text(
                            arguments,
                            TOOL_ARGUMENT_MAX_CHARS,
                        )

                except Exception:
                    function_copy[
                        "arguments"
                    ] = compact_text(
                        arguments,
                        TOOL_ARGUMENT_MAX_CHARS,
                    )

            else:
                function_copy[
                    "arguments"
                ] = compact_text(
                    arguments,
                    TOOL_ARGUMENT_MAX_CHARS,
                )

            call_copy[
                "function"
            ] = function_copy

        compacted_calls.append(
            call_copy
        )

    result[
        "tool_calls"
    ] = compacted_calls

    return result


# ============================================================
# PREPARE MESSAGES
# ============================================================

def prepare_messages_for_groq(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Prepare a compact but structurally valid conversation.

    We preserve:
      - system prompt
      - original user request
      - newest complete interaction blocks

    We compact:
      - source file contents
      - build output
      - file lists
      - write_file arguments
    """

    prepared: list[
        dict[str, Any]
    ] = []

    for message in messages:
        role = message.get(
            "role"
        )

        # ----------------------------------------------------
        # SYSTEM
        # ----------------------------------------------------

        if role == "system":
            copy = dict(
                message
            )

            copy["content"] = compact_text(
                message.get(
                    "content",
                    "",
                ),
                SYSTEM_MAX_CHARS,
            )

            prepared.append(
                copy
            )

            continue

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        if role == "user":
            copy = dict(
                message
            )

            copy["content"] = compact_text(
                message.get(
                    "content",
                    "",
                ),
                USER_MAX_CHARS,
            )

            prepared.append(
                copy
            )

            continue

        # ----------------------------------------------------
        # ASSISTANT
        # ----------------------------------------------------

        if role == "assistant":
            if message.get(
                "tool_calls"
            ):
                prepared.append(
                    compact_assistant_message(
                        message
                    )
                )
            else:
                copy = dict(
                    message
                )

                copy["content"] = compact_text(
                    message.get(
                        "content",
                        "",
                    ),
                    2200,
                )

                prepared.append(
                    copy
                )

            continue

        # ----------------------------------------------------
        # TOOL
        # ----------------------------------------------------

        if role == "tool":
            copy = dict(
                message
            )

            copy["content"] = compact_tool_result(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )

            prepared.append(
                copy
            )

            continue

        prepared.append(
            dict(message)
        )

    # --------------------------------------------------------
    # Fast path
    # --------------------------------------------------------

    total_chars = sum(
        len(
            str(
                message.get(
                    "content",
                    "",
                )
            )
        )
        + len(
            str(
                message.get(
                    "tool_calls",
                    "",
                )
            )
        )
        for message in prepared
    )

    if total_chars <= MAX_CONVERSATION_CHARS:
        return prepared

    # --------------------------------------------------------
    # Preserve first system and first user messages.
    # --------------------------------------------------------

    base: list[
        dict[str, Any]
    ] = []

    first_system = next(
        (
            message
            for message in prepared
            if message.get("role")
            == "system"
        ),
        None,
    )

    first_user = next(
        (
            message
            for message in prepared
            if message.get("role")
            == "user"
        ),
        None,
    )

    if first_system is not None:
        base.append(
            first_system
        )

    if first_user is not None:
        base.append(
            first_user
        )

    base_ids = {
        id(message)
        for message in base
    }

    remaining = [
        message
        for message in prepared
        if id(message)
        not in base_ids
    ]

    remaining_chars = (
        MAX_CONVERSATION_CHARS
        - sum(
            len(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )
            for message in base
        )
    )

    # --------------------------------------------------------
    # Group messages into complete turns.
    # --------------------------------------------------------

    blocks: list[
        list[dict[str, Any]]
    ] = []

    current_block: list[
        dict[str, Any]
    ] = []

    for message in remaining:
        role = message.get(
            "role"
        )

        # A new assistant/user message begins a new turn block.
        if (
            role in {
                "assistant",
                "user",
            }
            and current_block
        ):
            blocks.append(
                current_block
            )

            current_block = []

        current_block.append(
            message
        )

    if current_block:
        blocks.append(
            current_block
        )

    # --------------------------------------------------------
    # Keep newest complete blocks.
    # --------------------------------------------------------

    selected: list[
        list[dict[str, Any]]
    ] = []

    for block in reversed(
        blocks
    ):
        block_chars = sum(
            len(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )
            + len(
                str(
                    message.get(
                        "tool_calls",
                        "",
                    )
                )
            )
            for message in block
        )

        if block_chars > remaining_chars:
            continue

        selected.append(
            block
        )

        remaining_chars -= (
            block_chars
        )

        if remaining_chars <= 0:
            break

    selected.reverse()

    final_messages = (
        base.copy()
    )

    for block in selected:
        final_messages.extend(
            block
        )

    return final_messages


# ============================================================
# GROQ REQUEST
# ============================================================

def call_groq_with_retry(
    client: Groq,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
):
    """
    Call Groq using auto tool selection.

    Mandatory build/preview actions are NOT forced through Groq.
    Python executes them directly to avoid tool-choice mismatch.
    """

    prepared_messages = (
        prepare_messages_for_groq(
            messages
        )
    )

    current_max_tokens = (
        MAX_COMPLETION_TOKENS
    )

    for attempt in range(
        MAX_GROQ_RETRIES
    ):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=prepared_messages,
                tools=tools,
                tool_choice="auto",
                parallel_tool_calls=False,
                temperature=0.2,
                max_completion_tokens=(
                    current_max_tokens
                ),
                reasoning_effort="low",
                include_reasoning=False,
            )

        except Exception as error:
            status_code = getattr(
                error,
                "status_code",
                None,
            )

            # ------------------------------------------------
            # Rate limit
            # ------------------------------------------------

            if status_code == 429:
                if (
                    attempt
                    >= MAX_GROQ_RETRIES - 1
                ):
                    raise

                wait_seconds = (
                    2 ** attempt
                )

                print(
                    "⏳ Groq rate limit reached "
                    f"(429). Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            # ------------------------------------------------
            # Request too large
            # ------------------------------------------------

            if status_code == 413:
                if current_max_tokens > 1800:
                    current_max_tokens = 1800

                    print(
                        "⚠️ Groq request too large. "
                        "Retrying with smaller completion budget..."
                    )

                    time.sleep(
                        1
                    )

                    continue

                raise RuntimeError(
                    "Groq request remained too large after "
                    "context compaction."
                )

            raise

    raise RuntimeError(
        "Groq request failed after retries."
    )


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are GeneSys, an autonomous coding agent working inside an
isolated Daytona workspace.

The project is a real Vite + React + TypeScript application using
TanStack Router.

Do not assume Remix, Next.js, Vue, or another framework.

IMPORTANT WORKFLOW:

1. The project has already been inspected by GeneSys before you
   begin your coding work.
2. Use read_file to inspect the specific files relevant to the
   user's request.
3. Use write_file to implement the requested functionality.
4. After you make changes, GeneSys itself will automatically run
   the production build.
5. If that build fails, GeneSys will give you the actual build
   output. Read the relevant file, repair the problem with
   write_file, and let GeneSys run the build again.
6. Once the build passes, GeneSys itself will automatically start
   the application preview.

TOOL DISCIPLINE:

- Do NOT call list_files. The project has already been inspected.
- Do NOT call run_build. GeneSys executes the build automatically
  after your edits.
- Do NOT call start_preview. GeneSys starts preview automatically
  after a successful build.
- Do NOT repeatedly read the same file without making progress.
- Use read_file before modifying an existing file when necessary.
- Use write_file with complete file contents.

IMPLEMENTATION:

- Build the actual requested feature.
- Prefer the existing project architecture.
- Do not rewrite unrelated files.
- Do not modify .env or protected secrets.
- Do not fabricate framework files.
- Use the actual project as the source of truth.

For interactive applications and games, implement a genuinely
usable feature with the requested UI, state, controls, and
responsive behavior.

When repairing build errors, use the compiler output as evidence.
Do not guess randomly.
"""


# ============================================================
# DIRECT TOOL EXECUTION HELPER
# ============================================================

def execute_direct_tool(
    tool_name: str,
    project_id: str,
) -> dict[str, Any]:
    """
    Execute a mandatory infrastructure tool directly from Python.

    This intentionally bypasses model tool_choice.
    """

    print(
        f"🔧 TOOL: {tool_name}"
    )

    try:
        result = execute_tool(
            tool_name,
            {},
            project_id=project_id,
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "status": "success",
                "result": result,
            }

        print(
            f"✅ TOOL COMPLETE: "
            f"{tool_name}"
        )

        return result

    except Exception as error:
        result = {
            "status": "error",
            "error": str(error),
        }

        print(
            f"❌ TOOL ERROR: "
            f"{tool_name}: {error}"
        )

        return result


# ============================================================
# APPEND DIRECT RESULT TO CONVERSATION
# ============================================================

def append_direct_result(
    messages: list[dict[str, Any]],
    label: str,
    result: dict[str, Any],
) -> None:
    """
    Direct tools do not originate from a Groq tool call, so they
    are represented as user-side execution notes rather than
    invalid orphaned tool messages.
    """

    compacted = compact_tool_result(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )

    messages.append(
        {
            "role": "user",
            "content": (
                f"GENESYS EXECUTION RESULT — {label}\n"
                f"{compacted}"
            ),
        }
    )


# ============================================================
# MAIN AGENT
# ============================================================

def run_agent(
    prompt: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not prompt or not str(
        prompt
    ).strip():
        raise ValueError(
            "Prompt is required."
        )

    project_id = (
        str(project_id).strip()
        or "genesys-project"
    )

    client = get_client()

    # --------------------------------------------------------
    # Conversation
    # --------------------------------------------------------

    messages: list[
        dict[str, Any]
    ] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Project ID: {project_id}\n\n"
                f"User request:\n{prompt}"
            ),
        },
    ]

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    inspected = False

    build_attempted = False

    build_passed = False

    preview_started = False

    changed_since_build = False

    modified_files: list[
        str
    ] = []

    steps: list[
        dict[str, Any]
    ] = []

    last_answer = ""

    last_tool_name: str | None = None

    consecutive_same_tool_calls = 0

    # ========================================================
    # STEP 1 — DIRECT PROJECT INSPECTION
    # ========================================================
    #
    # No reason to spend a Groq call asking it to choose
    # list_files. Python simply performs the required inspection.
    #

    print(
        "🔎 Performing mandatory project inspection..."
    )

    inspection = execute_direct_tool(
        "list_files",
        project_id,
    )

    steps.append(
        {
            "tool": "list_files",
            "status": (
                "success"
                if inspection.get(
                    "status"
                ) != "error"
                else "error"
            ),
            "result": inspection,
        }
    )

    if inspection.get(
        "status"
    ) == "error":
        return {
            "status": "error",
            "answer": (
                "GeneSys could not inspect the Daytona project: "
                f"{inspection.get('error', 'Unknown error')}"
            ),
            "steps": steps,
            "modifiedFiles": modified_files,
            "buildAttempted": False,
            "buildPassed": False,
            "projectId": project_id,
        }

    inspected = True

    append_direct_result(
        messages,
        "PROJECT INSPECTION",
        inspection,
    )

    print(
        "🔎 Project inspection complete."
    )

    # ========================================================
    # MAIN LOOP
    # ========================================================

    for step_number in range(
        2,
        MAX_STEPS + 1,
    ):

        print(
            f"🤖 Agent step "
            f"{step_number}/{MAX_STEPS}"
        )

        # ====================================================
        # MANDATORY BUILD
        # ====================================================
        #
        # Once the model has changed files, Python owns the build.
        #

        if (
            changed_since_build
        ):
            print(
                "🏗️ Running mandatory build..."
            )

            build_result = (
                execute_direct_tool(
                    "run_build",
                    project_id,
                )
            )

            steps.append(
                {
                    "tool": "run_build",
                    "status": (
                        "success"
                        if build_result.get(
                            "success"
                        ) is True
                        else "error"
                    ),
                    "result": build_result,
                }
            )

            build_attempted = True

            append_direct_result(
                messages,
                "BUILD",
                build_result,
            )

            if build_result.get(
                "success"
            ) is True:

                build_passed = True
                changed_since_build = False

                print(
                    "🏗️ BUILD PASSED"
                )

            else:

                build_passed = False
                changed_since_build = False

                print(
                    "❌ BUILD FAILED"
                )

                # ------------------------------------------------
                # The next model turn becomes a repair turn.
                # ------------------------------------------------

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The latest production build FAILED. "
                            "Repair the project using the actual "
                            "build output above. Read the relevant "
                            "file(s) and use write_file to correct "
                            "the problem. Do not finish until you "
                            "have made the repair."
                        ),
                    }
                )

                continue

        # ====================================================
        # MANDATORY PREVIEW
        # ====================================================

        if (
            build_passed
            and modified_files
            and not preview_started
        ):
            print(
                "🌐 Starting mandatory application preview..."
            )

            preview_result = (
                execute_direct_tool(
                    "start_preview",
                    project_id,
                )
            )

            steps.append(
                {
                    "tool": "start_preview",
                    "status": (
                        "success"
                        if preview_result.get(
                            "status"
                        ) == "success"
                        else "error"
                    ),
                    "result": preview_result,
                }
            )

            append_direct_result(
                messages,
                "PREVIEW",
                preview_result,
            )

            if (
                preview_result.get(
                    "status"
                )
                == "success"
            ):
                preview_started = True

                print(
                    "🌐 PREVIEW STARTED"
                )

            else:
                return {
                    "status": "error",
                    "answer": (
                        "The project built successfully, but "
                        "the application preview could not be started: "
                        f"{preview_result.get('error') or preview_result.get('message') or 'Unknown error'}"
                    ),
                    "steps": steps,
                    "modifiedFiles": modified_files,
                    "buildAttempted": build_attempted,
                    "buildPassed": build_passed,
                    "projectId": project_id,
                }

            # ------------------------------------------------
            # We have completed the actual work.
            # Return without another Groq call.
            # ------------------------------------------------

            last_answer = (
                last_answer
                or "GeneSys completed the requested change."
            )

            print(
                "🤖 AGENT RESULT: success"
            )

            return {
                "status": "success",
                "answer": last_answer,
                "steps": steps,
                "modifiedFiles": modified_files,
                "buildAttempted": build_attempted,
                "buildPassed": build_passed,
                "projectId": project_id,
            }

        # ====================================================
        # CHOOSE MODEL TOOL SET
        # ====================================================
        #
        # The model is only allowed to inspect/edit here.
        # Infrastructure actions are handled by Python.
        #

        if inspected:

            allowed_tools = [
                TOOL_BY_NAME["read_file"],
                TOOL_BY_NAME["write_file"],
            ]

        else:
            allowed_tools = [
                TOOL_BY_NAME["list_files"]
            ]

        # ----------------------------------------------------
        # Call Groq
        # ----------------------------------------------------

        try:
            response = (
                call_groq_with_retry(
                    client,
                    messages,
                    allowed_tools,
                )
            )

        except Exception as error:
            print(
                f"❌ AGENT ERROR: {error}"
            )

            return {
                "status": "error",
                "answer": (
                    "GeneSys encountered an agent error: "
                    f"{error}"
                ),
                "steps": steps,
                "modifiedFiles": modified_files,
                "buildAttempted": build_attempted,
                "buildPassed": build_passed,
                "projectId": project_id,
            }

        choice = (
            response.choices[0]
        )

        message = choice.message

        last_answer = (
            message.content
            if message.content
            else last_answer
        )

        tool_calls = (
            getattr(
                message,
                "tool_calls",
                None,
            )
            or []
        )

        # ====================================================
        # MODEL TOOL CALLS
        # ====================================================

        if tool_calls:

            assistant_message = (
                build_assistant_tool_message(
                    message
                )
            )

            messages.append(
                assistant_message
            )

            wrote_file_this_turn = False

            for tool_call in tool_calls:

                tool_name = (
                    tool_call.function.name
                )

                raw_arguments = (
                    tool_call.function.arguments
                    or "{}"
                )

                print(
                    f"🔧 TOOL: {tool_name}"
                )

                # ------------------------------------------------
                # Only read_file/write_file are expected here.
                # ------------------------------------------------

                if tool_name not in {
                    "read_file",
                    "write_file",
                }:
                    result = {
                        "status": "error",
                        "error": (
                            f"Tool '{tool_name}' is not allowed "
                            "during the coding phase."
                        ),
                    }

                    print(
                        f"❌ TOOL BLOCKED: "
                        f"{tool_name}"
                    )

                else:

                    # --------------------------------------------
                    # Parse arguments
                    # --------------------------------------------

                    try:
                        arguments = json.loads(
                            raw_arguments
                        )

                        if not isinstance(
                            arguments,
                            dict,
                        ):
                            raise ValueError(
                                "Tool arguments must be a JSON object."
                            )

                    except Exception as error:
                        result = {
                            "status": "error",
                            "error": (
                                f"Invalid tool arguments: "
                                f"{error}"
                            ),
                        }

                        print(
                            "❌ TOOL ARGUMENT ERROR: "
                            f"{error}"
                        )

                    else:

                        # ----------------------------------------
                        # Repetition tracking
                        # ----------------------------------------

                        if (
                            tool_name
                            == last_tool_name
                        ):
                            consecutive_same_tool_calls += 1
                        else:
                            consecutive_same_tool_calls = 1

                        last_tool_name = tool_name

                        # ----------------------------------------
                        # Execute
                        # ----------------------------------------

                        try:
                            result = execute_tool(
                                tool_name,
                                arguments,
                                project_id=project_id,
                            )

                            if not isinstance(
                                result,
                                dict,
                            ):
                                result = {
                                    "status": "success",
                                    "result": result,
                                }

                            succeeded = (
                                result.get(
                                    "status"
                                )
                                != "error"
                            )

                            # ------------------------------------
                            # WRITE FILE
                            # ------------------------------------

                            if (
                                tool_name
                                == "write_file"
                                and succeeded
                            ):
                                wrote_file_this_turn = True
                                changed_since_build = True

                                file_name = (
                                    result.get(
                                        "file"
                                    )
                                )

                                if (
                                    file_name
                                    and file_name
                                    not in modified_files
                                ):
                                    modified_files.append(
                                        file_name
                                    )

                            print(
                                f"✅ TOOL COMPLETE: "
                                f"{tool_name}"
                            )

                        except Exception as error:
                            result = {
                                "status": "error",
                                "error": str(error),
                            }

                            print(
                                f"❌ TOOL ERROR: "
                                f"{tool_name}: "
                                f"{error}"
                            )

                # ------------------------------------------------
                # Tell model what happened.
                # ------------------------------------------------

                steps.append(
                    {
                        "tool": tool_name,
                        "status": (
                            "success"
                            if result.get(
                                "status"
                            ) != "error"
                            else "error"
                        ),
                        "result": result,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": (
                            tool_call.id
                        ),
                        "name": tool_name,
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )

            # ----------------------------------------------------
            # If model wrote something, next loop MUST build.
            # ----------------------------------------------------

            if wrote_file_this_turn:
                print(
                    "📝 Files changed. "
                    "Next action will be the mandatory build."
                )

                continue

            # ----------------------------------------------------
            # Detect repetitive inspection.
            # ----------------------------------------------------

            if (
                consecutive_same_tool_calls
                >= 3
            ):
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have repeated the same tool "
                            "multiple times without making progress. "
                            "Stop rereading the same file. "
                            "Use the information already available "
                            "and make the requested change with "
                            "write_file."
                        ),
                    }
                )

            continue

        # ====================================================
        # MODEL RETURNED TEXT WITHOUT A TOOL CALL
        # ====================================================

        # ----------------------------------------------------
        # If changes already exist, build will happen at the
        # beginning of the next loop.
        # ----------------------------------------------------

        if changed_since_build:
            print(
                "⚠️ Model returned text after changes. "
                "The mandatory build will run next."
            )

            continue

        # ----------------------------------------------------
        # Repair phase
        #
        # If the model has not called write_file after a failed
        # build, force it back into the repair workflow.
        # ----------------------------------------------------

        if (
            build_attempted
            and not build_passed
        ):
            messages.append(
                {
                    "role": "assistant",
                    "content": last_answer,
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The build is still failing and no repair "
                        "has been written yet. You MUST inspect "
                        "the relevant file and use write_file to "
                        "repair the build. Do not finish with text."
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # No modifications required.
        # ----------------------------------------------------

        print(
            "🤖 AGENT RESULT: success"
        )

        return {
            "status": "success",
            "answer": (
                last_answer
                or "GeneSys completed the request."
            ),
            "steps": steps,
            "modifiedFiles": modified_files,
            "buildAttempted": build_attempted,
            "buildPassed": build_passed,
            "projectId": project_id,
        }

    # ========================================================
    # MAX STEPS
    # ========================================================

    print(
        "⚠️ AGENT STOPPED: "
        "maximum step limit reached."
    )

    return {
        "status": "stopped",
        "answer": (
            "GeneSys reached the maximum number of "
            "agent steps before completing the request."
        ),
        "steps": steps,
        "modifiedFiles": modified_files,
        "buildAttempted": build_attempted,
        "buildPassed": build_passed,
        "projectId": project_id,
    }