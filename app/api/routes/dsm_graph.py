"""Derived DSM knowledge graph API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import require_admin_token
from app.graph.schemas import GraphQueryRequest, GraphRebuildRequest
from app.services.graph_service import DsmGraphService

router = APIRouter(prefix="/api/dsm/graph", tags=["dsm-graph"])


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)):
    return await DsmGraphService(session).get_status()


@router.post("/rebuild", dependencies=[Depends(require_admin_token)])
async def rebuild(request: GraphRebuildRequest, session: AsyncSession = Depends(get_session)):
    graph, graph_path, graphify = await DsmGraphService(session).export_graph(
        version_id=request.version_id,
        persist=request.persist,
        send_to_graphify=request.send_to_graphify,
    )
    return {
        "version_id": graph.version_id,
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "warnings": graph.warnings,
        "graph_path": str(graph_path) if graph_path else None,
        "graphify": graphify,
    }


@router.get("/export")
async def export(version_id: str = "active", session: AsyncSession = Depends(get_session)):
    return await DsmGraphService(session).load_graph(version_id)


@router.get("/nodes")
async def nodes(
    version_id: str = "active",
    type: str | None = Query(default=None),  # noqa: A002 - API parameter name is part of contract
    q: str | None = None,
    limit: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    graph = await DsmGraphService(session).load_graph(version_id)
    needle = (q or "").casefold()
    result = graph.nodes
    if type:
        result = [node for node in result if node.type == type]
    if needle:
        result = [node for node in result if needle in node.label.casefold() or needle in str(node.metadata).casefold()]
    return result[:limit]


@router.get("/node/{node_id:path}")
async def node(node_id: str, version_id: str = "active", session: AsyncSession = Depends(get_session)):
    result = await DsmGraphService(session).get_node(version_id, node_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Graph node not found")
    return result


@router.get("/related/{node_id:path}")
async def related(
    node_id: str,
    version_id: str = "active",
    depth: int = Query(1, ge=0, le=5),
    edge_type: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    return await DsmGraphService(session).get_related(version_id, node_id, depth, edge_type, limit)


@router.post("/query")
async def query(request: GraphQueryRequest, session: AsyncSession = Depends(get_session)):
    return await DsmGraphService(session).query_graph(request)
