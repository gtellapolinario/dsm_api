from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import dsm_documents


def fake_doc(chapter_id="01"):
    return SimpleNamespace(
        id=uuid4(), version_id="v1", item_id="tdah", chapter_id=chapter_id, chapter_name="Neuro",
        name="TDAH", category="FULL", estrutura_diagnostica="polythetic_clusters_simetricos", ui_mode="structured_full",
        render_structured_interview=True, has_formal_severity=True, severity_type="contagem_sintomas_e_prejuizo", active=True,
        document={"item_id": "tdah"},
    )


def test_lista_documentos(monkeypatch):
    async def list_stub(self, **filters):
        return [fake_doc()]
    monkeypatch.setattr(dsm_documents.DsmDocumentRepository, "list", list_stub)
    response = TestClient(app).get("/api/dsm/documents")
    assert response.status_code == 200
    assert response.json()[0]["item_id"] == "tdah"


def test_filtra_por_capitulo(monkeypatch):
    captured = {}
    async def list_stub(self, **filters):
        captured.update(filters)
        return [fake_doc(filters["chapter_id"])]
    monkeypatch.setattr(dsm_documents.DsmDocumentRepository, "list", list_stub)
    response = TestClient(app).get("/api/dsm/documents?chapter_id=01")
    assert response.status_code == 200
    assert captured["chapter_id"] == "01"


def test_retorna_documento_por_item_id(monkeypatch):
    async def get_stub(self, item_id, version_id="active"):
        return fake_doc()
    monkeypatch.setattr(dsm_documents.DsmDocumentRepository, "get_by_item_id", get_stub)
    response = TestClient(app).get("/api/dsm/documents/tdah")
    assert response.status_code == 200
    assert response.json()["document"] == {"item_id": "tdah"}
