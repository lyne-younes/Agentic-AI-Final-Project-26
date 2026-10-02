"""OpenAI embeddings, kept separate from the swappable chat model."""

import openai

from app.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-large"
# Shortened to 1536 dimensions to match the vector(1536) column (HNSW allows at most 2000).
# Changing the model re-indexes all materials at startup; a new size needs a migration.
EMBEDDING_DIMENSIONS = 1536
_BATCH_SIZE = 100


class EmbeddingError(Exception):
    pass


async def embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = get_settings().openai_api_key
    if not api_key:
        raise EmbeddingError("OPENAI_API_KEY is not set")

    vectors: list[list[float]] = []
    try:
        async with openai.AsyncOpenAI(api_key=api_key) as client:
            for start in range(0, len(texts), _BATCH_SIZE):
                response = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts[start : start + _BATCH_SIZE],
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                ordered = sorted(response.data, key=lambda item: item.index)
                vectors.extend(item.embedding for item in ordered)
    except openai.OpenAIError as exc:
        raise EmbeddingError(f"OpenAI embeddings request failed: {exc}") from exc
    return vectors
