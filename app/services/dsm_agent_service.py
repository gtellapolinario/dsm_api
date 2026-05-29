"""Agentic DSM service with deterministic API contracts."""
from __future__ import annotations

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import DsmAgentDeps
from app.agents.dsm_answer_agent import create_answer_agent
from app.agents.dsm_critic_agent import create_critic_agent
from app.agents.dsm_interview_agent import create_interview_agent
from app.agents.schemas import (
    AgentObservability,
    ChunkExplanation,
    DsmAgentResponse,
    DsmAnswerOutput,
    DsmAnswerRequest,
    DsmCriticIssue,
    DsmCriticOutput,
    DsmCriticRequest,
    DsmInterviewPlanOutput,
    DsmInterviewPlanRequest,
    InterviewQuestion,
    UsedChunk,
)
from app.core.config import get_settings
from app.schemas.search import DsmSearchRequest, DsmSearchResultItem
from app.services.hybrid_search import HybridSearchService

logger = logging.getLogger(__name__)
WEAK_RETRIEVAL_THRESHOLD = 0.05


class DsmAgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.search = HybridSearchService(session)
        self._last_usage: dict[str, int | float | None] = {}

    async def answer(self, request: DsmAnswerRequest) -> DsmAgentResponse:
        started = time.perf_counter()
        chunks, version_id = await self._retrieve(request)
        deps = self._deps(request, version_id)
        if not chunks:
            output = self._no_evidence_answer("Não há chunks DSM recuperados para responder com segurança.")
            return self._response(request.query, version_id, output, chunks, started)
        prompt = (
            f"Pergunta: {request.query}\nPúblico: {request.audience}\n"
            f"Use estes chunks já recuperados como evidência obrigatória:\n{self._chunks_prompt(chunks)}"
        )
        output = await self._run_answer_agent(prompt, deps, chunks, request)
        output = self._guard_answer(output, chunks)
        return self._response(request.query, version_id, output, chunks, started)

    async def interview_plan(self, request: DsmInterviewPlanRequest) -> DsmAgentResponse:
        started = time.perf_counter()
        chunks, version_id = await self._retrieve(request)
        deps = self._deps(request, version_id)
        if not chunks:
            output = DsmInterviewPlanOutput(
                plan_title="Plano indisponível por ausência de evidência DSM",
                questions=[],
                limitations=["Não há chunks DSM recuperados para montar plano de entrevista com segurança."],
                confidence=0,
                used_chunks=[],
            )
            return self._response(request.query, version_id, output, chunks, started)
        prompt = (
            f"Monte plano de entrevista para: {request.query}\nContexto clínico: {request.clinical_context or 'não informado'}\n"
            f"Chunks obrigatórios:\n{self._chunks_prompt(chunks)}"
        )
        output = await self._run_interview_agent(prompt, deps, chunks, request)
        output = self._guard_interview(output, chunks)
        return self._response(request.query, version_id, output, chunks, started)

    async def critic(self, request: DsmCriticRequest) -> DsmAgentResponse:
        started = time.perf_counter()
        chunks, version_id = await self._retrieve(request)
        deps = self._deps(request, version_id)
        if not chunks:
            output = DsmCriticOutput(
                summary="Revisão indisponível por ausência de evidência DSM recuperada.",
                limitations=["Não há chunks DSM recuperados para revisar relatório com segurança."],
                confidence=0,
                used_chunks=[],
            )
            return self._response(request.query, version_id, output, chunks, started)
        prompt = (
            f"Tarefa: {request.query}\nRelatório a revisar/redigir:\n{request.report_text}\n"
            f"Chunks obrigatórios:\n{self._chunks_prompt(chunks)}"
        )
        output = await self._run_critic_agent(prompt, deps, chunks, request)
        output = self._guard_critic(output, chunks)
        return self._response(request.query, version_id, output, chunks, started)

    async def _retrieve(self, request: DsmAnswerRequest | DsmInterviewPlanRequest | DsmCriticRequest) -> tuple[list[DsmSearchResultItem], str]:
        result = await self.search.search(
            DsmSearchRequest(
                query=request.query,
                version_id=request.version_id,
                chapter_id=request.chapter_id,
                item_id=request.item_id,
                top_k=request.top_k,
                use_vector=request.use_vector,
                use_fts=request.use_fts,
                allow_fallback=request.allow_fallback,
            )
        )
        return result.results, result.version_id

    def _deps(self, request: DsmAnswerRequest | DsmInterviewPlanRequest | DsmCriticRequest, version_id: str) -> DsmAgentDeps:
        return DsmAgentDeps(
            session=self.session,
            version_id=version_id,
            query=request.query,
            chapter_id=request.chapter_id,
            item_id=request.item_id,
            top_k=request.top_k,
            use_vector=request.use_vector,
            use_fts=request.use_fts,
            allow_fallback=request.allow_fallback,
        )

    async def _run_answer_agent(self, prompt: str, deps: DsmAgentDeps, chunks: list[DsmSearchResultItem], request: DsmAnswerRequest) -> DsmAnswerOutput:
        agent = create_answer_agent(deps.model_name)
        if agent is None or not self.settings.openai_api_key:
            self._last_usage = {}
            return self._fallback_answer(request.query, chunks)
        result = await agent.run(prompt, deps=deps)
        self._last_usage = self._usage_to_dict(getattr(result, "usage", None))
        return result.output

    async def _run_interview_agent(self, prompt: str, deps: DsmAgentDeps, chunks: list[DsmSearchResultItem], request: DsmInterviewPlanRequest) -> DsmInterviewPlanOutput:
        agent = create_interview_agent(deps.model_name)
        if agent is None or not self.settings.openai_api_key:
            self._last_usage = {}
            return self._fallback_interview(request.query, chunks)
        result = await agent.run(prompt, deps=deps)
        self._last_usage = self._usage_to_dict(getattr(result, "usage", None))
        return result.output

    async def _run_critic_agent(self, prompt: str, deps: DsmAgentDeps, chunks: list[DsmSearchResultItem], request: DsmCriticRequest) -> DsmCriticOutput:
        agent = create_critic_agent(deps.model_name)
        if agent is None or not self.settings.openai_api_key:
            self._last_usage = {}
            return self._fallback_critic(request.query, chunks, request.report_text)
        result = await agent.run(prompt, deps=deps)
        self._last_usage = self._usage_to_dict(getattr(result, "usage", None))
        return result.output

    def _fallback_answer(self, query: str, chunks: list[DsmSearchResultItem]) -> DsmAnswerOutput:
        evidence = "\n\n".join(chunk.chunk_text for chunk in chunks[:3])
        return DsmAnswerOutput(
            answer=(
                "Resposta baseada exclusivamente nos chunks recuperados; não substitui julgamento clínico.\n"
                f"Pergunta: {query}\nEvidência resumida:\n{evidence}"
            ),
            limitations=self._limitations(chunks),
            confidence=self._confidence(chunks),
            used_chunks=self._used_chunks(chunks),
            chunk_explanations=[
                ChunkExplanation(chunk_id=str(chunk.chunk_id), contribution=f"Evidência de {chunk.chunk_type}: {chunk.chunk_title or chunk.document_name or chunk.document_item_id}")
                for chunk in chunks[:5]
            ],
        )

    def _fallback_interview(self, query: str, chunks: list[DsmSearchResultItem]) -> DsmInterviewPlanOutput:
        questions = [
            InterviewQuestion(
                order=index + 1,
                question=f"Explorar {chunk.chunk_title or chunk.chunk_type}: {self._shorten(chunk.chunk_text)}",
                target_criterion=chunk.chunk_type,
                source_chunk_id=str(chunk.chunk_id),
            )
            for index, chunk in enumerate(chunks[:6])
        ]
        return DsmInterviewPlanOutput(
            plan_title=f"Plano de entrevista DSM — {query}",
            questions=questions,
            limitations=self._limitations(chunks),
            confidence=self._confidence(chunks),
            used_chunks=self._used_chunks(chunks),
        )

    def _fallback_critic(self, query: str, chunks: list[DsmSearchResultItem], report_text: str) -> DsmCriticOutput:
        issues = [
            DsmCriticIssue(
                severity="medium",
                issue=f"Verificar alinhamento do relatório com {chunk.chunk_title or chunk.chunk_type}.",
                recommendation="Ajustar afirmações diagnósticas para refletirem apenas critérios presentes na evidência recuperada.",
                source_chunk_id=str(chunk.chunk_id),
            )
            for chunk in chunks[:3]
        ]
        return DsmCriticOutput(
            summary=f"Revisão DSM baseada em chunks recuperados para: {query}.",
            issues=issues,
            revised_clinical_text=(
                "Texto clínico sugerido, condicionado à confirmação em entrevista: "
                f"{self._shorten(report_text, 700)}"
            ),
            limitations=self._limitations(chunks),
            confidence=self._confidence(chunks),
            used_chunks=self._used_chunks(chunks),
        )

    def _no_evidence_answer(self, message: str) -> DsmAnswerOutput:
        return DsmAnswerOutput(answer=message, limitations=[message], confidence=0, used_chunks=[], chunk_explanations=[])

    def _guard_answer(self, output: DsmAnswerOutput, chunks: list[DsmSearchResultItem]) -> DsmAnswerOutput:
        output.used_chunks = self._ensure_used_chunks(output.used_chunks, chunks)
        output.confidence = min(output.confidence, self._confidence(chunks))
        output.limitations = self._ensure_limitations(output.limitations, chunks)
        return output

    def _guard_interview(self, output: DsmInterviewPlanOutput, chunks: list[DsmSearchResultItem]) -> DsmInterviewPlanOutput:
        output.used_chunks = self._ensure_used_chunks(output.used_chunks, chunks)
        output.confidence = min(output.confidence, self._confidence(chunks))
        output.limitations = self._ensure_limitations(output.limitations, chunks)
        return output

    def _guard_critic(self, output: DsmCriticOutput, chunks: list[DsmSearchResultItem]) -> DsmCriticOutput:
        output.used_chunks = self._ensure_used_chunks(output.used_chunks, chunks)
        output.confidence = min(output.confidence, self._confidence(chunks))
        output.limitations = self._ensure_limitations(output.limitations, chunks)
        return output

    def _ensure_used_chunks(self, used_chunks: list[UsedChunk], chunks: list[DsmSearchResultItem]) -> list[UsedChunk]:
        allowed = {str(chunk.chunk_id) for chunk in chunks}
        filtered = [chunk for chunk in used_chunks if chunk.chunk_id in allowed]
        return filtered or self._used_chunks(chunks)

    def _ensure_limitations(self, limitations: list[str], chunks: list[DsmSearchResultItem]) -> list[str]:
        merged = list(limitations)
        for limitation in self._limitations(chunks):
            if limitation not in merged:
                merged.append(limitation)
        return merged

    def _limitations(self, chunks: list[DsmSearchResultItem]) -> list[str]:
        if not chunks:
            return ["Não há chunks DSM recuperados; a resposta não deve inferir critérios."]
        if max(chunk.hybrid_score for chunk in chunks) < WEAK_RETRIEVAL_THRESHOLD:
            return ["Recuperação fraca: use a resposta apenas como hipótese orientada por evidência parcial."]
        return ["Resposta limitada aos chunks recuperados; não substitui avaliação clínica completa."]

    def _confidence(self, chunks: list[DsmSearchResultItem]) -> float:
        if not chunks:
            return 0
        best = max(chunk.hybrid_score for chunk in chunks)
        if best < WEAK_RETRIEVAL_THRESHOLD:
            return 0.25
        return min(0.9, 0.45 + best)

    def _used_chunks(self, chunks: list[DsmSearchResultItem]) -> list[UsedChunk]:
        return [
            UsedChunk(
                chunk_id=str(chunk.chunk_id),
                document_item_id=chunk.document_item_id,
                chapter_id=chunk.chapter_id,
                chunk_type=chunk.chunk_type,
                chunk_title=chunk.chunk_title,
                hybrid_score=chunk.hybrid_score,
            )
            for chunk in chunks[:8]
        ]

    def _response(self, query: str, version_id: str, output: DsmAnswerOutput | DsmInterviewPlanOutput | DsmCriticOutput, chunks: list[DsmSearchResultItem], started: float) -> DsmAgentResponse:
        response_time_ms = int((time.perf_counter() - started) * 1000)
        observability = AgentObservability(
            query=query,
            used_chunks=output.used_chunks,
            dsm_version=version_id,
            model=self._model_name(),
            input_tokens=self._last_usage.get("input_tokens"),
            output_tokens=self._last_usage.get("output_tokens"),
            total_tokens=self._last_usage.get("total_tokens"),
            cost=self._last_usage.get("cost"),
            confidence=output.confidence,
            response_time_ms=response_time_ms,
        )
        logger.info(
            "dsm_agent_response",
            extra={
                "query": query,
                "chunks_used": [chunk.chunk_id for chunk in output.used_chunks],
                "dsm_version": version_id,
                "model": observability.model,
                "input_tokens": observability.input_tokens,
                "output_tokens": observability.output_tokens,
                "total_tokens": observability.total_tokens,
                "cost": observability.cost,
                "confidence": output.confidence,
                "response_time_ms": response_time_ms,
            },
        )
        return DsmAgentResponse(query=query, version_id=version_id, output=output, chunks=chunks, observability=observability)

    def _usage_to_dict(self, usage) -> dict[str, int | float | None]:
        if usage is None:
            return {}
        if callable(usage):
            usage = usage()
        data = usage if isinstance(usage, dict) else getattr(usage, "__dict__", {})
        input_tokens = data.get("input_tokens") or data.get("request_tokens")
        output_tokens = data.get("output_tokens") or data.get("response_tokens")
        total_tokens = data.get("total_tokens")
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": data.get("cost"),
        }

    def _model_name(self) -> str:
        if self.settings.llm_provider == "openai":
            return f"openai:{self.settings.llm_model}"
        return f"{self.settings.llm_provider}:{self.settings.llm_model}"

    def _chunks_prompt(self, chunks: list[DsmSearchResultItem]) -> str:
        return "\n\n".join(
            f"chunk_id={chunk.chunk_id}; item={chunk.document_item_id}; type={chunk.chunk_type}; score={chunk.hybrid_score}\n{chunk.chunk_text}"
            for chunk in chunks[:8]
        )

    def _shorten(self, text: str, max_len: int = 240) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 1] + "…"
