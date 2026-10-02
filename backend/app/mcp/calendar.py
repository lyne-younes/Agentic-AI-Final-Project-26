"""MCP client for the Calendar server, the backend's only route to Google Calendar.

Discovers the server's tools at runtime. The student's access token is hidden from the model and
injected into every tool call.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.types import TextContent

from app.config import get_settings

logger = logging.getLogger(__name__)

# Injected on every call and hidden from the model.
TOKEN_ARG = "access_token"

# Error markers from the server: token rejected (refresh and retry), event deleted by hand.
AUTH_MARKER = "google-auth-rejected"
EVENT_GONE_MARKER = "calendar-event-gone"


class CalendarMcpError(RuntimeError):
    """The MCP server was unreachable, or a call failed in a way the agent can't correct."""


@dataclass(frozen=True)
class McpTool:
    """One tool as advertised by the MCP server, already stripped of the token argument."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def as_openai_tool(self) -> dict[str, Any]:
        """The OpenAI-format tool definition handed to `llm.complete`."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass(frozen=True)
class ToolOutcome:
    """The result of one tool call, as the ReAct loop sees it."""

    content: Any
    is_error: bool
    auth_rejected: bool = False
    event_gone: bool = False


def _strip_token_arg(schema: dict[str, Any]) -> dict[str, Any]:
    properties = {k: v for k, v in schema.get("properties", {}).items() if k != TOKEN_ARG}
    required = [name for name in schema.get("required", []) if name != TOKEN_ARG]
    stripped = {**schema, "properties": properties}
    if required:
        stripped["required"] = required
    else:
        stripped.pop("required", None)
    return stripped


@asynccontextmanager
async def session() -> AsyncIterator["CalendarMcpSession"]:
    """Open one MCP client session, used for a whole planner turn (several tool calls)."""
    settings = get_settings()
    try:
        async with Client(settings.calendar_mcp_url) as client:
            yield CalendarMcpSession(client, settings.calendar_mcp_timeout)
    except CalendarMcpError:
        raise
    except Exception as exc:  # noqa: BLE001 - transport/protocol failures surface the same way
        raise CalendarMcpError(
            f"Could not reach the Calendar MCP server at {settings.calendar_mcp_url}: {exc}"
        ) from exc


class CalendarMcpSession:
    """A live MCP session. Tool discovery is cached for the lifetime of one turn."""

    def __init__(self, client: Client, timeout: float) -> None:
        self._client = client
        self._timeout = timeout
        self._tools: list[McpTool] | None = None

    async def list_tools(self) -> list[McpTool]:
        """Discover the server's tools over MCP, minus the injected token argument."""
        if self._tools is None:
            result = await self._client.list_tools()
            self._tools = [
                McpTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=_strip_token_arg(tool.input_schema or {}),
                )
                for tool in result.tools
            ]
            logger.info("Calendar MCP tools discovered: %s", [t.name for t in self._tools])
        return self._tools

    async def call_tool(
        self, name: str, arguments: dict[str, Any], *, access_token: str
    ) -> ToolOutcome:
        """Invoke one tool, injecting the student's token. Only transport failures raise."""
        try:
            result = await self._client.call_tool(
                name,
                {**arguments, TOKEN_ARG: access_token},
                read_timeout_seconds=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001 - unknown tool name, or transport failure
            raise CalendarMcpError(f"Calendar MCP call {name!r} failed: {exc}") from exc

        if result.is_error:
            message = _result_text(result)
            return ToolOutcome(
                message,
                True,
                auth_rejected=AUTH_MARKER in message,
                event_gone=EVENT_GONE_MARKER in message,
            )

        if result.structured_content is not None:
            structured = result.structured_content
            # MCPServer wraps a bare list/scalar return in {"result": ...}; unwrap for the model.
            if isinstance(structured, dict) and set(structured) == {"result"}:
                return ToolOutcome(structured["result"], False)
            return ToolOutcome(structured, False)
        return ToolOutcome(_result_text(result), False)


def _result_text(result: Any) -> str:
    parts = [block.text for block in result.content if isinstance(block, TextContent)]
    return "\n".join(parts) if parts else ""
