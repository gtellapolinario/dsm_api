"""Service layer for derived DSM knowledge graph operations."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.graph.builder import DsmGraphBuilder
from app.graph.graphify_adapter import GraphifyAdapter
from app.graph.schemas import GraphExport, GraphQueryRequest
from app.graph.store import LocalGraphStore
from app.graph.traversal import direct_edges, related_subgraph


class DsmGraphService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.store = LocalGraphStore(self.settings.graph_export_dir)
        self.adapter = GraphifyAdapter(self.settings.graphify_enabled, self.settings.graphify_cli_path)

    async def build_graph(self, version_id: str = "active") -> GraphExport:
        return await DsmGraphBuilder(self.session).build_graph(version_id)

    async def export_graph(self, version_id: str = "active", persist: bool = True, send_to_graphify: bool = False) -> tuple[GraphExport, Path | None, dict]:
        graph = await self.build_graph(version_id)
        graph_path = await self.store.save(graph) if persist else None
        graphify_result = {"enabled": self.settings.graphify_enabled, "available": False}
        if send_to_graphify:
            if graph_path is None:
                graph_path = await self.store.save(graph)
            graphify_result = await self.adapter.ingest_graph(graph_path, graph.version_id)
            message = graphify_result.get("message")
            if message and not graphify_result.get("available"):
                graph.warnings.append(message)
                if persist and graph_path is not None:
                    graph_path = await self.store.save(graph)
        return graph, graph_path, graphify_result

    async def load_graph(self, version_id: str = "active", auto_build: bool = True) -> GraphExport:
        graph = await self.store.load(version_id)
        if graph is not None:
            return graph
        if not auto_build:
            raise FileNotFoundError(f"No graph export found for {version_id}")
        graph, _, _ = await self.export_graph(version_id=version_id, persist=True, send_to_graphify=False)
        return graph

    async def get_node(self, version_id: str, node_id: str) -> dict | None:
        graph = await self.load_graph(version_id)
        node = next((node for node in graph.nodes if node.id == node_id), None)
        if node is None:
            return None
        return {"node": node, "edges": direct_edges(graph, node_id)}

    async def get_related(self, version_id: str, node_id: str, depth: int = 1, edge_type: str | None = None, limit: int = 100) -> GraphExport:
        graph = await self.load_graph(version_id)
        return related_subgraph(graph, node_id=node_id, depth=depth, edge_type=edge_type, limit=limit)

    async def query_graph(self, request: GraphQueryRequest) -> GraphExport:
        graph = await self.load_graph(request.version_id)
        if request.node_id:
            return related_subgraph(graph, request.node_id, request.depth, request.edge_type, request.limit)
        query = (request.query or "").casefold()
        nodes = graph.nodes
        if request.node_type:
            nodes = [node for node in nodes if node.type == request.node_type]
        if query:
            nodes = [node for node in nodes if query in node.label.casefold() or query in str(node.metadata).casefold()]
        nodes = nodes[: max(1, min(request.limit, 1000))]
        selected_ids = {node.id for node in nodes}
        edges = [edge for edge in graph.edges if edge.source in selected_ids or edge.target in selected_ids]
        if request.edge_type:
            edges = [edge for edge in edges if edge.type == request.edge_type]
        edges = edges[: max(1, min(request.limit, 1000))]
        connected_ids = selected_ids | {edge.source for edge in edges} | {edge.target for edge in edges}
        node_map = {node.id: node for node in graph.nodes}
        out_nodes = [node_map[node_id] for node_id in connected_ids if node_id in node_map]
        return GraphExport(version_id=graph.version_id, generated_at=graph.generated_at, nodes=out_nodes, edges=edges, counts={"nodes": len(out_nodes), "edges": len(edges)}, warnings=[])

    async def get_status(self) -> dict:
        return {
            "graph_enabled": self.settings.graph_enabled,
            "graphify_enabled": self.settings.graphify_enabled,
            "graphify_available": await self.adapter.is_available(),
            "export_dir": self.settings.graph_export_dir,
            "available_exports": await self.store.list_exports(),
        }
