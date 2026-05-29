"""Traversal helpers for in-memory DSM graph exports."""
from __future__ import annotations

from app.graph.schemas import GraphEdge, GraphExport


def direct_edges(graph: GraphExport, node_id: str, edge_type: str | None = None) -> list[GraphEdge]:
    return [
        edge for edge in graph.edges
        if (edge.source == node_id or edge.target == node_id) and (edge_type is None or edge.type == edge_type)
    ]


def related_subgraph(graph: GraphExport, node_id: str, depth: int = 1, edge_type: str | None = None, limit: int = 100) -> GraphExport:
    node_map = {node.id: node for node in graph.nodes}
    if node_id not in node_map:
        return GraphExport(version_id=graph.version_id, generated_at=graph.generated_at, nodes=[], edges=[], counts={"nodes": 0, "edges": 0}, warnings=[f"Node not found: {node_id}"])
    depth = max(0, min(depth, 5))
    visited = {node_id}
    frontier = {node_id}
    selected_edges: list[GraphEdge] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in graph.edges:
            if edge_type and edge.type != edge_type:
                continue
            if edge.source in frontier or edge.target in frontier:
                if len(selected_edges) >= limit:
                    break
                selected_edges.append(edge)
                other = edge.target if edge.source in frontier else edge.source
                if other not in visited:
                    visited.add(other)
                    next_frontier.add(other)
        frontier = next_frontier
        if not frontier or len(selected_edges) >= limit:
            break
    nodes = [node_map[node_id] for node_id in visited if node_id in node_map]
    edge_ids = set()
    edges = []
    selected_node_ids = {node.id for node in nodes}
    for edge in selected_edges:
        if edge.id not in edge_ids and edge.source in selected_node_ids and edge.target in selected_node_ids:
            edges.append(edge)
            edge_ids.add(edge.id)
    return GraphExport(version_id=graph.version_id, generated_at=graph.generated_at, nodes=nodes, edges=edges, counts={"nodes": len(nodes), "edges": len(edges)}, warnings=[])
