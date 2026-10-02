"""Check the configured chat model through LiteLLM.

python -m app.scripts.check_chat_model

Prints the active configuration (not the key), then makes one plain completion and one forced
tool call.
"""

import asyncio
import time

from app import llm
from app.config import get_settings

PING_TOOL = {
    "type": "function",
    "function": {
        "name": "ping",
        "description": "Call this tool when asked to.",
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer"}},
            "required": ["n"],
        },
    },
}


async def main() -> None:
    settings = get_settings()
    print(f"CHAT_MODEL     {settings.chat_model}")
    print(f"API key        {'set' if settings.chat_api_key else 'not set'}")
    print(f"CHAT_API_BASE  {settings.chat_api_base or '(none)'}")

    try:
        started = time.monotonic()
        reply = await llm.complete(
            [{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=20
        )
        print(f"1. plain reply  {reply.content!r} ({time.monotonic() - started:.1f}s)")

        started = time.monotonic()
        reply = await llm.complete(
            [{"role": "user", "content": "Call the ping tool with n=7."}],
            tools=[PING_TOOL],
            tool_choice="required",
            max_tokens=100,
        )
    except llm.LlmError as exc:
        print(f"FAILED         {exc}")
        raise SystemExit(1) from exc

    elapsed = time.monotonic() - started
    if reply.tool_calls and reply.tool_calls[0].name == "ping":
        print(f"2. tool call    ping({reply.tool_calls[0].arguments}) ({elapsed:.1f}s)")
        print("OK             this model can run the Q&A agent")
    else:
        print(f"2. tool call    none; the model replied {reply.content!r}")
        print(
            "WARNING        no tool call, so the Q&A agent can't search materials with this model"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
