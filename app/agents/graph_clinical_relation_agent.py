"""GraphClinicalRelationAgent for evidence-bound DSM relationship exploration."""
from __future__ import annotations

from app.agents import graph_tools
from app.agents.deps import GraphAgentDeps
from app.agents.graph_schemas import GraphAgentAnswer, UsedChunk, UsedGraphEdge, UsedGraphNode


def _nodes(payload: dict) -> list[UsedGraphNode]:
    return [UsedGraphNode(**node) for node in payload.get("nodes", [])]


def _edges(payload: dict) -> list[UsedGraphEdge]:
    return [UsedGraphEdge(**edge) for edge in payload.get("edges", [])]


def _chunks(payload: dict) -> list[UsedChunk]:
    return [UsedChunk(**chunk) for chunk in payload.get("chunks", [])]


async def answer_clinical_relations(deps: GraphAgentDeps, query: str, limit: int = 20, allow_hybrid_search: bool = True) -> GraphAgentAnswer:
    """Combine graph traversal and optional FTS while refusing unsupported claims."""
    q = query.casefold()
    payloads: list[dict] = []

    if "gravidade" in q or "frequ" in q:
        payloads.append(await graph_tools.find_disorders_by_severity_type(deps, "frequencia" if "frequ" in q else query, limit=limit))
    if "estrutura" in q:
        payloads.append(await graph_tools.find_disorders_by_structure_type(deps, query, limit=limit))
    if "chapter" in q or "capítulo" in q or "capitulo" in q or "neurodesenvolvimento" in q:
        payloads.append(await graph_tools.find_disorders_by_chapter(deps, "01" if "neurodesenvolvimento" in q else query, limit=limit))
    if "refer" in q:
        payloads.append(await graph_tools.find_registry_cross_references(deps, query, limit=limit))
    payloads.append(await graph_tools.find_nodes(deps, query=query, limit=limit))

    used_nodes: list[UsedGraphNode] = []
    used_edges: list[UsedGraphEdge] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()
    version_id = deps.version_id
    for payload in payloads:
        version_id = payload.get("version_id", version_id)
        for node in _nodes(payload):
            if node.id not in seen_nodes:
                used_nodes.append(node)
                seen_nodes.add(node.id)
        for edge in _edges(payload):
            if edge.id not in seen_edges:
                used_edges.append(edge)
                seen_edges.add(edge.id)

    used_chunks: list[UsedChunk] = []
    limitations: list[str] = []
    if (not used_nodes or not used_edges) and allow_hybrid_search:
        search_payload = await graph_tools.hybrid_search_chunks(deps, query, limit=min(limit, 8))
        version_id = search_payload.get("version_id", version_id)
        used_chunks = _chunks(search_payload)
        limitations.extend(search_payload.get("limitations", []))

    if used_edges:
        relation_types = sorted({edge.type for edge in used_edges})
        labels = [node.label for node in used_nodes if node.type in {"Disorder", "Specifier", "Differential", "SeverityType", "StructureType"}]
        answer = "Encontrei relações explícitas no grafo: " + ", ".join(relation_types) + ". Entidades principais: " + ", ".join(labels[:limit]) + "."
        confidence = "high"
    elif used_chunks:
        answer = "Não encontrei relações explícitas suficientes no grafo; encontrei chunks textuais que podem ser revisados como evidência auxiliar: " + ", ".join((chunk.title or chunk.id) for chunk in used_chunks) + "."
        confidence = "medium"
        limitations.append("A resposta usa busca textual auxiliar porque o grafo não continha relação explícita suficiente.")
    else:
        answer = "Não encontrei evidência no grafo nem em chunks retornados para sustentar uma relação clínica."
        confidence = "low"
        limitations.append("Sem evidência retornada pelas tools; nenhuma relação foi inferida.")

    return GraphAgentAnswer(answer=answer, version_id=version_id, confidence=confidence, used_nodes=used_nodes[:limit], used_edges=used_edges[:limit], used_chunks=used_chunks, limitations=list(dict.fromkeys(limitations)), suggested_followups=["Tentar termos mais específicos ou limitar por capítulo."])
