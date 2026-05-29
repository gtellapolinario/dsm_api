"""Validate a local DSM graph export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.graph.schemas import GraphExport


def validate_graph(graph: GraphExport) -> list[str]:
    errors: list[str] = []
    node_ids = [node.id for node in graph.nodes]
    node_id_set = set(node_ids)
    if len(node_ids) != len(node_id_set):
        errors.append("duplicate node IDs found")
    edge_ids = [edge.id for edge in graph.edges]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("duplicate edge IDs found")
    if not any(node.type == "Version" for node in graph.nodes):
        errors.append("missing Version node")
    for edge in graph.edges:
        if edge.source not in node_id_set or edge.target not in node_id_set:
            errors.append(f"orphan edge {edge.id}: {edge.source} -> {edge.target}")
    outgoing = {(edge.source, edge.type) for edge in graph.edges}
    incoming_by_target_type = {(edge.target, edge.type) for edge in graph.edges}
    disorders = [node for node in graph.nodes if node.type == "Disorder"]
    for disorder in disorders:
        for edge_type in ("BELONGS_TO_CHAPTER", "HAS_STRUCTURE_TYPE", "HAS_UI_MODE", "HAS_SEVERITY_TYPE"):
            if (disorder.id, edge_type) not in outgoing:
                errors.append(f"{disorder.id} missing {edge_type}")
    for chunk in [node for node in graph.nodes if node.type == "Chunk"]:
        if (chunk.id, "HAS_CHUNK") not in incoming_by_target_type:
            errors.append(f"{chunk.id} is not targeted by HAS_CHUNK")
    return list(dict.fromkeys(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate DSM graph export")
    parser.add_argument("graph_path", nargs="?", default="graph_exports/active/graph.json")
    args = parser.parse_args()
    raw = Path(args.graph_path).read_text(encoding="utf-8")
    json.loads(raw)
    graph = GraphExport.model_validate_json(raw)
    errors = validate_graph(graph)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"valid": True, "version_id": graph.version_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
