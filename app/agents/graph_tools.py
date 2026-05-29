"""Controlled, read-only tools used by DSM graph agents."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.agents.deps import GraphAgentDeps
from app.graph.schemas import GraphQueryRequest
from app.schemas.search import DsmSearchRequest

MAX_TEXT_CHARS = 600


def _limit(value: int | None, default: int = 20, maximum: int = 100) -> int:
    return max(1, min(value or default, maximum))


def _node_to_dict(node: Any) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "label": node.label,
        "metadata": dict(node.metadata or {}),
    }


def _edge_to_dict(edge: Any) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "type": edge.type,
        "label": edge.label,
        "metadata": dict(edge.metadata or {}),
    }


def _graph_to_dict(graph: Any, limit: int | None = None) -> dict[str, Any]:
    capped = _limit(limit, default=50, maximum=200)
    return {
        "version_id": graph.version_id,
        "nodes": [_node_to_dict(node) for node in graph.nodes[:capped]],
        "edges": [_edge_to_dict(edge) for edge in graph.edges[:capped]],
        "counts": dict(graph.counts or {}),
        "warnings": list(graph.warnings or []),
    }


def _matches(value: Any, expected: str) -> bool:
    return str(value or "").casefold() == expected.casefold()


def _contains(node: Any, query: str | None) -> bool:
    if not query:
        return True
    needle = query.casefold()
    return needle in node.label.casefold() or needle in str(node.metadata or {}).casefold() or needle in node.id.casefold()


def _edges_for_nodes(edges: Iterable[Any], node_ids: set[str], edge_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    out = []
    for edge in edges:
        if edge_type and edge.type != edge_type:
            continue
        if edge.source in node_ids or edge.target in node_ids:
            out.append(_edge_to_dict(edge))
        if len(out) >= limit:
            break
    return out


async def _load_graph(deps: GraphAgentDeps, version_id: str | None = None):
    return await deps.graph_service.load_graph(version_id or deps.version_id)


async def get_graph_status(deps: GraphAgentDeps, version_id: str | None = None) -> dict[str, Any]:
    status = await deps.graph_service.get_status()
    status["requested_version_id"] = version_id or deps.version_id
    return status


async def load_graph_summary(deps: GraphAgentDeps, version_id: str | None = None) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    return {
        "version_id": graph.version_id,
        "counts": dict(graph.counts or {}),
        "warnings": list(graph.warnings or []),
    }


async def find_nodes(
    deps: GraphAgentDeps,
    version_id: str | None = None,
    node_type: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    capped = _limit(limit)
    nodes = [node for node in graph.nodes if (node_type is None or node.type == node_type) and _contains(node, query)]
    selected = nodes[:capped]
    node_ids = {node.id for node in selected}
    return {"version_id": graph.version_id, "nodes": [_node_to_dict(node) for node in selected], "edges": _edges_for_nodes(graph.edges, node_ids, limit=capped)}


async def get_node(deps: GraphAgentDeps, node_id: str, version_id: str | None = None) -> dict[str, Any]:
    result = await deps.graph_service.get_node(version_id or deps.version_id, node_id)
    if result is None:
        return {"version_id": version_id or deps.version_id, "node": None, "edges": []}
    return {
        "version_id": version_id or deps.version_id,
        "node": _node_to_dict(result["node"]),
        "edges": [_edge_to_dict(edge) for edge in result["edges"]],
    }


async def get_related_nodes(
    deps: GraphAgentDeps,
    node_id: str,
    version_id: str | None = None,
    depth: int = 1,
    edge_type: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    graph = await deps.graph_service.get_related(version_id or deps.version_id, node_id, max(0, min(depth, 3)), edge_type, _limit(limit, maximum=100))
    return _graph_to_dict(graph, limit)


async def traverse_graph(
    deps: GraphAgentDeps,
    version_id: str | None = None,
    node_id: str | None = None,
    edge_type: str | None = None,
    node_type: str | None = None,
    query: str | None = None,
    depth: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    request = GraphQueryRequest(version_id=version_id or deps.version_id, node_id=node_id, edge_type=edge_type, node_type=node_type, query=query, depth=max(0, min(depth, 3)), limit=_limit(limit, maximum=100))
    graph = await deps.graph_service.query_graph(request)
    return _graph_to_dict(graph, limit)


async def _find_disorders_by_taxonomy(deps: GraphAgentDeps, edge_type: str, taxonomy_type: str, value: str, version_id: str | None, limit: int) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    capped = _limit(limit)
    taxonomy_nodes = [node for node in graph.nodes if node.type == taxonomy_type and _contains(node, value)]
    taxonomy_ids = {node.id for node in taxonomy_nodes}
    edges = [edge for edge in graph.edges if edge.type == edge_type and edge.target in taxonomy_ids]
    disorder_ids = [edge.source for edge in edges]
    node_map = {node.id: node for node in graph.nodes}
    disorders = [node_map[node_id] for node_id in disorder_ids if node_id in node_map][:capped]
    selected_ids = {node.id for node in disorders} | taxonomy_ids
    selected_edges = [edge for edge in edges if edge.source in selected_ids][:capped]
    return {"version_id": graph.version_id, "nodes": [_node_to_dict(node) for node in [*taxonomy_nodes, *disorders]][: capped * 2], "edges": [_edge_to_dict(edge) for edge in selected_edges]}


async def find_disorders_by_severity_type(deps: GraphAgentDeps, severity_type: str, version_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    return await _find_disorders_by_taxonomy(deps, "HAS_SEVERITY_TYPE", "SeverityType", severity_type, version_id, limit)


async def find_disorders_by_structure_type(deps: GraphAgentDeps, structure_type: str, version_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    return await _find_disorders_by_taxonomy(deps, "HAS_STRUCTURE_TYPE", "StructureType", structure_type, version_id, limit)


async def find_disorders_by_chapter(deps: GraphAgentDeps, chapter_id: str, version_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    capped = _limit(limit)
    chapter_query = chapter_id.removeprefix("chapter:")
    chapters = [node for node in graph.nodes if node.type == "Chapter" and (_matches(node.metadata.get("chapter_id"), chapter_query) or _contains(node, chapter_query))]
    chapter_ids = {node.id for node in chapters}
    edges = [edge for edge in graph.edges if edge.type == "BELONGS_TO_CHAPTER" and edge.target in chapter_ids]
    disorder_ids = [edge.source for edge in edges]
    node_map = {node.id: node for node in graph.nodes}
    disorders = [node_map[node_id] for node_id in disorder_ids if node_id in node_map][:capped]
    return {"version_id": graph.version_id, "nodes": [_node_to_dict(node) for node in [*chapters, *disorders]], "edges": [_edge_to_dict(edge) for edge in edges[:capped]]}


async def find_chunks_for_disorder(deps: GraphAgentDeps, disorder_query: str, version_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    capped = _limit(limit)
    disorders = [node for node in graph.nodes if node.type == "Disorder" and _contains(node, disorder_query)]
    disorder_ids = {node.id for node in disorders}
    edges = [edge for edge in graph.edges if edge.type == "HAS_CHUNK" and edge.source in disorder_ids]
    chunk_ids = {edge.target for edge in edges}
    chunks = [node for node in graph.nodes if node.id in chunk_ids][:capped]
    return {"version_id": graph.version_id, "nodes": [_node_to_dict(node) for node in [*disorders, *chunks]][: capped * 2], "edges": [_edge_to_dict(edge) for edge in edges[:capped]]}


async def find_registry_cross_references(deps: GraphAgentDeps, query: str | None = None, version_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    graph = await _load_graph(deps, version_id)
    capped = _limit(limit)
    registries = [node for node in graph.nodes if node.type == "RegistryItem" and _contains(node, query)]
    registry_ids = {node.id for node in registries}
    edges = [edge for edge in graph.edges if edge.type == "CROSS_REFERENCES" and edge.source in registry_ids][:capped]
    chapter_ids = {edge.target for edge in edges}
    chapters = [node for node in graph.nodes if node.id in chapter_ids]
    return {"version_id": graph.version_id, "nodes": [_node_to_dict(node) for node in [*registries[:capped], *chapters]], "edges": [_edge_to_dict(edge) for edge in edges]}


async def hybrid_search_chunks(deps: GraphAgentDeps, query: str, version_id: str | None = None, limit: int = 8) -> dict[str, Any]:
    if deps.search_service is None:
        return {"version_id": version_id or deps.version_id, "chunks": [], "limitations": ["HybridSearchService is not configured."]}
    result = await deps.search_service.search(DsmSearchRequest(query=query, version_id=version_id or deps.version_id, top_k=_limit(limit, default=8, maximum=20), use_vector=False, use_fts=True, allow_fallback=True))
    chunks = []
    for item in result.results:
        text = item.chunk_text or ""
        chunks.append({
            "id": str(item.chunk_id),
            "document_item_id": item.document_item_id,
            "chapter_id": item.chapter_id,
            "chunk_type": item.chunk_type,
            "title": item.chunk_title,
            "text": text[:MAX_TEXT_CHARS] + ("…" if len(text) > MAX_TEXT_CHARS else ""),
            "score": item.hybrid_score,
            "metadata": dict(item.metadata or {}),
        })
    return {"version_id": result.version_id, "chunks": chunks}
