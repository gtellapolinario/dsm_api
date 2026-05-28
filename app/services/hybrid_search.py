"""Hybrid full-text and vector search service."""
from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.dsm_chunks import DsmChunkRepository
from app.repositories.dsm_versions import DsmVersionRepository
from app.schemas.search import DsmSearchRequest, DsmSearchResult, DsmSearchResultItem
from app.services.embeddings import EmbeddingService


class HybridSearchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.chunks = DsmChunkRepository(session)
        self.versions = DsmVersionRepository(session)
        self.embeddings = EmbeddingService(self.settings)

    async def search(self, request: DsmSearchRequest) -> DsmSearchResult:
        version_id = await self._resolve_version(request.version_id)
        rows_by_id: dict[str, dict[str, Any]] = {}
        scores: dict[str, dict[str, float | None]] = defaultdict(lambda: {"text_score": None, "vector_score": None})
        if request.use_fts:
            for row in await self.chunks.fts_search(
                version_id=version_id, query=request.query, fts_language=self.settings.fts_language, top_k=request.top_k,
                chapter_id=request.chapter_id, item_id=request.item_id, category=request.category, chunk_types=request.chunk_types,
            ):
                key = str(row["chunk_id"])
                rows_by_id[key] = row
                scores[key]["text_score"] = float(row.get("text_score") or 0)
        if request.use_vector:
            if not self.embeddings.enabled:
                if not request.allow_fallback or not request.use_fts:
                    raise HTTPException(status_code=400, detail="Vector search requested but embeddings are disabled")
            else:
                vectors = await self.embeddings.embed_texts([request.query])
                if vectors:
                    for row in await self.chunks.vector_search(
                        version_id=version_id, embedding=vectors[0], top_k=request.top_k,
                        chapter_id=request.chapter_id, item_id=request.item_id, category=request.category, chunk_types=request.chunk_types,
                    ):
                        key = str(row["chunk_id"])
                        rows_by_id[key] = row
                        scores[key]["vector_score"] = float(row.get("vector_score") or 0)
        items: list[DsmSearchResultItem] = []
        for key, row in rows_by_id.items():
            text_score = scores[key]["text_score"]
            vector_score = scores[key]["vector_score"]
            hybrid = (0.55 * (vector_score or 0)) + (0.45 * (text_score or 0))
            if vector_score is None:
                hybrid = text_score or 0
            if text_score is None:
                hybrid = vector_score or 0
            items.append(
                DsmSearchResultItem(
                    chunk_id=row["chunk_id"], document_item_id=row["document_item_id"], document_name=row.get("document_name"),
                    chapter_id=row["chapter_id"], chunk_type=row["chunk_type"], chunk_title=row.get("chunk_title"),
                    chunk_text=row["chunk_text"], vector_score=vector_score, text_score=text_score, hybrid_score=float(hybrid),
                    metadata=row.get("metadata") or {},
                )
            )
        items.sort(key=lambda item: item.hybrid_score, reverse=True)
        return DsmSearchResult(query=request.query, version_id=version_id, results=items[: request.top_k])

    async def _resolve_version(self, version_id: str) -> str:
        if version_id != "active":
            return version_id
        active = await self.versions.get_active()
        if active is None:
            raise HTTPException(status_code=404, detail="No active DSM version")
        return active.id
