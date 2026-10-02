"""Check that the backend can reach the Calendar MCP server.

    docker compose exec backend python -m app.scripts.check_calendar_mcp
    docker compose exec backend python -m app.scripts.check_calendar_mcp --email you@gmail.com

Lists the server's tools. With `--email`, also refreshes that user's Google token and makes one
read-only `get_calendar_events` call for the next 7 days.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.auth.tokens import get_valid_google_access_token
from app.config import get_settings
from app.db import SessionLocal
from app.mcp import calendar
from app.models import User


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Also make one real read-only call as this student")
    args = parser.parse_args()

    print(f"Calendar MCP URL: {get_settings().calendar_mcp_url}")

    async with calendar.session() as mcp:
        tools = await mcp.list_tools()
        print(f"\nTools advertised over MCP ({len(tools)}):")
        for tool in tools:
            params = ", ".join(tool.input_schema.get("properties", {}))
            first_line = tool.description.splitlines()[0] if tool.description else ""
            print(f"  - {tool.name}({params})")
            print(f"      {first_line}")

        if not args.email:
            print("\nHandshake OK. Pass --email to also make a real Calendar read.")
            return

        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.email == args.email))
            if user is None:
                print(f"\nNo user with email {args.email!r}; sign in through the app first.")
                return
            token = await get_valid_google_access_token(db, user)

        now = datetime.now(UTC)
        outcome = await mcp.call_tool(
            "get_calendar_events",
            {
                "time_min": now.isoformat(),
                "time_max": (now + timedelta(days=7)).isoformat(),
            },
            access_token=token,
        )
        if outcome.is_error:
            print(f"\nTool call failed: {outcome.content}")
            return
        events = outcome.content
        print(f"\nEvents in the next 7 days for {args.email}: {len(events)}")
        for event in events[:10]:
            marker = " [study session]" if event.get("study_session") else ""
            print(f"  - {event['start']}  {event['title']}{marker}")


if __name__ == "__main__":
    asyncio.run(main())
