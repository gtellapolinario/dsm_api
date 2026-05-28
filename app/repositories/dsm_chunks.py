"""Repository for DSM chunks and search SQL."""
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticChunk


class DsmChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_add(self, chunks: list[DiagnosticChunk]) -> None:
        self.session.add_all(chunks)
        await self.session.flush()

    async def fts_search(
        self,
        *,
        version_id: str,
        query: str,
        fts_language: str,
        top_k: int,
        chapter_id: str | None = None,
        item_id: str | None = None,
        category: str | None = None,
        chunk_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
        SELECT c.id AS chunk_id, c.document_item_id, d.name AS document_name, c.chapter_id,
               c.chunk_type, c.chunk_title, c.chunk_text, c.metadata,
               ts_rank_cd(c.search_vector, plainto_tsquery(:lang, :query)) AS text_score
        FROM diagnostic_chunks c
        LEFT JOIN diagnostic_documents d ON d.version_id = c.version_id AND d.item_id = c.document_item_id
        WHERE c.version_id = :version_id
          AND c.search_vector @@ plainto_tsquery(:lang, :query)
        """
        params: dict[str, Any] = {"version_id": version_id, "query": query, "lang": fts_language, "top_k": top_k}
        if chapter_id:
            sql += " AND c.chapter_id = :chapter_id"
            params["chapter_id"] = chapter_id
        if item_id:
            sql += " AND c.document_item_id = :item_id"
            params["item_id"] = item_id
        if category:
            sql += " AND d.category = :category"
            params["category"] = category
        if chunk_types:
            sql += " AND c.chunk_type = ANY(:chunk_types)"
            params["chunk_types"] = chunk_types
        sql += " ORDER BY text_score DESC LIMIT :top_k"
        return [dict(row._mapping) for row in (await self.session.execute(text(sql), params)).all()]

    async def vector_search(self, *, version_id: str, embedding: list[float], top_k: int, **filters: Any) -> list[dict[str, Any]]:
        sql = """
        SELECT c.id AS chunk_id, c.document_item_id, d.name AS document_name, c.chapter_id,
               c.chunk_type, c.chunk_title, c.chunk_text, c.metadata,
               1 - (c.embedding <=> :embedding) AS vector_score
        FROM diagnostic_chunks c
        LEFT JOIN diagnostic_documents d ON d.version_id = c.version_id AND d.item_id = c.document_item_id
        WHERE c.version_id = :version_id AND c.embedding IS NOT NULL
        """
        params: dict[str, Any] = {"version_id": version_id, "embedding": str(embedding), "top_k": top_k}
        if filters.get("chapter_id"):
            sql += " AND c.chapter_id = :chapter_id"
            params["chapter_id"] = filters["chapter_id"]
        if filters.get("item_id"):
            sql += " AND c.document_item_id = :item_id"
            params["item_id"] = filters["item_id"]
        if filters.get("category"):
            sql += " AND d.category = :category"
            params["category"] = filters["category"]
        if filters.get("chunk_types"):
            sql += " AND c.chunk_type = ANY(:chunk_types)"
            params["chunk_types"] = filters["chunk_types"]
        sql += " ORDER BY c.embedding <=> :embedding LIMIT :top_k"
        return [dict(row._mapping) for row in (await self.session.execute(text(sql), params)).all()]

    async def list_by_version(self, version_id: str) -> list[DiagnosticChunk]:
        return list((await self.session.scalars(select(DiagnosticChunk).where(DiagnosticChunk.version_id == version_id))).all())
