"""hardening: ingestion runs, constraints and indexes

Revision ID: 20260529_0002
Revises: 20260528_0001
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260529_0002"
down_revision = "20260528_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="started"),
        sa.Column("source_package", sa.Text()),
        sa.Column("final_json_path", sa.Text()),
        sa.Column("registry_path", sa.Text()),
        sa.Column("documents_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registry_minimal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registry_excluded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embeddings_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('started', 'validation_failed', 'failed', 'imported_draft', 'imported_and_activated')", name="ck_ingestion_runs_status"),
    )
    op.create_index("idx_ingestion_runs_version_started", "diagnostic_ingestion_runs", ["version_id", "started_at"])

    op.create_check_constraint("ck_documents_ui_mode_not_empty", "diagnostic_documents", "char_length(ui_mode) > 0")
    op.create_check_constraint("ck_documents_structure_not_empty", "diagnostic_documents", "char_length(estrutura_diagnostica) > 0")
    op.create_check_constraint("ck_registry_type_not_empty", "diagnostic_registry", "char_length(registry_type) > 0")
    op.create_check_constraint("ck_chunks_type_not_empty", "diagnostic_chunks", "char_length(chunk_type) > 0")
    op.create_check_constraint("ck_chunks_text_not_empty", "diagnostic_chunks", "char_length(chunk_text) > 0")
    op.create_foreign_key(
        "fk_chunks_document_version_item",
        "diagnostic_chunks",
        "diagnostic_documents",
        ["version_id", "document_item_id"],
        ["version_id", "item_id"],
        ondelete="CASCADE",
    )

    op.create_index("idx_documents_frontend_picker", "diagnostic_documents", ["version_id", "active", "chapter_id", "category", "name"])
    op.create_index("idx_registry_frontend_picker", "diagnostic_registry", ["version_id", "category", "show_in_main_picker", "name"])
    op.create_index("idx_chunks_frontend_lookup", "diagnostic_chunks", ["version_id", "document_item_id", "chunk_type"])


def downgrade() -> None:
    op.drop_index("idx_chunks_frontend_lookup", table_name="diagnostic_chunks")
    op.drop_index("idx_registry_frontend_picker", table_name="diagnostic_registry")
    op.drop_index("idx_documents_frontend_picker", table_name="diagnostic_documents")
    op.drop_constraint("fk_chunks_document_version_item", "diagnostic_chunks", type_="foreignkey")
    op.drop_constraint("ck_chunks_text_not_empty", "diagnostic_chunks", type_="check")
    op.drop_constraint("ck_chunks_type_not_empty", "diagnostic_chunks", type_="check")
    op.drop_constraint("ck_registry_type_not_empty", "diagnostic_registry", type_="check")
    op.drop_constraint("ck_documents_structure_not_empty", "diagnostic_documents", type_="check")
    op.drop_constraint("ck_documents_ui_mode_not_empty", "diagnostic_documents", type_="check")
    op.drop_index("idx_ingestion_runs_version_started", table_name="diagnostic_ingestion_runs")
    op.drop_table("diagnostic_ingestion_runs")
