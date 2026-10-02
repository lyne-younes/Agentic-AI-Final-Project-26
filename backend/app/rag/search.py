"""Course-scoped similarity search over material_chunks."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IndexingStatus, Material, MaterialChunk
from app.rag import embeddings


@dataclass(frozen=True)
class ChunkMatch:
    material_id: int  # source traceability: every chunk maps back to its material
    material_title: str
    chunk_text: str
    chunk_order: int
    distance: float


async def search_materials(
    db: AsyncSession,
    course_id: int,
    query: str,
    *,
    tags: list[str] | None = None,
    limit: int = 5,
) -> list[ChunkMatch]:
    [query_vector] = await embeddings.embed_texts([query])
    distance = MaterialChunk.embedding.cosine_distance(query_vector)

    statement = (
        select(MaterialChunk, Material.title, distance.label("distance"))
        .join(Material, Material.id == MaterialChunk.material_id)
        # Only fully indexed materials (pending ones may hold outdated vectors).
        .where(
            MaterialChunk.course_id == course_id,
            Material.indexing_status == IndexingStatus.indexed,
        )
        .order_by(distance)
        .limit(limit)
    )
    if tags:
        # Tags only narrow the candidate pool; similarity still ranks what's left.
        statement = statement.where(Material.tags.overlap(tags))

    rows = await db.execute(statement)
    return [
        ChunkMatch(
            material_id=chunk.material_id,
            material_title=title,
            chunk_text=chunk.chunk_text,
            chunk_order=chunk.chunk_order,
            distance=float(chunk_distance),
        )
        for chunk, title, chunk_distance in rows.all()
    ]
