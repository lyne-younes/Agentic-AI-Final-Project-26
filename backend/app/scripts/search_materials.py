"""Debug CLI for the RAG index: print the chunks a query retrieves from a course.

python -m app.scripts.search_materials COURSE_ID "query" [--tag TAG ...] [--limit N]
"""

import argparse
import asyncio
import textwrap

from app.db import SessionLocal, engine
from app.rag.search import search_materials


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("course_id", type=int)
    parser.add_argument("query")
    parser.add_argument("--tag", action="append", dest="tags", help="pre-filter by tag")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    async with SessionLocal() as db:
        matches = await search_materials(
            db, args.course_id, args.query, tags=args.tags, limit=args.limit
        )
    await engine.dispose()

    if not matches:
        print("No matching chunks. Is the course's material indexed?")
    for rank, match in enumerate(matches, start=1):
        print(
            f"#{rank}  distance={match.distance:.3f}  "
            f"material={match.material_id} ({match.material_title})  chunk={match.chunk_order}"
        )
        print(textwrap.indent(textwrap.shorten(match.chunk_text, width=400), "    "))


if __name__ == "__main__":
    asyncio.run(main())
