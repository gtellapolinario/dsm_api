"""Optional DSM graph agent endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import GraphAgentDeps
from app.agents.graph_audit_agent import audit_graph
from app.agents.graph_clinical_relation_agent import answer_clinical_relations
from app.agents.graph_query_planner_agent import plan_graph_query
from app.agents.graph_schemas import GraphAgentAnswer, GraphAuditResult, GraphQueryPlan
from app.agents.graph_traversal_agent import answer_graph_traversal
from app.core.config import get_settings
from app.core.database import get_session
from app.services.graph_service import DsmGraphService
from app.services.hybrid_search import HybridSearchService

router = APIRouter(prefix="/api/dsm/graph/agents", tags=["dsm-graph-agents"])


class GraphAgentAskRequest(BaseModel):
    query: str = Field(min_length=1)
    version_id: str = "active"
    limit: int = Field(default=20, ge=1, le=100)


class GraphClinicalRelationsRequest(GraphAgentAskRequest):
    allow_hybrid_search: bool = True


class GraphAuditRequest(BaseModel):
    version_id: str = "active"


class GraphPlanQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    version_id: str = "active"


def _ensure_agents_enabled() -> None:
    settings = get_settings()
    if not settings.agents_enabled or not settings.graph_agent_enabled:
        raise HTTPException(status_code=503, detail="Agents are disabled.")


def _deps(session: AsyncSession, version_id: str, include_search: bool = False) -> GraphAgentDeps:
    return GraphAgentDeps(
        session=session,
        version_id=version_id,
        graph_service=DsmGraphService(session),
        search_service=HybridSearchService(session) if include_search else None,
    )


@router.post("/ask", response_model=GraphAgentAnswer)
async def ask(request: GraphAgentAskRequest, session: AsyncSession = Depends(get_session)):
    _ensure_agents_enabled()
    return await answer_graph_traversal(_deps(session, request.version_id), request.query, request.limit)


@router.post("/clinical-relations", response_model=GraphAgentAnswer)
async def clinical_relations(request: GraphClinicalRelationsRequest, session: AsyncSession = Depends(get_session)):
    _ensure_agents_enabled()
    return await answer_clinical_relations(
        _deps(session, request.version_id, include_search=request.allow_hybrid_search),
        request.query,
        request.limit,
        request.allow_hybrid_search,
    )


@router.post("/audit", response_model=GraphAuditResult)
async def audit(request: GraphAuditRequest, session: AsyncSession = Depends(get_session)):
    _ensure_agents_enabled()
    return await audit_graph(_deps(session, request.version_id))


@router.post("/plan-query", response_model=GraphQueryPlan)
async def plan_query(request: GraphPlanQueryRequest):
    _ensure_agents_enabled()
    return plan_graph_query(request.query, request.version_id)
