"""GraphTraversalAgent for structural DSM graph questions."""
from __future__ import annotations

from app.agents import graph_tools
from app.agents.deps import GraphAgentDeps
from app.agents.graph_query_planner_agent import plan_graph_query
from app.agents.graph_schemas import GraphAgentAnswer, UsedGraphEdge, UsedGraphNode


def _used_nodes(payload: dict) -> list[UsedGraphNode]:
    return [UsedGraphNode(**node) for node in payload.get("nodes", [])]


def _used_edges(payload: dict) -> list[UsedGraphEdge]:
    return [UsedGraphEdge(**edge) for edge in payload.get("edges", [])]


def _disorder_labels(nodes: list[UsedGraphNode]) -> list[str]:
    return [node.label for node in nodes if node.type == "Disorder"]


def _value_from_plan(filters: dict[str, str | None], *keys: str) -> str | None:
    for key in keys:
        value = filters.get(key)
        if value:
            return value.split("|", 1)[0]
    return None


async def answer_graph_traversal(deps: GraphAgentDeps, query: str, limit: int = 20) -> GraphAgentAnswer:
    plan = plan_graph_query(query, deps.version_id)
    q = query.casefold()
    payload: dict

    if plan.edge_filters.get("edge_type") == "HAS_SEVERITY_TYPE":
        value = _value_from_plan(plan.node_filters, "severity_type") or query
        payload = await graph_tools.find_disorders_by_severity_type(deps, value, limit=limit)
    elif plan.edge_filters.get("edge_type") == "HAS_STRUCTURE_TYPE":
        value = _value_from_plan(plan.node_filters, "structure_type") or query
        payload = await graph_tools.find_disorders_by_structure_type(deps, value, limit=limit)
    elif "chunk" in q:
        payload = await graph_tools.find_chunks_for_disorder(deps, query, limit=limit)
    elif "chapter_id" in plan.node_filters:
        payload = await graph_tools.find_disorders_by_chapter(deps, plan.node_filters["chapter_id"] or query, limit=limit)
    else:
        payload = await graph_tools.find_nodes(deps, node_type=plan.node_filters.get("node_type"), query=plan.node_filters.get("query") or query, limit=limit)

    nodes = _used_nodes(payload)
    edges = _used_edges(payload)
    disorders = _disorder_labels(nodes)
    limitations = []
    if not nodes or (plan.edge_filters and not edges):
        limitations.append("Não encontrei evidência suficiente no grafo para responder sem inferência.")
        answer = "Não há evidência suficiente nos nodes/edges retornados para responder à pergunta."
        confidence = "low"
    elif disorders:
        answer = f"Encontrei {len(disorders)} transtorno(s) com evidência no grafo: " + ", ".join(disorders[:limit]) + "."
        confidence = "high" if edges else "medium"
    else:
        answer = f"Encontrei {len(nodes)} node(s) relevantes no grafo: " + ", ".join(node.label for node in nodes[:limit]) + "."
        confidence = "medium"

    return GraphAgentAnswer(answer=answer, version_id=payload.get("version_id", deps.version_id), confidence=confidence, used_nodes=nodes, used_edges=edges, limitations=limitations, suggested_followups=["Refinar por capítulo, tipo de node ou tipo de edge."])
