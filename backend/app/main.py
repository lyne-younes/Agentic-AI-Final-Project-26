import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.courses.router import router as courses_router
from app.flashcards.router import router as flashcards_router
from app.materials.router import router as materials_router
from app.quizzes.router import router as quizzes_router
from app.rag import indexing
from app.summaries.router import router as summaries_router

# Show the app's INFO logs; quiet the noisy LiteLLM and httpx loggers.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")
for noisy in ("LiteLLM", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Re-index outdated materials in the background.
    reindexing = asyncio.create_task(indexing.reindex_outdated_materials())
    yield
    reindexing.cancel()


app = FastAPI(title="Agentic Study Assistant", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(materials_router)
app.include_router(chat_router)
app.include_router(summaries_router)
app.include_router(quizzes_router)
app.include_router(flashcards_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
