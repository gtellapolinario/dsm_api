from app.graph.schemas import GraphEdge, GraphExport, GraphNode
from app.services import graph_service


def graph():
    return GraphExport(
        version_id="v1",
        generated_at="now",
        nodes=[
            GraphNode(id="disorder:tea", type="Disorder", label="Autismo"),
            GraphNode(id="severity:suporte", type="SeverityType", label="necessidade_suporte_por_dominio"),
        ],
        edges=[GraphEdge(id="e1", source="disorder:tea", target="severity:suporte", type="HAS_SEVERITY_TYPE")],
        counts={"nodes": 2, "edges": 1},
    )


async def test_query_por_node_type_disorder_funciona(monkeypatch):
    async def load_stub(self, version_id="active", auto_build=True):
        return graph()

    monkeypatch.setattr(graph_service.DsmGraphService, "load_graph", load_stub)
    service = graph_service.DsmGraphService(session=None)  # type: ignore[arg-type]
    from app.graph.schemas import GraphQueryRequest

    result = await service.query_graph(GraphQueryRequest(node_type="Disorder", query="Autismo"))
    assert any(node.type == "Disorder" for node in result.nodes)


async def test_get_related_service_retorna_subgrafo(monkeypatch):
    async def load_stub(self, version_id="active", auto_build=True):
        return graph()

    monkeypatch.setattr(graph_service.DsmGraphService, "load_graph", load_stub)
    service = graph_service.DsmGraphService(session=None)  # type: ignore[arg-type]
    result = await service.get_related("active", "disorder:tea", depth=1, edge_type=None, limit=10)
    assert any(edge.type == "HAS_SEVERITY_TYPE" for edge in result.edges)
