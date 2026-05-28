"""initial DSM operational schema

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "diagnostic_versions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("source_package", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("renderable_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minimal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("excluded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft', 'active', 'archived')", name="ck_versions_status"),
    )
    op.create_index("uq_diagnostic_versions_single_active", "diagnostic_versions", ["status"], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_table(
        "diagnostic_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", sa.Text(), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("chapter_id", sa.Text(), nullable=False),
        sa.Column("chapter_name", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("estrutura_diagnostica", sa.Text(), nullable=False),
        sa.Column("ui_mode", sa.Text(), nullable=False),
        sa.Column("render_structured_interview", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("has_formal_severity", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("severity_type", sa.Text(), nullable=False, server_default="nao_aplica"),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_id", "item_id", name="uq_documents_version_item"),
        sa.CheckConstraint("category IN ('FULL', 'SHORT')", name="ck_documents_category"),
        sa.CheckConstraint("render_structured_interview IS TRUE", name="ck_documents_renderable"),
    )
    op.create_table(
        "diagnostic_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", sa.Text(), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("chapter_id", sa.Text()),
        sa.Column("chapter_name", sa.Text()),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("registry_type", sa.Text(), nullable=False),
        sa.Column("render_structured_interview", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_in_main_picker", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_in_residual_panel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("canonical_chapter_id", sa.Text()),
        sa.Column("canonical_chapter_name", sa.Text()),
        sa.Column("reason", sa.Text()),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_id", "item_id", "category", name="uq_registry_version_item_category"),
        sa.CheckConstraint("category IN ('MINIMAL', 'EXCLUDE')", name="ck_registry_category"),
        sa.CheckConstraint("render_structured_interview IS FALSE", name="ck_registry_not_renderable"),
    )
    op.create_table(
        "diagnostic_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", sa.Text(), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_item_id", sa.Text(), nullable=False),
        sa.Column("chapter_id", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.Text(), nullable=False),
        sa.Column("chunk_title", sa.Text()),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("token_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name, table, cols in [
        ("idx_diagnostic_documents_version", "diagnostic_documents", ["version_id"]),
        ("idx_diagnostic_documents_chapter", "diagnostic_documents", ["version_id", "chapter_id"]),
        ("idx_diagnostic_documents_category", "diagnostic_documents", ["version_id", "category"]),
        ("idx_diagnostic_documents_structure", "diagnostic_documents", ["estrutura_diagnostica"]),
        ("idx_diagnostic_registry_version", "diagnostic_registry", ["version_id"]),
        ("idx_diagnostic_registry_category", "diagnostic_registry", ["version_id", "category"]),
        ("idx_diagnostic_chunks_version", "diagnostic_chunks", ["version_id"]),
        ("idx_diagnostic_chunks_document", "diagnostic_chunks", ["version_id", "document_item_id"]),
        ("idx_diagnostic_chunks_type", "diagnostic_chunks", ["version_id", "chunk_type"]),
    ]:
        op.create_index(name, table, cols)
    op.create_index("idx_diagnostic_documents_document_gin", "diagnostic_documents", ["document"], postgresql_using="gin")
    op.create_index("idx_diagnostic_chunks_fts", "diagnostic_chunks", ["search_vector"], postgresql_using="gin")
    op.execute("CREATE INDEX idx_diagnostic_chunks_embedding_hnsw ON diagnostic_chunks USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.drop_table("diagnostic_chunks")
    op.drop_table("diagnostic_registry")
    op.drop_table("diagnostic_documents")
    op.drop_index("uq_diagnostic_versions_single_active", table_name="diagnostic_versions")
    op.drop_table("diagnostic_versions")
