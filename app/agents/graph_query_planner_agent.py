"""Natural-language planner for read-only DSM graph queries."""
from __future__ import annotations

from app.agents.graph_schemas import GraphQueryPlan

BASE_GRAPH_AGENT_PROMPT = """
Você é um agente de consulta sobre um grafo DSM operacional.
A fonte normativa são exclusivamente os nodes, edges e chunks fornecidos pelas tools.
Não invente critérios, relações, especificadores, gravidade ou capítulos.
Se a informação não estiver presente no grafo ou nos chunks retornados, declare limitação.
Responda com saída estruturada no schema solicitado.
""".strip()


def plan_graph_query(query: str, version_id: str = "active") -> GraphQueryPlan:
    """Build a conservative deterministic query plan without clinical answering."""
    q = query.casefold()
    node_filters: dict[str, str | None] = {}
    edge_filters: dict[str, str | None] = {}
    operations = ["inspect_query_terms"]
    requires_vector_search = False
    depth = 1

    if "gravidade" in q or "severity" in q or "severidade" in q:
        node_filters["node_type"] = "SeverityType"
        edge_filters["edge_type"] = "HAS_SEVERITY_TYPE"
        operations.append("filter_disorders_by_severity_type")
        if "domínio" in q or "dominio" in q:
            node_filters["severity_type"] = "ordinal_por_dominio|necessidade_suporte_por_dominio"
        elif "funcionamento adaptativo" in q or "adaptativo" in q:
            node_filters["severity_type"] = "funcionamento_adaptativo"
        elif "frequ" in q:
            node_filters["severity_type"] = "frequencia"
    if "estrutura" in q or "temporal" in q or "topogr" in q:
        node_filters["node_type"] = "StructureType"
        edge_filters["edge_type"] = "HAS_STRUCTURE_TYPE"
        operations.append("filter_disorders_by_structure_type")
        if "temporal" in q or "topogr" in q:
            node_filters["structure_type"] = "temporal_topografico"
    if "capítulo" in q or "capitulo" in q or "chapter" in q or "neurodesenvolvimento" in q:
        operations.append("filter_disorders_by_chapter")
        edge_filters.setdefault("edge_type", "BELONGS_TO_CHAPTER")
        if "neurodesenvolvimento" in q or "01" in q:
            node_filters["chapter_id"] = "01"
    if "chunk" in q or "texto" in q or "busca" in q or "catatonia" in q or "substância" in q or "substancia" in q:
        operations.append("search_chunks_when_graph_evidence_is_insufficient")
        node_filters.setdefault("node_type", "Chunk")
        requires_vector_search = True
    if "relacion" in q or "compartilham" in q or "diferenciais" in q or "especificadores" in q:
        operations.append("traverse_related_edges")
        depth = 2

    if not edge_filters and not node_filters:
        operations.append("find_nodes_by_label_or_metadata")
        node_filters["query"] = query

    return GraphQueryPlan(
        query=query,
        version_id=version_id,
        intended_operations=list(dict.fromkeys(operations)),
        node_filters=node_filters,
        edge_filters=edge_filters,
        traversal_depth=depth,
        requires_vector_search=requires_vector_search,
        requires_graph_traversal=True,
    )
