"""Background job that (re)builds a material's chunks and embeddings."""

import logging

from sqlalchemy import and_, delete, or_, select, update

from app import db as app_db
from app.models import IndexingStatus, Material, MaterialChunk
from app.rag import embeddings
from app.rag.chunking import chunk_text

logger = logging.getLogger(__name__)


async def index_material(material_id: int) -> None:
    # Runs after the response is sent, so it uses its own session rather than the request's.
    async with app_db.SessionLocal() as db:
        material = await db.get(Material, material_id)
        if material is None:
            return  # deleted before the job ran

        try:
            chunks = chunk_text(material.raw_text)
            vectors = await embeddings.embed_texts(chunks) if chunks else []

            await db.execute(delete(MaterialChunk).where(MaterialChunk.material_id == material_id))
            db.add_all(
                MaterialChunk(
                    material_id=material.id,
                    course_id=material.course_id,
                    chunk_text=text,
                    embedding=vector,
                    chunk_order=order,
                )
                for order, (text, vector) in enumerate(zip(chunks, vectors, strict=True))
            )
            material.indexing_status = IndexingStatus.indexed
            material.embedding_model = embeddings.EMBEDDING_MODEL
            await db.commit()
        except Exception:
            # A failed job must not leave the material stuck at "pending"; the UI offers a retry.
            logger.exception("Indexing material %s failed", material_id)
            await db.rollback()
            await _mark_failed(material_id)


async def reindex_outdated_materials() -> int:
    """Startup job: re-index materials built with another embedding model or left `pending`.

    Returns how many were re-indexed.
    """
    try:
        async with app_db.SessionLocal() as db:
            outdated = list(
                await db.scalars(
                    select(Material.id).where(
                        or_(
                            Material.indexing_status == IndexingStatus.pending,
                            and_(
                                Material.indexing_status == IndexingStatus.indexed,
                                or_(
                                    Material.embedding_model.is_(None),
                                    Material.embedding_model != embeddings.EMBEDDING_MODEL,
                                ),
                            ),
                        )
                    )
                )
            )
            if not outdated:
                return 0
            # Search skips pending materials, so old vectors are never mixed with new query vectors.
            await db.execute(
                update(Material)
                .where(Material.id.in_(outdated))
                .values(indexing_status=IndexingStatus.pending)
            )
            await db.commit()

        logger.info("Re-indexing %d material(s) with %s", len(outdated), embeddings.EMBEDDING_MODEL)
        for material_id in outdated:  # one at a time, to stay well under API rate limits
            await index_material(material_id)
        return len(outdated)
    except Exception:
        logger.exception("Re-indexing outdated materials failed")
        return 0


async def _mark_failed(material_id: int) -> None:
    async with app_db.SessionLocal() as db:
        material = await db.get(Material, material_id)
        if material is not None:
            material.indexing_status = IndexingStatus.failed
            await db.commit()
