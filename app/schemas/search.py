"""Schemas for search endpoints."""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DsmSearchRequest(BaseModel):
    query: str = Field(min_length=1, json_schema_extra={"example": "critérios para transtorno de pânico"})
    version_id: str = "active"
    chapter_id: str | None = None
    item_id: str | None = None
    category: str | None = None
    chunk_types: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    use_vector: bool = True
    use_fts: bool = True
    allow_fallback: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "critérios para transtorno de pânico", "version_id": "active", "top_k": 8, "use_vector": False, "use_fts": True}
            ]
        }
    }


class DsmSearchResultItem(BaseModel):
    chunk_id: UUID | str
    document_item_id: str
    document_name: str | None = None
    chapter_id: str
    chunk_type: str
    chunk_title: str | None = None
    chunk_text: str
    vector_score: float | None = None
    text_score: float | None = None
    hybrid_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class DsmSearchResult(BaseModel):
    query: str
    version_id: str
    results: list[DsmSearchResultItem]
