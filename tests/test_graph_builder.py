from types import SimpleNamespace
from uuid import uuid4

from app.graph.builder import DsmGraphBuilder


class ScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    async def scalar(self, stmt):
        return SimpleNamespace(id="v1", status="active")

    async def scalars(self, stmt):
        sql = str(stmt)
        if "diagnostic_documents" in sql:
            return ScalarResult([
                SimpleNamespace(
                    version_id="v1", item_id="tea", chapter_id="01", chapter_name="Neurodesenvolvimento",
                    name="Transtorno do Espectro Autista", category="FULL", estrutura_diagnostica="criterios_multiaxiais",
                    ui_mode="structured_full", render_structured_interview=True, severity_type="necessidade_suporte_por_dominio",
                    active=True, document={"criteria": ["Déficits persistentes"], "critical_differentials": ["substância"]},
                ),
                SimpleNamespace(
                    version_id="v1", item_id="tdah", chapter_id="01", chapter_name="Neurodesenvolvimento",
                    name="TDAH", category="FULL", estrutura_diagnostica="criterios_multiaxiais",
                    ui_mode="structured_full", render_structured_interview=True, severity_type="contagem_sintomas_e_prejuizo",
                    active=True, document={"criterios": ["Sintomas de desatenção"]},
                ),
            ])
        if "diagnostic_registry" in sql:
            return ScalarResult([
                SimpleNamespace(
                    version_id="v1", item_id="x", name="Excluído", chapter_id="02", chapter_name="Psicóticos", category="EXCLUDE",
                    registry_type="excluded", canonical_chapter_id="01", canonical_chapter_name="Neurodesenvolvimento", reason="referência cruzada", active=True,
                )
            ])
        if "diagnostic_chunks" in sql:
            return ScalarResult([
                SimpleNamespace(id=uuid4(), version_id="v1", document_item_id="tea", chapter_id="01", chunk_type="criteria", chunk_title="Critérios", chunk_text="texto")
            ])
        return ScalarResult([])


async def test_build_graph_retorna_nodes_edges():
    graph = await DsmGraphBuilder(FakeSession()).build_graph("active")
    assert graph.version_id == "v1"
    assert graph.nodes
    assert graph.edges
    assert any(node.type == "Disorder" and node.id == "disorder:tea" for node in graph.nodes)
    assert any(edge.type == "HAS_CHUNK" for edge in graph.edges)


async def test_disorders_tem_edges_obrigatorias():
    graph = await DsmGraphBuilder(FakeSession()).build_graph("active")
    disorders = [node for node in graph.nodes if node.type == "Disorder"]
    outgoing = {(edge.source, edge.type) for edge in graph.edges}
    for disorder in disorders:
        assert (disorder.id, "BELONGS_TO_CHAPTER") in outgoing
        assert (disorder.id, "HAS_STRUCTURE_TYPE") in outgoing
        assert (disorder.id, "HAS_SEVERITY_TYPE") in outgoing
