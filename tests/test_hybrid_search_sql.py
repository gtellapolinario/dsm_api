from types import SimpleNamespace

import pytest

from app.repositories import dsm_chunks, dsm_versions
from app.schemas.search import DsmSearchRequest
from app.services.hybrid_search import HybridSearchService


@pytest.mark.asyncio
async def test_busca_textual_retorna_chunk_esperado(monkeypatch):
    async def active_stub(self):
        return SimpleNamespace(id="v1")

    async def fts_stub(self, **kwargs):
        return [{
            "chunk_id": "c1", "document_item_id": "tourette", "document_name": "Tourette", "chapter_id": "01",
            "chunk_type": "critical_differentials", "chunk_title": "Tourette — diferenciais", "chunk_text": "Diferenciar de tique transitório.",
            "metadata": {}, "text_score": 0.5,
        }]

    monkeypatch.setattr(dsm_versions.DsmVersionRepository, "get_active", active_stub)
    monkeypatch.setattr(dsm_chunks.DsmChunkRepository, "fts_search", fts_stub)
    result = await HybridSearchService(session=None).search(DsmSearchRequest(query="tique", use_vector=False))  # type: ignore[arg-type]
    assert result.results[0].document_item_id == "tourette"
