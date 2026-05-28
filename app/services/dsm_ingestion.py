"""DSM JSON validation and ingestion service."""
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import DsmValidationError
from app.models import DiagnosticChunk, DiagnosticDocument, DiagnosticRegistry, DiagnosticVersion
from app.repositories.dsm_chunks import DsmChunkRepository
from app.repositories.dsm_documents import DsmDocumentRepository
from app.repositories.dsm_registry import DsmRegistryRepository
from app.repositories.dsm_versions import DsmVersionRepository
from app.schemas.ingestion import DsmImportRequest, DsmImportResult
from app.services.chunking import DsmChunkingService
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

STRUCTURES = {
    "monothetic_puro", "monothetic_tripartite", "polythetic_monocluster", "polythetic_clusters_simetricos",
    "polythetic_clusters_assimetricos", "mixed_monothetic_polythetic", "polythetic_com_ancora", "temporal_topografico",
    "etiologico_externo", "qualitativo_descritivo", "episodico", "episodico_com_sintomas",
    "categoria_residual_especificada", "categoria_residual_nao_especificada", "referencia_cruzada_outro_capitulo", "administrativo",
}
SEVERITIES = {
    "nao_aplica", "ordinal_simples", "ordinal_por_dominio", "funcionamento_adaptativo", "necessidade_suporte_por_dominio",
    "contagem_sintomas_e_prejuizo", "frequencia_eventos", "marcador_biometrico", "episodio_atual", "pervasividade_contextual", "curso_ou_remissao",
}
UI_MODES = {
    "structured_full", "structured_compact", "qualitative_core", "residual_specified", "residual_unspecified", "cross_reference", "administrative_only", "not_rendered",
}


class DsmIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.chunking = DsmChunkingService()
        self.embeddings = EmbeddingService(self.settings)

    async def import_release(self, request: DsmImportRequest) -> DsmImportResult:
        docs = self.load_final_json(Path(request.final_json_path))
        minimal = self.load_registry_file(Path(request.registry_path) / "minimal_all.json", "MINIMAL")
        excluded = self.load_registry_file(Path(request.registry_path) / "excluded_all.json", "EXCLUDE")
        errors, warnings = self.validate_all(docs, minimal + excluded)
        if errors:
            return DsmImportResult(version_id=request.version_id, errors=errors, warnings=warnings, status="validation_failed")

        version_repo = DsmVersionRepository(self.session)
        if await version_repo.get(request.version_id):
            raise DsmValidationError(f"Version already exists: {request.version_id}")
        version = DiagnosticVersion(
            id=request.version_id, label=request.label, source_package=request.source_package,
            status="draft", renderable_count=len(docs), minimal_count=len(minimal), excluded_count=len(excluded), notes=request.notes,
        )
        await version_repo.create(version)

        documents = [DiagnosticDocument(version_id=request.version_id, **self.normalize_document(d), document=d) for d in docs]
        await DsmDocumentRepository(self.session).bulk_add(documents)
        registry_rows = [DiagnosticRegistry(version_id=request.version_id, **self.normalize_registry(r), document=r) for r in minimal + excluded]
        await DsmRegistryRepository(self.session).bulk_add(registry_rows)

        chunk_models: list[DiagnosticChunk] = []
        for doc in docs:
            normalized = self.normalize_document(doc)
            for chunk in self.chunking.build_chunks({**doc, "item_id": normalized["item_id"], "chapter_id": normalized["chapter_id"], "category": normalized["category"]}):
                chunk_models.append(
                    DiagnosticChunk(
                        version_id=request.version_id,
                        document_item_id=normalized["item_id"],
                        chapter_id=normalized["chapter_id"],
                        chunk_type=chunk.chunk_type,
                        chunk_title=chunk.chunk_title,
                        chunk_text=chunk.chunk_text,
                        chunk_metadata=chunk.metadata,
                        token_count=len(chunk.chunk_text.split()),
                    )
                )
        embeddings_generated = 0
        should_embed = request.generate_embeddings and self.embeddings.enabled
        if should_embed:
            vectors = await self.embeddings.embed_texts([chunk.chunk_text for chunk in chunk_models])
            for chunk, vector in zip(chunk_models, vectors, strict=False):
                chunk.embedding = vector
            embeddings_generated = len(vectors)
        await DsmChunkRepository(self.session).bulk_add(chunk_models)
        await self.session.flush()
        await self.populate_search_vectors(request.version_id)
        if request.activate:
            await version_repo.activate(request.version_id)
        await self.session.commit()
        return DsmImportResult(
            version_id=request.version_id, documents_imported=len(docs), registry_minimal=len(minimal), registry_excluded=len(excluded),
            chunks_generated=len(chunk_models), embeddings_generated=embeddings_generated, warnings=warnings,
            status="imported_and_activated" if request.activate else "imported_draft",
        )

    def load_final_json(self, path: Path) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for file in sorted(path.glob("*.json")):
            payload = json.loads(file.read_text(encoding="utf-8"))
            docs.extend(self._extract_items(payload, inherit_fields=("chapter_id", "chapter_name")))
        return docs

    def load_registry_file(self, path: Path, category: str) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = self._extract_items(json.loads(path.read_text(encoding="utf-8")))
        for row in rows:
            row.setdefault("category", category)
        return rows

    def _extract_items(self, payload: Any, inherit_fields: tuple[str, ...] = ()) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [p for p in payload if isinstance(p, dict)]
        if isinstance(payload, dict):
            for key in ("items", "documents", "disorders", "registry", "entries"):
                if isinstance(payload.get(key), list):
                    inherited = {field: payload[field] for field in inherit_fields if payload.get(field)}
                    items: list[dict[str, Any]] = []
                    for item in payload[key]:
                        if isinstance(item, dict):
                            items.append({**inherited, **item})
                    return items
            return [payload]
        return []

    def validate_all(self, docs: list[dict[str, Any]], registry: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        seen: set[str] = set()
        for doc in docs:
            try:
                n = self.normalize_document(doc)
                if n["item_id"] in seen:
                    errors.append(f"Duplicate renderable item_id: {n['item_id']}")
                seen.add(n["item_id"])
            except DsmValidationError as exc:
                errors.append(str(exc))
        for row in registry:
            try:
                self.normalize_registry(row)
            except DsmValidationError as exc:
                errors.append(str(exc))
        return errors, warnings

    def normalize_document(self, doc: dict[str, Any]) -> dict[str, Any]:
        item_id = doc.get("item_id") or doc.get("id") or doc.get("slug")
        name = doc.get("name") or doc.get("title")
        category = str(doc.get("category") or "").upper()
        severity = doc.get("severity") if isinstance(doc.get("severity"), dict) else {}
        severity_type = severity.get("type") or doc.get("severity_type") or "nao_aplica"
        has_formal_severity = bool(severity.get("has_formal_severity") or doc.get("has_formal_severity", False))
        required = {"item_id": item_id, "name": name, "chapter_id": doc.get("chapter_id"), "category": category,
                    "estrutura_diagnostica": doc.get("estrutura_diagnostica"), "ui_mode": doc.get("ui_mode")}
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise DsmValidationError(f"Renderable document missing {missing}: {name or item_id or '<unknown>'}")
        if category not in {"FULL", "SHORT"}:
            raise DsmValidationError(f"Renderable document has invalid category {category}: {item_id}")
        if doc.get("render_structured_interview", True) is not True:
            raise DsmValidationError(f"Renderable document must render structured interview: {item_id}")
        if not doc.get("diagnostic_rule"):
            raise DsmValidationError(f"Renderable document missing diagnostic_rule: {item_id}")
        if doc["estrutura_diagnostica"] not in STRUCTURES:
            raise DsmValidationError(f"Invalid estrutura_diagnostica for {item_id}: {doc['estrutura_diagnostica']}")
        if str(severity_type) not in SEVERITIES:
            raise DsmValidationError(f"Invalid severity.type for {item_id}: {severity_type}")
        if doc["ui_mode"] not in UI_MODES:
            raise DsmValidationError(f"Invalid ui_mode for {item_id}: {doc['ui_mode']}")
        return {
            "item_id": str(item_id), "chapter_id": str(doc.get("chapter_id")), "chapter_name": str(doc.get("chapter_name") or ""),
            "name": str(name), "category": category, "estrutura_diagnostica": str(doc["estrutura_diagnostica"]), "ui_mode": str(doc["ui_mode"]),
            "render_structured_interview": True, "has_formal_severity": has_formal_severity, "severity_type": str(severity_type), "active": True,
        }

    def normalize_registry(self, row: dict[str, Any]) -> dict[str, Any]:
        item_id = row.get("item_id") or row.get("id") or row.get("slug")
        name = row.get("name") or row.get("title")
        category = str(row.get("category") or row.get("registry_type") or "").upper()
        if not item_id or not name:
            raise DsmValidationError(f"Registry item missing item_id/name: {name or item_id or '<unknown>'}")
        if category not in {"MINIMAL", "EXCLUDE"}:
            raise DsmValidationError(f"Registry item has invalid category {category}: {item_id}")
        if row.get("render_structured_interview", False) is not False:
            raise DsmValidationError(f"Registry item cannot render structured interview: {item_id}")
        return {
            "item_id": str(item_id), "name": str(name), "chapter_id": row.get("chapter_id"), "chapter_name": row.get("chapter_name"),
            "category": category, "registry_type": str(row.get("registry_type") or category.lower()), "render_structured_interview": False,
            "show_in_main_picker": bool(row.get("show_in_main_picker", False)), "show_in_residual_panel": bool(row.get("show_in_residual_panel", False)),
            "canonical_chapter_id": row.get("canonical_chapter_id"), "canonical_chapter_name": row.get("canonical_chapter_name"),
            "reason": row.get("reason"), "active": True,
        }

    async def populate_search_vectors(self, version_id: str) -> None:
        await self.session.execute(
            text("UPDATE diagnostic_chunks SET search_vector = to_tsvector(:lang, coalesce(chunk_title,'') || ' ' || chunk_text) WHERE version_id = :version_id"),
            {"lang": self.settings.fts_language, "version_id": version_id},
        )
