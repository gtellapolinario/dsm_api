"""Pydantic schemas for DSM resources."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DsmVersionCreate(BaseModel):
    id: str
    label: str
    source_package: str | None = None
    notes: str | None = None


class DsmVersionRead(BaseModel):
    id: str
    label: str
    source_package: str | None
    status: str
    renderable_count: int
    minimal_count: int
    excluded_count: int
    notes: str | None
    created_at: datetime | None = None
    activated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class DsmDocumentListItem(BaseModel):
    id: UUID | str
    version_id: str
    item_id: str
    chapter_id: str
    chapter_name: str
    name: str
    category: str
    estrutura_diagnostica: str
    ui_mode: str
    render_structured_interview: bool
    has_formal_severity: bool
    severity_type: str
    active: bool
    model_config = ConfigDict(from_attributes=True)


class DsmDocumentRead(DsmDocumentListItem):
    document: dict[str, Any]


class DsmRegistryRead(BaseModel):
    id: UUID | str
    version_id: str
    item_id: str
    name: str
    chapter_id: str | None = None
    chapter_name: str | None = None
    category: str
    registry_type: str
    render_structured_interview: bool
    show_in_main_picker: bool
    show_in_residual_panel: bool
    canonical_chapter_id: str | None = None
    canonical_chapter_name: str | None = None
    reason: str | None = None
    document: dict[str, Any]
    active: bool
    model_config = ConfigDict(from_attributes=True)


class DsmChunkRead(BaseModel):
    id: UUID | str
    version_id: str
    document_item_id: str
    chapter_id: str
    chunk_type: str
    chunk_title: str | None = None
    chunk_text: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="chunk_metadata")
    token_count: int | None = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
