from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agents.deps import GraphAgentDeps
from app.agents.graph_audit_agent import audit_graph
from app.agents.graph_clinical_relation_agent import answer_clinical_relations
from app.agents.graph_query_planner_agent import plan_graph_query
from app.agents.graph_traversal_agent import answer_graph_traversal
from app.graph.schemas import GraphEdge, GraphExport, GraphNode
from app.main import app


def sample_graph():
    return GraphExport(
        version_id="v1",
        generated_at="now",
        nodes=[
            GraphNode(id="version:v1", type="Version", label="v1"),
            GraphNode(id="chapter:01", type="Chapter", label="Neurodesenvolvimento", metadata={"chapter_id": "01"}),
            GraphNode(id="disorder:tea", type="Disorder", label="Transtorno do Espectro Autista", metadata={"chapter_id": "01"}),
            GraphNode(id="severity:funcionamento_adaptativo", type="SeverityType", label="funcionamento_adaptativo"),
            GraphNode(id="structure:temporal_topografico", type="StructureType", label="temporal_topografico"),
            GraphNode(id="ui_mode:structured_full", type="UiMode", label="structured_full"),
            GraphNode(id="chunk:c1", type="Chunk", label="Gravidade", metadata={"document_item_id": "tea", "chapter_id": "01", "chunk_type": "severity"}),
        ],
        edges=[
            GraphEdge(id="e0", source="version:v1", target="chapter:01", type="HAS_CHAPTER"),
            GraphEdge(id="e1", source="disorder:tea", target="chapter:01", type="BELONGS_TO_CHAPTER"),
            GraphEdge(id="e2", source="disorder:tea", target="severity:funcionamento_adaptativo", type="HAS_SEVERITY_TYPE"),
            GraphEdge(id="e3", source="disorder:tea", target="structure:temporal_topografico", type="HAS_STRUCTURE_TYPE"),
            GraphEdge(id="e4", source="disorder:tea", target="ui_mode:structured_full", type="HAS_UI_MODE"),
            GraphEdge(id="e5", source="disorder:tea", target="chunk:c1", type="HAS_CHUNK"),
        ],
        counts={"nodes": 7, "edges": 6},
    )


class FakeGraphService:
    async def load_graph(self, version_id="active", auto_build=True):
        return sample_graph()

    async def get_status(self):
        return {"graph_enabled": True, "graphify_enabled": False, "export_dir": "graph_exports", "available_exports": ["v1"]}

    async def get_node(self, version_id, node_id):
        graph = sample_graph()
        node = next((node for node in graph.nodes if node.id == node_id), None)
        if node is None:
            return None
        return {"node": node, "edges": [edge for edge in graph.edges if edge.source == node_id or edge.target == node_id]}

    async def get_related(self, version_id, node_id, depth=1, edge_type=None, limit=20):
        return sample_graph()

    async def query_graph(self, request):
        return sample_graph()


class EmptyGraphService(FakeGraphService):
    async def load_graph(self, version_id="active", auto_build=True):
        return GraphExport(version_id="v1", generated_at="now", nodes=[], edges=[], counts={"nodes": 0, "edges": 0})

    async def query_graph(self, request):
        return await self.load_graph(request.version_id)


class EmptySearchService:
    async def search(self, request):
        return SimpleNamespace(version_id="v1", results=[])


def deps(service=None, search_service=None):
    return GraphAgentDeps(session=None, version_id="active", graph_service=service or FakeGraphService(), search_service=search_service)


def test_agents_disabled_retorna_erro_controlado():
    response = TestClient(app).post("/api/dsm/graph/agents/ask", json={"query": "teste"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Agents are disabled."}


async def test_graph_traversal_agent_responde_com_used_nodes_para_severity_type_conhecido():
    result = await answer_graph_traversal(deps(), "quais transtornos têm gravidade por funcionamento adaptativo?", limit=20)
    assert result.used_nodes
    assert any(node.id == "disorder:tea" for node in result.used_nodes)
    assert any(edge.type == "HAS_SEVERITY_TYPE" for edge in result.used_edges)


async def test_graph_audit_agent_retorna_pass_em_grafo_valido():
    result = await audit_graph(deps())
    assert result.status in {"PASS", "PASS_WITH_WARNINGS"}
    assert result.checked_rules


def test_query_planner_agent_gera_plano_com_edge_type_ou_node_type():
    result = plan_graph_query("quais transtornos compartilham estrutura temporal-topográfica?", "active")
    assert result.edge_filters.get("edge_type") or result.node_filters.get("node_type")


async def test_clinical_relation_agent_nao_inventa_quando_tools_retornam_vazio():
    result = await answer_clinical_relations(deps(EmptyGraphService(), EmptySearchService()), "catatonia", limit=20, allow_hybrid_search=True)
    assert result.confidence == "low"
    assert result.used_nodes == []
    assert result.used_edges == []
    assert result.limitations


def test_graph_agent_endpoints_exist_openapi():
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/dsm/graph/agents/ask" in paths
    assert "/api/dsm/graph/agents/clinical-relations" in paths
    assert "/api/dsm/graph/agents/audit" in paths
    assert "/api/dsm/graph/agents/plan-query" in paths
