"""Create optional vector indexes, useful when HNSW was skipped during migration."""
import asyncio

from sqlalchemy import text

from app.core.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_diagnostic_chunks_embedding_hnsw ON diagnostic_chunks USING hnsw (embedding vector_cosine_ops)"))
        await session.commit()
    print("Vector HNSW index ensured. If unsupported, use IVFFlat or sequential vector search as a local fallback.")


if __name__ == "__main__":
    asyncio.run(main())
