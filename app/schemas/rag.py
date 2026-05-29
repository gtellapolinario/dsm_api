"""Schemas for RAG endpoints."""
from pydantic import BaseModel, Field

from app.schemas.search import DsmSearchResultItem


class DsmRagCitation(BaseModel):
    document_item_id: str
    chunk_id: str
    chunk_type: str
    chunk_title: str | None = None



class DsmRagRequest(BaseModel):
    question: str = Field(min_length=1, json_schema_extra={"example": "Quais evidências diferenciam TDAH de ansiedade?"})
    version_id: str = "active"
    chapter_id: str | None = None
    item_id: str | None = None
    chunk_types: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=30)
    use_vector: bool = True
    use_fts: bool = True
    allow_fallback: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "Quais evidências diferenciam TDAH de ansiedade?", "version_id": "active", "top_k": 5}
            ]
        }
    }


class DsmRagResponse(BaseModel):
    question: str
    version_id: str
    answer: str | None = None
    message: str | None = None
    chunks: list[DsmSearchResultItem]
    citations: list[DsmRagCitation] = Field(default_factory=list)
