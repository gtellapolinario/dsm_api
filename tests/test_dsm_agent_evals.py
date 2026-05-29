import asyncio
from uuid import uuid4

import pytest

from app.agents.schemas import DsmAnswerRequest, DsmCriticRequest, DsmInterviewPlanRequest
from app.schemas.search import DsmSearchResult, DsmSearchResultItem
from app.services import dsm_agent_service
from app.services.dsm_agent_service import DsmAgentService

CASES = [
    ("tique transitório <1 ano", "Tique transitório exige duração inferior a 1 ano.", "duration"),
    ("cleptomania sem gravidade formal", "Cleptomania não possui gravidade formal operacionalizada.", "severity"),
    ("DI gravidade por funcionamento adaptativo", "Deficiência intelectual: gravidade pelo funcionamento adaptativo.", "severity"),
    ("TEA gravidade por domínio", "TEA: gravidade especificada por domínio social e comportamentos restritos/repetitivos.", "severity"),
    ("TOD gravidade por ambientes", "TOD: gravidade relacionada ao número de ambientes.", "severity"),
]


def chunk(text: str, chunk_type: str) -> DsmSearchResultItem:
    return DsmSearchResultItem(
        chunk_id=str(uuid4()),
        document_item_id="eval_item",
        document_name="Eval",
        chapter_id="01",
        chunk_type=chunk_type,
        chunk_title="Eval chunk",
        chunk_text=text,
        hybrid_score=0.6,
        metadata={},
    )


@pytest.mark.parametrize(("query", "text", "chunk_type"), CASES)
def test_agent_answer_evals_use_chunks_and_limitations(monkeypatch, query, text, chunk_type):
    async def search_stub(self, request):
        return DsmSearchResult(query=request.query, version_id="v_eval", results=[chunk(text, chunk_type)])

    monkeypatch.setattr(dsm_agent_service.HybridSearchService, "search", search_stub)
    response = asyncio.run(DsmAgentService(session=None).answer(DsmAnswerRequest(query=query, use_vector=False)))  # type: ignore[arg-type]

    assert response.version_id == "v_eval"
    assert response.output.used_chunks
    assert response.output.limitations
    assert response.output.confidence > 0
    assert response.observability.used_chunks == response.output.used_chunks


def test_interview_plan_eval_has_source_chunk(monkeypatch):
    async def search_stub(self, request):
        return DsmSearchResult(query=request.query, version_id="v_eval", results=[chunk("TOD gravidade por ambientes.", "severity")])

    monkeypatch.setattr(dsm_agent_service.HybridSearchService, "search", search_stub)
    response = asyncio.run(DsmAgentService(session=None).interview_plan(DsmInterviewPlanRequest(query="TOD gravidade por ambientes", use_vector=False)))  # type: ignore[arg-type]

    assert response.output.used_chunks
    assert response.output.questions[0].source_chunk_id == response.output.used_chunks[0].chunk_id


def test_critic_eval_requires_chunks(monkeypatch):
    async def search_stub(self, request):
        return DsmSearchResult(query=request.query, version_id="v_eval", results=[])

    monkeypatch.setattr(dsm_agent_service.HybridSearchService, "search", search_stub)
    response = asyncio.run(
        DsmAgentService(session=None).critic(  # type: ignore[arg-type]
            DsmCriticRequest(query="cleptomania sem gravidade formal", report_text="Paciente com gravidade formal grave.", use_vector=False)
        )
    )

    assert response.output.confidence == 0
    assert not response.output.used_chunks
    assert "ausência de evidência" in response.output.summary
