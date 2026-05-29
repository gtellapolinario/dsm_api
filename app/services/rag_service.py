"""RAG retrieval and answer service."""
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.rag import DsmRagCitation, DsmRagRequest, DsmRagResponse
from app.schemas.search import DsmSearchRequest
from app.services.hybrid_search import HybridSearchService

logger = logging.getLogger(__name__)


class DsmRagService:
    def __init__(self, session: AsyncSession):
        self.settings = get_settings()
        self.search = HybridSearchService(session)

    async def retrieve(self, request: DsmRagRequest) -> DsmRagResponse:
        started = time.perf_counter()
        result = await self.search.search(self._to_search_request(request))
        citations = [
            DsmRagCitation(
                document_item_id=item.document_item_id,
                chunk_id=str(item.chunk_id),
                chunk_type=item.chunk_type,
                chunk_title=item.chunk_title,
            )
            for item in result.results
        ]
        logger.info("dsm_rag_retrieve_completed", extra={"duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        return DsmRagResponse(question=request.question, version_id=result.version_id, chunks=result.results, citations=citations)

    async def answer(self, request: DsmRagRequest) -> DsmRagResponse:
        response = await self.retrieve(request)
        if not response.chunks:
            response.message = "Sem evidência recuperada suficiente; a API não gera resposta sem chunks citados."
            return response
        if not self.settings.rag_answer_enabled:
            response.message = "RAG answer disabled. Retrieval results returned."
            return response
        response.answer = self._extractive_answer(request.question, response.chunks)
        return response

    def _to_search_request(self, request: DsmRagRequest) -> DsmSearchRequest:
        return DsmSearchRequest(
            query=request.question, version_id=request.version_id, chapter_id=request.chapter_id, item_id=request.item_id,
            chunk_types=request.chunk_types, top_k=request.top_k, use_vector=request.use_vector, use_fts=request.use_fts,
            allow_fallback=request.allow_fallback,
        )

    def _extractive_answer(self, question, chunks):
        used = ", ".join(f"{c.document_item_id}/{c.chunk_type}" for c in chunks[:5])
        evidence = "\n\n".join(c.chunk_text for c in chunks[:3])
        return (
            "Resposta baseada exclusivamente nos chunks recuperados; não substitui julgamento clínico.\n"
            f"Pergunta: {question}\nChunks usados: {used}\nEvidência:\n{evidence}"
        )
