"""PydanticAI agent for DSM RAG answers."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.agents.deps import (
    DsmAgentDeps,
)
from app.agents.deps import (
    get_current_version as _get_current_version,
)
from app.agents.deps import (
    get_dsm_document as _get_dsm_document,
)
from app.agents.deps import (
    get_registry_item as _get_registry_item,
)
from app.agents.deps import (
    search_dsm_chunks as _search_dsm_chunks,
)
from app.agents.schemas import DsmAnswerOutput

if TYPE_CHECKING:  # pragma: no cover
    from pydantic_ai import Agent as PydanticAgent


SYSTEM_PROMPT = """
Você é um agente DSM para apoio clínico. Responda somente com base nos chunks DSM recuperados.
Use apenas as ferramentas controladas: search_dsm_chunks, get_dsm_document, get_current_version e get_registry_item.
Guardrails obrigatórios:
- Nunca responda pergunta DSM sem evidência de chunks.
- Nunca invente critério, gravidade formal, duração ou exclusão diagnóstica.
- Sempre preencha used_chunks com os chunks efetivamente usados.
- Declare limitação quando a recuperação for fraca, ambígua ou insuficiente.
- Diferencie texto clínico de diagnóstico definitivo; não substitui julgamento clínico.
"""


def create_answer_agent(model: str) -> PydanticAgent[DsmAgentDeps, DsmAnswerOutput] | None:
    try:
        from pydantic_ai import Agent, RunContext
    except ModuleNotFoundError:
        return None

    agent = Agent(model, deps_type=DsmAgentDeps, output_type=DsmAnswerOutput, instructions=SYSTEM_PROMPT)

    @agent.tool
    async def search_dsm_chunks(ctx: RunContext[DsmAgentDeps], query: str | None = None, top_k: int | None = None) -> list[dict]:
        """Search DSM chunks for evidence."""
        chunks = await _search_dsm_chunks(ctx.deps, query, top_k)
        return [chunk.model_dump(mode="json") for chunk in chunks]

    @agent.tool
    async def get_dsm_document(ctx: RunContext[DsmAgentDeps], item_id: str) -> dict:
        """Get a renderable DSM document by item_id."""
        return await _get_dsm_document(ctx.deps, item_id)

    @agent.tool
    async def get_current_version(ctx: RunContext[DsmAgentDeps]) -> dict:
        """Get the active DSM version."""
        return await _get_current_version(ctx.deps)

    @agent.tool
    async def get_registry_item(ctx: RunContext[DsmAgentDeps], item_id: str) -> dict | None:
        """Get a DSM registry entry by item_id."""
        return await _get_registry_item(ctx.deps, item_id)

    return agent
