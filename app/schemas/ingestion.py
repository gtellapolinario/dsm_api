"""Schemas for DSM ingestion."""
from pydantic import BaseModel, Field


class DsmImportRequest(BaseModel):
    final_json_path: str
    registry_path: str
    version_id: str
    label: str
    source_package: str | None = None
    activate: bool = False
    generate_embeddings: bool = False
    notes: str | None = None


class DsmImportResult(BaseModel):
    version_id: str
    documents_imported: int = 0
    registry_minimal: int = 0
    registry_excluded: int = 0
    chunks_generated: int = 0
    embeddings_generated: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    status: str
