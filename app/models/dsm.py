"""SQLAlchemy models for DSM operational data."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.database import Base

settings = get_settings()


class DiagnosticVersion(Base):
    __tablename__ = "diagnostic_versions"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'archived')", name="ck_versions_status"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    source_package: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    renderable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiagnosticDocument(Base):
    __tablename__ = "diagnostic_documents"
    __table_args__ = (
        UniqueConstraint("version_id", "item_id", name="uq_documents_version_item"),
        CheckConstraint("category IN ('FULL', 'SHORT')", name="ck_documents_category"),
        CheckConstraint("render_structured_interview IS TRUE", name="ck_documents_renderable"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    version_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_id: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_name: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    estrutura_diagnostica: Mapped[str] = mapped_column(Text, nullable=False)
    ui_mode: Mapped[str] = mapped_column(Text, nullable=False)
    render_structured_interview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    has_formal_severity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    severity_type: Mapped[str] = mapped_column(Text, nullable=False, default="nao_aplica")
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    version: Mapped[DiagnosticVersion] = relationship()


class DiagnosticRegistry(Base):
    __tablename__ = "diagnostic_registry"
    __table_args__ = (
        UniqueConstraint("version_id", "item_id", "category", name="uq_registry_version_item_category"),
        CheckConstraint("category IN ('MINIMAL', 'EXCLUDE')", name="ck_registry_category"),
        CheckConstraint("render_structured_interview IS FALSE", name="ck_registry_not_renderable"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    version_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_id: Mapped[str | None] = mapped_column(Text)
    chapter_name: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    registry_type: Mapped[str] = mapped_column(Text, nullable=False)
    render_structured_interview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_in_main_picker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_in_residual_panel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    canonical_chapter_id: Mapped[str | None] = mapped_column(Text)
    canonical_chapter_name: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiagnosticChunk(Base):
    __tablename__ = "diagnostic_chunks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    version_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False)
    document_item_id: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_id: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_title: Mapped[str | None] = mapped_column(Text)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions))
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
