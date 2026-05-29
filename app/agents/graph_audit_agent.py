"""Deterministic audit agent for DSM graph exports."""
from __future__ import annotations

from app.agents.deps import GraphAgentDeps
from app.agents.graph_schemas import GraphAuditFinding, GraphAuditResult

CHECKED_RULES = [
    "Todo Disorder pertence a Chapter.",
    "Todo Disorder tem StructureType.",
    "Todo Disorder tem SeverityType.",
    "Todo Disorder tem UiMode.",
    "Todo Chunk aponta para Disorder existente.",
    "Todo RegistryItem pertence a Chapter quando chapter_id existir.",
    "CROSS_REFERENCES aponta para Chapter existente.",
    "Não há edges órfãs.",
    "Não há nodes duplicados.",
    "Graphify desabilitado não impede LocalGraphStore.",
]


def _edge_index(edges) -> dict[tuple[str, str], list]:
    index: dict[tuple[str, str], list] = {}
    for edge in edges:
        index.setdefault((edge.source, edge.type), []).append(edge)
    return index


async def audit_graph(deps: GraphAgentDeps) -> GraphAuditResult:
    findings: list[GraphAuditFinding] = []
    try:
        graph = await deps.graph_service.load_graph(deps.version_id)
        status = await deps.graph_service.get_status()
    except Exception as exc:  # noqa: BLE001 - controlled endpoint should return a structured blocked result
        return GraphAuditResult(version_id=deps.version_id, status="BLOCKED", checked_rules=CHECKED_RULES, findings=[GraphAuditFinding(severity="critical", problem="Graph export could not be loaded.", evidence=str(exc), recommendation="Export or rebuild the local graph outside the agent before auditing.")])

    node_ids = [node.id for node in graph.nodes]
    node_id_set = set(node_ids)
    duplicate_ids = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
    if duplicate_ids:
        findings.append(GraphAuditFinding(severity="high", problem="Duplicate node ids detected.", evidence=", ".join(duplicate_ids[:20]), recommendation="Ensure graph builder emits stable unique node ids."))

    edges_by_source_type = _edge_index(graph.edges)
    for node in graph.nodes:
        if node.type == "Disorder":
            required = [("BELONGS_TO_CHAPTER", "Disorder is not linked to a Chapter."), ("HAS_STRUCTURE_TYPE", "Disorder is missing StructureType."), ("HAS_SEVERITY_TYPE", "Disorder is missing SeverityType."), ("HAS_UI_MODE", "Disorder is missing UiMode.")]
            for edge_type, problem in required:
                if not edges_by_source_type.get((node.id, edge_type)):
                    findings.append(GraphAuditFinding(severity="medium", node_id=node.id, problem=problem, evidence=node.label, recommendation=f"Regenerate graph and verify source field for {edge_type}."))
        if node.type == "RegistryItem" and node.metadata.get("chapter_id") and not edges_by_source_type.get((node.id, "REGISTRY_BELONGS_TO_CHAPTER")):
            findings.append(GraphAuditFinding(severity="medium", node_id=node.id, problem="RegistryItem has chapter_id but no REGISTRY_BELONGS_TO_CHAPTER edge.", evidence=str(node.metadata.get("chapter_id")), recommendation="Verify registry chapter fields during graph build."))

    for edge in graph.edges:
        if edge.source not in node_id_set or edge.target not in node_id_set:
            findings.append(GraphAuditFinding(severity="high", edge_id=edge.id, problem="Orphan edge detected.", evidence=f"{edge.source} -> {edge.target}", recommendation="Remove orphan edge or create missing endpoint node."))
        if edge.type == "HAS_CHUNK":
            source = next((node for node in graph.nodes if node.id == edge.source), None)
            target = next((node for node in graph.nodes if node.id == edge.target), None)
            if source is None or source.type != "Disorder" or target is None or target.type != "Chunk":
                findings.append(GraphAuditFinding(severity="high", edge_id=edge.id, problem="Chunk edge does not connect Disorder to Chunk.", evidence=f"{edge.source} -> {edge.target}", recommendation="Verify chunk document_item_id maps to an existing Disorder."))
        if edge.type == "CROSS_REFERENCES" and edge.target not in node_id_set:
            findings.append(GraphAuditFinding(severity="medium", edge_id=edge.id, problem="CROSS_REFERENCES points to missing Chapter.", evidence=edge.target, recommendation="Create the target Chapter node or correct registry canonical chapter."))

    if status.get("graphify_enabled") is False and "export_dir" not in status:
        findings.append(GraphAuditFinding(severity="low", problem="Graphify disabled status lacks LocalGraphStore export_dir.", recommendation="Expose LocalGraphStore export_dir in graph status."))

    status_value = "PASS" if not findings else "PASS_WITH_WARNINGS"
    return GraphAuditResult(version_id=graph.version_id, status=status_value, findings=findings, checked_rules=CHECKED_RULES)
