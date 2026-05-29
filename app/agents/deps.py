"""Dependencies and controlled tools for DSM PydanticAI agents."""
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.dsm_documents import DsmDocumentRepository
from app.repositories.dsm_registry import DsmRegistryRepository
from app.repositories.dsm_versions import DsmVersionRepository
from app.schemas.search import DsmSearchRequest, DsmSearchResultItem
from app.services.hybrid_search import HybridSearchService


@dataclass
class DsmAgentDeps:
    session: AsyncSession
    version_id: str = "active"
    query: str = ""
    chapter_id: str | None = None
    item_id: str | None = None
    top_k: int = 8
    use_vector: bool = True
    use_fts: bool = True
    allow_fallback: bool = True

    @property
    def model_name(self) -> str:
        settings = get_settings()
        if settings.llm_provider == "openai":
            return f"openai:{settings.llm_model}"
        return f"{settings.llm_provider}:{settings.llm_model}"


async def search_dsm_chunks(
    deps: DsmAgentDeps,
    query: str | None = None,
    top_k: int | None = None,
    chunk_types: list[str] | None = None,
) -> list[DsmSearchResultItem]:
    """Controlled RAG tool: search DSM chunks for evidence."""
    request = DsmSearchRequest(
        query=query or deps.query,
        version_id=deps.version_id,
        chapter_id=deps.chapter_id,
        item_id=deps.item_id,
        chunk_types=chunk_types,
        top_k=top_k or deps.top_k,
        use_vector=deps.use_vector,
        use_fts=deps.use_fts,
        allow_fallback=deps.allow_fallback,
    )
    result = await HybridSearchService(deps.session).search(request)
    deps.version_id = result.version_id
    return result.results


async def get_dsm_document(deps: DsmAgentDeps, item_id: str) -> dict[str, Any]:
    """Controlled DSM document tool."""
    document = await DsmDocumentRepository(deps.session).get_by_item_id(item_id, deps.version_id)
    if document is None:
        raise HTTPException(status_code=404, detail="DSM document not found")
    return {
        "item_id": document.item_id,
        "name": document.name,
        "chapter_id": document.chapter_id,
        "chapter_name": document.chapter_name,
        "severity_type": document.severity_type,
        "has_formal_severity": document.has_formal_severity,
        "document": document.document,
    }


async def get_current_version(deps: DsmAgentDeps) -> dict[str, Any]:
    """Controlled version tool."""
    version = await DsmVersionRepository(deps.session).get_active()
    if version is None:
        raise HTTPException(status_code=404, detail="No active DSM version")
    deps.version_id = version.id
    return {"id": version.id, "label": version.label, "status": version.status}


async def get_registry_item(deps: DsmAgentDeps, item_id: str) -> dict[str, Any] | None:
    """Controlled registry lookup tool."""
    item = await DsmRegistryRepository(deps.session).get_by_item_id(item_id, deps.version_id)
    if item is None:
        return None
    return {
        "item_id": item.item_id,
        "name": item.name,
        "chapter_id": item.chapter_id,
        "category": item.category,
        "registry_type": item.registry_type,
        "reason": item.reason,
        "document": item.document,
    }
