from app.graph.graphify_adapter import GraphifyAdapter
from app.graph.schemas import GraphEdge, GraphExport, GraphNode
from app.graph.traversal import related_subgraph
from app.scripts.validate_dsm_graph import validate_graph


def sample_graph():
    return GraphExport(
        version_id="v1",
        generated_at="now",
        nodes=[
            GraphNode(id="version:v1", type="Version", label="v1"),
            GraphNode(id="chapter:01", type="Chapter", label="Capítulo 01"),
            GraphNode(id="disorder:tea", type="Disorder", label="TEA"),
            GraphNode(id="structure:s", type="StructureType", label="s"),
            GraphNode(id="ui_mode:u", type="UiMode", label="u"),
            GraphNode(id="severity:x", type="SeverityType", label="x"),
            GraphNode(id="chunk:1", type="Chunk", label="chunk"),
        ],
        edges=[
            GraphEdge(id="e1", source="version:v1", target="chapter:01", type="HAS_CHAPTER"),
            GraphEdge(id="e2", source="disorder:tea", target="chapter:01", type="BELONGS_TO_CHAPTER"),
            GraphEdge(id="e3", source="disorder:tea", target="structure:s", type="HAS_STRUCTURE_TYPE"),
            GraphEdge(id="e4", source="disorder:tea", target="ui_mode:u", type="HAS_UI_MODE"),
            GraphEdge(id="e5", source="disorder:tea", target="severity:x", type="HAS_SEVERITY_TYPE"),
            GraphEdge(id="e6", source="disorder:tea", target="chunk:1", type="HAS_CHUNK"),
        ],
        counts={"nodes": 7, "edges": 6},
    )


def test_graph_export_nao_contem_edges_orfas():
    assert validate_graph(sample_graph()) == []


def test_get_related_retorna_subgrafo():
    graph = related_subgraph(sample_graph(), "disorder:tea", depth=1, limit=10)
    assert graph.nodes
    assert graph.edges
    assert any(node.id == "severity:x" for node in graph.nodes)


async def test_graphify_adapter_disabled_nao_quebra(tmp_path):
    adapter = GraphifyAdapter(enabled=False, cli_path=None)
    assert await adapter.is_available() is False
    result = await adapter.ingest_graph(tmp_path / "graph.json", "v1")
    assert result["enabled"] is False
