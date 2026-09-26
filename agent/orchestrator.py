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

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ============================================================
# MODEL / AGENT SETTINGS
# ============================================================

MODEL = "openai/gpt-oss-120b"

# Maximum number of agent/tool turns.
MAX_STEPS = 18

# Keep this below the current TPM ceiling so the agent has room
# for retries and multiple tool-calling turns.
MAX_COMPLETION_TOKENS = 6000

# Retry configuration for Groq HTTP 429 rate limits.
MAX_GROQ_RETRIES = 4


# ============================================================
# CLIENT
# ============================================================

def get_client() -> Groq:
    """
    Create the Groq client using the server-side GROQ_API_KEY.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from the environment."
        )

    return Groq(api_key=api_key)


# ============================================================
# GROQ REQUEST WITH RETRY
# ============================================================

def call_groq_with_retry(
    client: Groq,
    messages: list[dict[str, Any]],
):
    """
    Call Groq and automatically retry temporary 429 rate-limit errors.

    We use short exponential backoff:
        attempt 1 -> 2 seconds
        attempt 2 -> 4 seconds
        attempt 3 -> 8 seconds
        attempt 4 -> 16 seconds
    """

    for attempt in range(MAX_GROQ_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=MAX_COMPLETION_TOKENS,
            )

            return response

        except Exception as error:
            status_code = getattr(error, "status_code", None)

            # Only retry rate-limit errors.
            if status_code != 429:
                raise

            # Final attempt failed.
            if attempt >= MAX_GROQ_RETRIES - 1:
                raise

            wait_seconds = 2 ** attempt

            print(
                f"⏳ Groq rate limit reached (429). "
                f"Retrying in {wait_seconds}s "
                f"(attempt {attempt + 1}/{MAX_GROQ_RETRIES})..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Groq request failed after all retries.")


# ============================================================
# TOOL MESSAGE BUILDER
# ============================================================

def build_assistant_tool_message(message: Any) -> dict[str, Any]:
    """
    Reconstruct the assistant message containing tool calls.

    We intentionally do NOT use message.model_dump() here because
    Groq may include fields such as 'annotations' that are not
    accepted when the message is sent back in the next request.
    """

    tool_calls = getattr(message, "tool_calls", None) or []

    return {
        "role": "assistant",
        "content": message.content,
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
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are GeneSys, an autonomous coding agent working inside a real
Vite + React + TypeScript project.

Your job is to inspect the project, understand the existing code,
make the requested changes, and verify that the project builds.

IMPORTANT PROJECT FACTS:

- This project uses Vite.
- This project uses React.
- This project uses TypeScript / TSX.
- This project uses TanStack Router.
- Do NOT assume Remix.
- Do NOT assume Next.js.
- Do NOT assume Vue.
- Do NOT invent framework files that do not exist.
- The local workspace is the source of truth.

CORE WORKFLOW:

1. Inspect the project with list_files.
2. Before modifying an existing file, read it with read_file.
3. Make the smallest appropriate changes using write_file.
4. After making code changes, ALWAYS run run_build.
5. If run_build fails:
   - inspect the build error carefully,
   - identify the relevant file,
   - read the file if necessary,
   - repair the problem,
   - run run_build again.
6. Continue repairing until the build passes or there is a genuine
   blocker that cannot be resolved.
7. Never claim success if the final build has not passed.

WHEN BUILD ERRORS OCCUR:

Treat compiler and Vite errors as concrete evidence.

For example:
- TypeScript syntax errors -> inspect the reported file and fix syntax.
- Missing imports -> inspect the importing file and relevant project files.
- Invalid JSX/TSX -> repair the component syntax.
- Vite resolution errors -> verify the referenced path exists.
- Type errors -> inspect the involved types and imports.

DO NOT randomly rewrite unrelated files.

WHEN THE USER REQUESTS A NEW FEATURE:

Build the actual feature in the existing application rather than
merely returning an explanation.

For example, if the user requests a game:
- implement the actual game,
- create the necessary UI,
- add the necessary logic,
- make it playable,
- integrate it with the existing app structure,
- then run the build.

When modifying the application, prefer existing architecture,
components, routes, and utilities when appropriate.

DO NOT MODIFY PROTECTED SECRETS OR CONFIGURATION UNLESS A TOOL
EXPLICITLY ALLOWS IT.
PREVIEW:

After successfully completing a meaningful application change and
confirming that the build passes, call start_preview so the user can
see and interact with the current application.

Do not call start_preview before the build has passed.

If the preview server is already running, reuse it.

The agent should focus on producing working project code and verifying
it with the build command.
"""


# ============================================================
# AGENT RUNNER
# ============================================================

def run_agent(
    prompt: str,
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Run the GeneSys autonomous coding agent.

    Returns:
        {
            "status": "success" | "error" | "stopped",
            "answer": str,
            "steps": list,
            "modifiedFiles": list[str],
            "buildAttempted": bool,
            "buildPassed": bool,
            "projectId": str,
        }
    """

    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt is required.")

    client = get_client()

    # --------------------------------------------------------
    # Conversation state
    # --------------------------------------------------------

    messages: list[dict[str, Any]] = [
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

    steps: list[dict[str, Any]] = []
    modified_files: list[str] = []

    build_attempted = False
    build_passed = False
    changed_files_since_build = False

    # --------------------------------------------------------
    # Main agent loop
    # --------------------------------------------------------

    for step_number in range(1, MAX_STEPS + 1):
        print(
            f"🤖 Agent step {step_number}/{MAX_STEPS}"
        )

        try:
            response = call_groq_with_retry(
                client,
                messages,
            )
        except Exception as error:
            print(
                f"❌ AGENT ERROR: {error}"
            )

            return {
                "status": "error",
                "answer": (
                    "The GeneSys agent encountered an error while "
                    f"communicating with the model: {error}"
                ),
                "steps": steps,
                "modifiedFiles": modified_files,
                "buildAttempted": build_attempted,
                "buildPassed": build_passed,
                "projectId": project_id,
            }

        choice = response.choices[0]
        message = choice.message

        tool_calls = getattr(message, "tool_calls", None) or []

        # ----------------------------------------------------
        # Model wants to call tools
        # ----------------------------------------------------

        if tool_calls:
            assistant_tool_message = build_assistant_tool_message(
                message
            )

            messages.append(assistant_tool_message)

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments or "{}"

                print(
                    f"🔧 TOOL: {tool_name}"
                )

                # --------------------------------------------
                # Parse arguments
                # --------------------------------------------

                try:
                    arguments = json.loads(raw_arguments)

                    if not isinstance(arguments, dict):
                        raise ValueError(
                            "Tool arguments must be a JSON object."
                        )

                except Exception as error:
                    result = {
                        "status": "error",
                        "error": (
                            f"Invalid tool arguments: {error}"
                        ),
                    }

                    print(
                        f"❌ TOOL ARGUMENT ERROR: {error}"
                    )

                    steps.append(
                        {
                            "tool": tool_name,
                            "status": "error",
                            "result": result,
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )

                    continue

                # --------------------------------------------
                # Execute tool
                # --------------------------------------------

                try:
                    result = execute_tool(
                        tool_name,
                        arguments,
                    )

                    tool_status = (
                        "success"
                        if result.get("status") != "error"
                        else "error"
                    )

                    if tool_name == "write_file" and tool_status == "success":
                        changed_files_since_build = True

                        file_name = result.get("file")

                        if file_name and file_name not in modified_files:
                            modified_files.append(file_name)

                    if tool_name == "run_build":
                        build_attempted = True

                        if result.get("success") is True:
                            build_passed = True
                            changed_files_since_build = False

                            print(
                                "🏗️ BUILD PASSED"
                            )
                        else:
                            build_passed = False

                            print(
                                "❌ BUILD FAILED"
                            )

                    steps.append(
                        {
                            "tool": tool_name,
                            "status": tool_status,
                            "result": result,
                        }
                    )

                    print(
                        f"✅ TOOL COMPLETE: {tool_name}"
                    )

                except Exception as error:
                    result = {
                        "status": "error",
                        "error": str(error),
                    }

                    steps.append(
                        {
                            "tool": tool_name,
                            "status": "error",
                            "result": result,
                        }
                    )

                    print(
                        f"❌ TOOL ERROR: {tool_name}: {error}"
                    )

                # --------------------------------------------
                # Feed tool result back to the model
                # --------------------------------------------

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )

            # Continue the loop so the model can inspect the
            # tool results and decide what to do next.
            continue

        # ----------------------------------------------------
        # Model wants to finish
        # ----------------------------------------------------

        answer = (
            message.content
            if message.content is not None
            else "Agent completed the request."
        )

        # ----------------------------------------------------
        # HARD BUILD GATE
        # ----------------------------------------------------
        #
        # If the agent changed files but has not successfully
        # built the project, do NOT allow it to finish.
        #
        # Send it back into the tool loop and require a build.
        #

        if changed_files_since_build and not build_passed:
            print(
                "⚠️ Agent attempted to finish without a "
                "successful build. Requiring run_build."
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You changed project files but the project has "
                        "not been successfully verified yet. "
                        "You MUST call run_build now. "
                        "If the build fails, inspect the error, repair "
                        "the project, and run run_build again. "
                        "Do not finish until the build passes."
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        print(
            "🤖 AGENT RESULT: success"
        )

        return {
            "status": "success",
            "answer": answer,
            "steps": steps,
            "modifiedFiles": modified_files,
            "buildAttempted": build_attempted,
            "buildPassed": build_passed,
            "projectId": project_id,
        }

    # ========================================================
    # MAX STEP LIMIT
    # ========================================================

    print(
        "⚠️ AGENT STOPPED: maximum step limit reached."
    )

    return {
        "status": "stopped",
        "answer": (
            "The GeneSys agent reached its maximum number of steps "
            "before completing the request."
        ),
        "steps": steps,
        "modifiedFiles": modified_files,
        "buildAttempted": build_attempted,
        "buildPassed": build_passed,
        "projectId": project_id,
    }
