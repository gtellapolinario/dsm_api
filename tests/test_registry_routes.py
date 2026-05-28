from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import dsm_registry


def registry_row(category):
    return SimpleNamespace(
        id=uuid4(), version_id="v1", item_id="x", name="X", chapter_id="01", chapter_name="Neuro",
        category=category, registry_type=category.lower(), render_structured_interview=False, show_in_main_picker=False,
        show_in_residual_panel=False, canonical_chapter_id=None, canonical_chapter_name=None, reason=None,
        document={"item_id": "x"}, active=True,
    )


def test_lista_minimal(monkeypatch):
    async def list_stub(self, version_id="active", category=None):
        return [registry_row(category)]
    monkeypatch.setattr(dsm_registry.DsmRegistryRepository, "list", list_stub)
    response = TestClient(app).get("/api/dsm/registry/minimal")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "MINIMAL"


def test_lista_excluded(monkeypatch):
    async def list_stub(self, version_id="active", category=None):
        return [registry_row(category)]
    monkeypatch.setattr(dsm_registry.DsmRegistryRepository, "list", list_stub)
    response = TestClient(app).get("/api/dsm/registry/excluded")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "EXCLUDE"


def test_registry_render_structured_interview_false(monkeypatch):
    async def list_stub(self, version_id="active", category=None):
        return [registry_row("MINIMAL")]
    monkeypatch.setattr(dsm_registry.DsmRegistryRepository, "list", list_stub)
    response = TestClient(app).get("/api/dsm/registry")
    assert response.json()[0]["render_structured_interview"] is False
