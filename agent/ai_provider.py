import json
import time
from dataclasses import dataclass, field
from typing import Any

from .config import load_settings

# ============================================================
# CONFIGURATION
# ============================================================

settings = load_settings()


# ============================================================
# NORMALIZED AI TYPES
# ============================================================

@dataclass
class AIToolCall:
    """Provider-independent representation of a tool call."""

    id: str
    name: str
    arguments: dict[str, Any]

    # Gemini tool-calling support
    thought_signature: Any | None = None


@dataclass(init=False)
class AIResponse:
    """Provider-independent representation of an AI response."""

    content: str = ""
    tool_calls: list[AIToolCall] = field(
        default_factory=list
    )

    def __init__(
        self,
        text: str = "",
        tool_calls: list[AIToolCall] | None = None,
        content: str | None = None,
    ) -> None:
        if content is not None:
            self.content = content
        else:
            self.content = text

        self.tool_calls = (
            tool_calls
            if tool_calls is not None
            else []
        )

    @property
    def text(self) -> str:
        return self.content

# ============================================================
# PROVIDER INTERFACE
# ============================================================

class AIProvider:
    """Common interface for all GeneSys AI providers."""

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AIResponse:
        raise NotImplementedError


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_MODEL = settings.genesys_gemini_model


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_MODEL = settings.genesys_model

MAX_COMPLETION_TOKENS = 3200

MAX_GROQ_RETRIES = 2

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
    if isinstance(content, bytes):
        content = content.decode(
            "utf-8",
            errors="replace",
        )
    try:
        data = json.loads(content)
    except Exception:
        return compact_text(
            content,
            GENERIC_TOOL_MAX_CHARS,
        )

    if not isinstance(data, dict):
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
            default=str,
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

        if isinstance(files, list):
            result["files"] = files[:140]

        tree = data.get("tree")

        if isinstance(tree, dict):
            tree_copy = dict(tree)

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
                default=str,
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
            default=str,
        )

    # --------------------------------------------------------
    # browser_screenshot
    # --------------------------------------------------------

    if (
        data.get("format") == "png"
        and "image" in data
    ):
        result = dict(data)

        image = result.pop(
            "image",
            None,
        )

        if isinstance(image, (bytes, bytearray)):
            result["imageBytes"] = len(image)
        elif isinstance(image, str):
            result["imageBytes"] = len(image) // 2

        return compact_text(
            json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            ),
            GENERIC_TOOL_MAX_CHARS,
        )

    # --------------------------------------------------------
    # generic
    # --------------------------------------------------------

    return compact_text(
        json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        ),
        GENERIC_TOOL_MAX_CHARS,
    )


# ============================================================
# ASSISTANT TOOL COMPACTION
# ============================================================

def compact_assistant_message(
    message: dict[str, Any],
) -> dict[str, Any]:
    result = dict(message)

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
        call_copy = dict(call)

        call_copy.pop(
            "thought_signature",
            None,
        )

        function = call.get(
            "function"
        )

        if isinstance(
            function,
            dict,
        ):
            function_copy = dict(function)

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
# PREPARE MESSAGES FOR GROQ
# ============================================================

def prepare_messages_for_groq(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare a compact but structurally valid Groq conversation."""

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
            copy = dict(message)

            copy["content"] = compact_text(
                message.get(
                    "content",
                    "",
                ),
                SYSTEM_MAX_CHARS,
            )

            prepared.append(copy)

            continue

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        if role == "user":
            copy = dict(message)

            copy["content"] = compact_text(
                message.get(
                    "content",
                    "",
                ),
                USER_MAX_CHARS,
            )

            prepared.append(copy)

            continue

        # ----------------------------------------------------
        # ASSISTANT
        # ----------------------------------------------------

        if role == "assistant":
            if message.get("tool_calls"):
                prepared.append(
                    compact_assistant_message(
                        message
                    )
                )
            else:
                copy = dict(message)

                copy["content"] = compact_text(
                    message.get(
                        "content",
                        "",
                    ),
                    2200,
                )

                prepared.append(copy)

            continue

        # ----------------------------------------------------
        # TOOL
        # ----------------------------------------------------

        if role == "tool":
            copy = dict(message)

            copy["content"] = compact_tool_result(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )

            prepared.append(copy)

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

    for block in reversed(blocks):
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

        selected.append(block)

        remaining_chars -= block_chars

        if remaining_chars <= 0:
            break

    selected.reverse()

    final_messages = base.copy()

    for block in selected:
        final_messages.extend(
            block
        )

    return final_messages


# ============================================================
# GEMINI PROVIDER
# ============================================================

class GeminiProvider(AIProvider):
    """Gemini provider with manual GeneSys tool calling."""

    def __init__(
        self,
        model: str | None = None,
    ):
        self.model = model or GEMINI_MODEL

        api_key = settings.gemini_api_key

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        from google import genai

        self.client = genai.Client(
            api_key=api_key
        )

    @staticmethod
    def _sanitize_tool_schema(
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert OpenAI-style JSON Schema to Gemini-compatible schema."""

        if not isinstance(schema, dict):
            return {
                "type": "object",
                "properties": {},
            }

        cleaned: dict[str, Any] = {}

        for key, value in schema.items():

            # Gemini does not accept these JSON Schema fields.
            if key in {
                "additional_properties",
                "additionalProperties",
            }:
                continue

            if isinstance(value, dict):
                cleaned[key] = (
                    GeminiProvider._sanitize_tool_schema(
                        value
                    )
                )

            elif isinstance(value, list):
                cleaned[key] = [
                    (
                        GeminiProvider._sanitize_tool_schema(
                            item
                        )
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]

            else:
                cleaned[key] = value

        return cleaned

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AIResponse:
        """Generate one Gemini response.

        Gemini tool calls are returned to the GeneSys orchestrator.
        The orchestrator remains responsible for actually executing
        the requested tool.
        """

        from google.genai import types

        contents: list[
            types.Content
        ] = []

        system_instruction: str | None = None

        for message in messages:
            role = message.get(
                "role"
            )

            content = message.get(
                "content",
                "",
            )

            if content is None:
                content = ""

            if role == "system":
                system_instruction = str(
                    content
                )
                continue

            if role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text=str(
                                    content
                                )
                            )
                        ],
                    )
                )
                continue

            if role == "assistant":
                assistant_parts = []

                if content:
                    assistant_parts.append(
                        types.Part.from_text(
                            text=str(content)
                        )
                    )

                assistant_tool_calls = (
                    message.get("tool_calls", [])
                    or []
                )

                for tool_call in assistant_tool_calls:
                    function_data = (
                        tool_call.get(
                            "function",
                            {},
                        )
                        or {}
                    )

                    function_name = (
                        function_data.get(
                            "name",
                            "",
                        )
                    )

                    raw_arguments = (
                        function_data.get(
                            "arguments",
                            "{}",
                        )
                    )

                    if not function_name:
                        continue

                    try:
                        function_arguments = json.loads(
                            str(raw_arguments)
                        )
                    except Exception:
                        function_arguments = {}

                    if not isinstance(
                        function_arguments,
                        dict,
                    ):
                        function_arguments = {}

                    function_part = (
                        types.Part.from_function_call(
                            name=function_name,
                            args=function_arguments,
                        )
                    )

                    thought_signature = (
                        tool_call.get(
                            "thought_signature"
                        )
                    )

                    if (
                        thought_signature
                        is not None
                    ):
                        function_part.thought_signature = (
                            thought_signature
                        )

                    assistant_parts.append(
                        function_part
                    )

                if assistant_parts:
                    contents.append(
                        types.Content(
                            role="model",
                            parts=assistant_parts,
                        )
                    )

                continue

            if role == "tool":
                tool_name = message.get(
                    "name",
                    "",
                )

                tool_call_id = message.get(
                    "tool_call_id",
                    "",
                )

                tool_content = message.get(
                    "content",
                    "",
                )

                if tool_content is None:
                    tool_content = ""

                try:
                    parsed_content = json.loads(
                        str(tool_content)
                    )
                except Exception:
                    parsed_content = {
                        "result": str(
                            tool_content
                        )
                    }

                if not isinstance(
                    parsed_content,
                    dict,
                ):
                    parsed_content = {
                        "result": parsed_content
                    }

                response_payload = {
                    "tool_call_id": tool_call_id,
                    "result": parsed_content,
                }

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=(
                                    tool_name
                                    or "unknown_tool"
                                ),
                                response=response_payload,
                            )
                        ],
                    )
                )
                continue

        function_declarations = []

        for tool in tools:
            if tool.get("type") != "function":
                continue

            function = tool.get(
                "function",
                {},
            )

            name = function.get(
                "name"
            )

            if not name:
                continue

            parameters = function.get(
                "parameters",
                {
                    "type": "object",
                    "properties": {},
                },
            )

            parameters = (
                self._sanitize_tool_schema(
                    parameters
                )
            )

            function_declarations.append(
                {
                    "name": name,
                    "description": function.get(
                        "description",
                        "",
                    ),
                    "parameters": parameters,
                }
            )

        config_kwargs: dict[str, Any] = {}

        if system_instruction:
            config_kwargs[
                "system_instruction"
            ] = system_instruction

        if function_declarations:
            config_kwargs["tools"] = [
                types.Tool(
                    function_declarations=(
                        function_declarations
                    )
                )
            ]

        config = types.GenerateContentConfig(
            **config_kwargs
        )

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        )

        if not response.candidates:
            return AIResponse()

        candidate = response.candidates[0]

        if not candidate.content:
            return AIResponse()

        text_parts: list[str] = []

        tool_calls: list[
            AIToolCall
        ] = []

        for index, part in enumerate(
            candidate.content.parts or []
        ):
            text = getattr(
                part,
                "text",
                None,
            )

            if text:
                text_parts.append(
                    text
                )

            function_call = getattr(
                part,
                "function_call",
                None,
            )

            if function_call:
                call_id = getattr(
                    function_call,
                    "id",
                    None,
                )

                if not call_id:
                    call_id = (
                        f"gemini-call-{index}"
                    )

                arguments = dict(
                    getattr(
                        function_call,
                        "args",
                        {},
                    )
                    or {}
                )

                tool_calls.append(
                    AIToolCall(
                        id=call_id,
                        name=function_call.name,
                        arguments=arguments,
                        thought_signature=getattr(
                            part,
                            "thought_signature",
                            None,
                        ),
                    )
                )

        return AIResponse(
            text="\n".join(
                text_parts
            ).strip(),
            tool_calls=tool_calls,
        )


# ============================================================
# GROQ PROVIDER
# ============================================================

class GroqProvider(AIProvider):
    """Groq implementation preserving the existing GeneSys behavior."""

    def __init__(
        self,
        model: str | None = None,
        client=None,
    ):
        from groq import Groq

        api_key = settings.groq_api_key

        if not api_key and client is None:
            raise RuntimeError(
                "GROQ_API_KEY is missing from configuration."
            )

        self.model = model or GROQ_MODEL

        self.client = client or Groq(
            api_key=api_key,
            max_retries=0,
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AIResponse:
        """Call Groq using the same settings as the existing agent."""

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
                response = (
                    self.client.chat.completions.create(
                        model=self.model,
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
                )

                choice = response.choices[0]

                message = choice.message

                text = (
                    message.content
                    if message.content
                    else ""
                )

                normalized_tool_calls = []

                for call in (
                    getattr(
                        message,
                        "tool_calls",
                        None,
                    )
                    or []
                ):
                    raw_arguments = (
                        call.function.arguments
                        or "{}"
                    )

                    try:
                        arguments = json.loads(
                            raw_arguments
                        )

                        if not isinstance(
                            arguments,
                            dict,
                        ):
                            arguments = {}

                    except Exception:
                        arguments = {}

                    normalized_tool_calls.append(
                        AIToolCall(
                            id=call.id,
                            name=call.function.name,
                            arguments=arguments,
                        )
                    )

                return AIResponse(
                    text=text,
                    tool_calls=normalized_tool_calls,
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

                    # Groq can tell us how long to wait.
                    # Fall back to exponential backoff if that
                    # information is unavailable.
                    wait_seconds = 2 ** attempt

                    error_text = str(error)
                    marker = "Please try again in "

                    if marker in error_text:
                        try:
                            retry_text = error_text.split(
                                marker,
                                1,
                            )[1]

                            retry_value = retry_text.split(
                                "s",
                                1,
                            )[0].strip()

                            wait_seconds = float(
                                retry_value
                            )
                        except (ValueError, IndexError):
                            pass

                    # Keep the retry bounded.
                    wait_seconds = max(
                        1.0,
                        min(
                            wait_seconds,
                            30.0,
                        ),
                    )

                    print(
                        "⏳ Groq rate limit reached "
                        f"(429). Retrying in "
                        f"{wait_seconds:.1f}s..."
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

                        time.sleep(1)

                        continue

                    raise RuntimeError(
                        "Groq request remained too large "
                        "after context compaction."
                    )

                raise

        raise RuntimeError(
            "Groq request failed after retries."
        )