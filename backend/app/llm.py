"""Chat model access through LiteLLM. The provider is set by CHAT_MODEL / CHAT_API_KEY /
CHAT_API_BASE. Embeddings don't use this module.
"""

import json
from dataclasses import dataclass, field
from typing import Any

import litellm
import openai

from app.config import get_settings

litellm.suppress_debug_info = True  # keep LiteLLM's "give feedback" banners out of the logs

REQUEST_TIMEOUT_SECONDS = 180
# Room for a long Q&A answer, which comes back inside one tool call.
DEFAULT_MAX_TOKENS = 8192
_CUT_OFF_REASONS = {"length", "max_tokens"}


class LlmError(Exception):
    """The chat model couldn't be reached or rejected the request."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LlmReply:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # True when generation stopped at max_tokens.
    truncated: bool = False


async def complete(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> LlmReply:
    """One chat completion. `messages` and `tools` use the OpenAI format; LiteLLM translates."""
    settings = get_settings()
    options: dict[str, Any] = {}
    if settings.chat_api_key:
        options["api_key"] = settings.chat_api_key
    if settings.chat_api_base:
        options["api_base"] = settings.chat_api_base
    if tools:
        options["tools"] = tools
        if tool_choice:
            options["tool_choice"] = tool_choice

    try:
        response = await litellm.acompletion(
            model=settings.chat_model,
            messages=messages,
            max_tokens=max_tokens,
            timeout=REQUEST_TIMEOUT_SECONDS,
            **options,
        )
    except openai.OpenAIError as exc:  # LiteLLM maps every provider's errors onto these types
        raise LlmError(str(exc)) from exc

    choice = response.choices[0]
    message = choice.message
    return LlmReply(
        content=message.content,
        tool_calls=[
            ToolCall(id=call.id, name=call.function.name, arguments=_parse_arguments(call))
            for call in message.tool_calls or []
        ],
        truncated=getattr(choice, "finish_reason", None) in _CUT_OFF_REASONS,
    )


def _parse_arguments(call: Any) -> dict[str, Any]:
    try:
        arguments = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        return {}
    return arguments if isinstance(arguments, dict) else {}
