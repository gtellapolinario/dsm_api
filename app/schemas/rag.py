"""Schemas for RAG endpoints."""
from pydantic import BaseModel, Field

from app.schemas.search import DsmSearchResultItem


class DsmRagRequest(BaseModel):
    question: str = Field(min_length=1)
    version_id: str = "active"
    chapter_id: str | None = None
    item_id: str | None = None
    chunk_types: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=30)
    use_vector: bool = True
    use_fts: bool = True
    allow_fallback: bool = True


class DsmRagResponse(BaseModel):
    question: str
    version_id: str
    answer: str | None = None
    message: str | None = None
    chunks: list[DsmSearchResultItem]
