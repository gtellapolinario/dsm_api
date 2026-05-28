"""Rebuild chunks for an imported version from stored JSON documents."""
import argparse
import asyncio

from sqlalchemy import delete, select, text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import DiagnosticChunk, DiagnosticDocument
from app.services.chunking import DsmChunkingService


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-id", required=True)
    args = parser.parse_args()
    chunking = DsmChunkingService()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(DiagnosticChunk).where(DiagnosticChunk.version_id == args.version_id))
        docs = (await session.scalars(select(DiagnosticDocument).where(DiagnosticDocument.version_id == args.version_id))).all()
        chunks = []
        for doc in docs:
            for chunk in chunking.build_chunks(doc.document):
                chunks.append(DiagnosticChunk(version_id=args.version_id, document_item_id=doc.item_id, chapter_id=doc.chapter_id, chunk_type=chunk.chunk_type, chunk_title=chunk.chunk_title, chunk_text=chunk.chunk_text, chunk_metadata=chunk.metadata, token_count=len(chunk.chunk_text.split())))
        session.add_all(chunks)
        await session.flush()
        await session.execute(text("UPDATE diagnostic_chunks SET search_vector = to_tsvector(:lang, coalesce(chunk_title,'') || ' ' || chunk_text) WHERE version_id = :version_id"), {"lang": get_settings().fts_language, "version_id": args.version_id})
        await session.commit()
    print(f"Rebuilt chunks: {len(chunks)}")


if __name__ == "__main__":
    asyncio.run(main())
