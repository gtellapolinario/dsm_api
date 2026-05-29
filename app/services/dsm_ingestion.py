"""DSM JSON validation and atomic ingestion service."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import DsmValidationError
from app.core.security import resolve_safe_path
from app.models import (
    DiagnosticChunk,
    DiagnosticDocument,
    DiagnosticIngestionRun,
    DiagnosticRegistry,
    DiagnosticVersion,
)
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
EXPECTED_RENDERABLE = 160
EXPECTED_REGISTRY = 50
ALLOWED_FTS_LANGUAGES = {"simple", "portuguese", "english", "spanish"}


@dataclass(frozen=True)
class ReleaseValidationReport:
    release_path: str | None
    manifest: dict[str, Any]
    counts: dict[str, int]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "release_path": self.release_path,
            "manifest_version_id": self.manifest.get("version_id"),
            "counts": self.counts,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        lines = [
            "# DSM release validation report",
            "",
            f"- Status: {'OK' if self.ok else 'FAILED'}",
            f"- Release path: `{self.release_path or '<manual paths>'}`",
            f"- Manifest version: `{self.manifest.get('version_id', '<missing>')}`",
            "",
            "## Counts",
        ]
        for key, value in self.counts.items():
            lines.append(f"- {key}: {value}")
        lines += ["", "## Errors"]
        lines += [f"- {error}" for error in self.errors] or ["- none"]
        lines += ["", "## Warnings"]
        lines += [f"- {warning}" for warning in self.warnings] or ["- none"]
        return "\n".join(lines) + "\n"


class DsmIngestionService:
    def __init__(self, session: AsyncSession | None):
        self.session = session
        self.settings = get_settings()
        self.chunking = DsmChunkingService()
        self.embeddings = EmbeddingService(self.settings)

    async def import_release(self, request: DsmImportRequest) -> DsmImportResult:
        if self.session is None:
            raise RuntimeError("import_release requires a database session")
        started = time.perf_counter()
        final_json_path = resolve_safe_path(request.final_json_path)
        registry_path = resolve_safe_path(request.registry_path)
        docs = self.load_final_json(final_json_path)
        minimal = self.load_registry_file(registry_path / "minimal_all.json", "MINIMAL")
        excluded = self.load_registry_file(registry_path / "excluded_all.json", "EXCLUDE")
        report = self.validate_release_payload(docs, minimal, excluded, manifest={})
        run = DiagnosticIngestionRun(
            version_id=request.version_id,
            status="started",
            source_package=request.source_package,
            final_json_path=str(final_json_path),
            registry_path=str(registry_path),
            report=report.to_dict(),
            errors={"errors": report.errors},
        )
        self.session.add(run)
        await self.session.flush()
        if report.errors:
            run.status = "validation_failed"
            run.finished_at = func.now()
            await self.session.commit()
            return DsmImportResult(version_id=request.version_id, errors=report.errors, warnings=report.warnings, status="validation_failed")

        version_repo = DsmVersionRepository(self.session)
        try:
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

            chunk_models = self._build_chunk_models(request.version_id, docs)
            if not chunk_models:
                raise DsmValidationError("No chunks were generated; version cannot be activated")

            embeddings_generated = 0
            should_embed = request.generate_embeddings and self.settings.embeddings_enabled
            if request.generate_embeddings and self.settings.embeddings_required and not self.embeddings.enabled:
                raise DsmValidationError("Embeddings are required but no embedding provider is enabled")
            if should_embed:
                vectors = await self.embeddings.embed_texts([chunk.chunk_text for chunk in chunk_models])
                if self.settings.embeddings_required and len(vectors) != len(chunk_models):
                    raise DsmValidationError("Embedding provider did not return a vector for every chunk")
                for chunk, vector in zip(chunk_models, vectors, strict=False):
                    chunk.embedding = vector
                embeddings_generated = len(vectors)
            await DsmChunkRepository(self.session).bulk_add(chunk_models)
            await self.session.flush()
            await self.populate_search_vectors(request.version_id)

            status = "imported_and_activated" if request.activate else "imported_draft"
            if request.activate:
                await version_repo.activate(request.version_id)
            run.status = status
            run.documents_imported = len(docs)
            run.registry_minimal = len(minimal)
            run.registry_excluded = len(excluded)
            run.chunks_generated = len(chunk_models)
            run.embeddings_generated = embeddings_generated
            run.finished_at = func.now()
            await self.session.commit()
            logger.info("dsm_ingestion_completed", extra={"duration_ms": round((time.perf_counter() - started) * 1000, 2)})
            return DsmImportResult(
                version_id=request.version_id, documents_imported=len(docs), registry_minimal=len(minimal), registry_excluded=len(excluded),
                chunks_generated=len(chunk_models), embeddings_generated=embeddings_generated, warnings=report.warnings, status=status,
            )
        except Exception as exc:
            await self.session.rollback()
            self.session.add(
                DiagnosticIngestionRun(
                    version_id=request.version_id,
                    status="failed",
                    source_package=request.source_package,
                    final_json_path=str(final_json_path),
                    registry_path=str(registry_path),
                    report=report.to_dict(),
                    errors={"errors": [str(exc)]},
                    finished_at=func.now(),
                )
            )
            await self.session.commit()
            logger.exception("dsm_ingestion_failed")
            raise exc

    def _build_chunk_models(self, version_id: str, docs: list[dict[str, Any]]) -> list[DiagnosticChunk]:
        chunk_models: list[DiagnosticChunk] = []
        for doc in docs:
            normalized = self.normalize_document(doc)
            chunk_input = {**doc, "item_id": normalized["item_id"], "chapter_id": normalized["chapter_id"], "category": normalized["category"]}
            for chunk in self.chunking.build_chunks(chunk_input):
                chunk_models.append(
                    DiagnosticChunk(
                        version_id=version_id,
                        document_item_id=normalized["item_id"],
                        chapter_id=normalized["chapter_id"],
                        chunk_type=chunk.chunk_type,
                        chunk_title=chunk.chunk_title,
                        chunk_text=chunk.chunk_text,
                        chunk_metadata=chunk.metadata,
                        token_count=len(chunk.chunk_text.split()),
                    )
                )
        return chunk_models

    def load_final_json(self, path: Path) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        if not path.exists() or not path.is_dir():
            raise DsmValidationError(f"final_json path does not exist or is not a directory: {path}")
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
                    return [{**inherited, **item} for item in payload[key] if isinstance(item, dict)]
            return [payload]
        return []

    def validate_all(self, docs: list[dict[str, Any]], registry: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        minimal = [row for row in registry if str(row.get("category", "")).upper() == "MINIMAL"]
        excluded = [row for row in registry if str(row.get("category", "")).upper() == "EXCLUDE"]
        report = self.validate_release_payload(docs, minimal, excluded, manifest={}, enforce_release_counts=False)
        return report.errors, report.warnings

    def validate_release_payload(
        self,
        docs: list[dict[str, Any]],
        minimal: list[dict[str, Any]],
        excluded: list[dict[str, Any]],
        *,
        manifest: dict[str, Any],
        enforce_release_counts: bool = True,
        release_path: Path | None = None,
    ) -> ReleaseValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        full = short = 0
        seen: dict[str, str] = {}
        doc_seen: set[str] = set()
        for doc in docs:
            try:
                n = self.normalize_document(doc)
                full += 1 if n["category"] == "FULL" else 0
                short += 1 if n["category"] == "SHORT" else 0
                if n["item_id"] in doc_seen:
                    errors.append(f"Duplicate renderable item_id: {n['item_id']}")
                doc_seen.add(n["item_id"])
                seen[n["item_id"]] = "final_json"
            except DsmValidationError as exc:
                errors.append(str(exc))
        for label, rows in (("MINIMAL", minimal), ("EXCLUDE", excluded)):
            for row in rows:
                try:
                    n = self.normalize_registry(row)
                    if n["category"] != label:
                        errors.append(f"Registry file {label} contains {n['category']}: {n['item_id']}")
                    if n["item_id"] in seen:
                        errors.append(f"Duplicate item_id across release: {n['item_id']}")
                    seen[n["item_id"]] = label
                except DsmValidationError as exc:
                    errors.append(str(exc))
        counts = {"full": full, "short": short, "renderable": len(docs), "minimal": len(minimal), "exclude": len(excluded), "registry": len(minimal) + len(excluded)}
        manifest_counts = manifest.get("counts", {}) if isinstance(manifest.get("counts"), dict) else {}
        for key, actual in counts.items():
            expected = manifest_counts.get(key)
            if expected is not None and expected != actual:
                errors.append(f"Manifest count mismatch for {key}: expected {expected}, got {actual}")
        if enforce_release_counts:
            if len(docs) != EXPECTED_RENDERABLE:
                errors.append(f"Renderable count must be {EXPECTED_RENDERABLE}, got {len(docs)}")
            if len(minimal) + len(excluded) != EXPECTED_REGISTRY:
                errors.append(f"Registry count must be {EXPECTED_REGISTRY}, got {len(minimal) + len(excluded)}")
        if not manifest and enforce_release_counts:
            warnings.append("manifest.json was not provided to validation")
        return ReleaseValidationReport(str(release_path) if release_path else None, manifest, counts, sorted(set(errors)), warnings)

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
        if doc["ui_mode"] not in UI_MODES or doc["ui_mode"] == "not_rendered":
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
        if self.session is None:
            raise RuntimeError("populate_search_vectors requires a database session")
        language = self.settings.fts_language.lower()
        if language not in ALLOWED_FTS_LANGUAGES:
            raise DsmValidationError(f"Unsupported FTS_LANGUAGE: {self.settings.fts_language}")
        await self.session.execute(
            text(f"UPDATE diagnostic_chunks SET search_vector = to_tsvector('{language}'::regconfig, coalesce(chunk_title,'') || ' ' || chunk_text) WHERE version_id = :version_id"),
            {"version_id": version_id},
        )
