"""Structured Pydantic output schemas for DSM agents."""
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.search import DsmSearchResultItem


class UsedChunk(BaseModel):
    chunk_id: str
    document_item_id: str
    chapter_id: str
    chunk_type: str
    chunk_title: str | None = None
    hybrid_score: float | None = None


class AgentObservability(BaseModel):
    query: str
    used_chunks: list[UsedChunk] = Field(default_factory=list)
    dsm_version: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    confidence: float = Field(ge=0, le=1)
    response_time_ms: int


class DsmAgentRequest(BaseModel):
    query: str = Field(min_length=1)
    version_id: str = "active"
    chapter_id: str | None = None
    item_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=30)
    use_vector: bool = True
    use_fts: bool = True
    allow_fallback: bool = True


class DsmAnswerRequest(DsmAgentRequest):
    audience: Literal["clinician", "patient", "student"] = "clinician"


class ChunkExplanation(BaseModel):
    chunk_id: str
    contribution: str


class DsmAnswerOutput(BaseModel):
    answer: str
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    used_chunks: list[UsedChunk] = Field(default_factory=list)
    chunk_explanations: list[ChunkExplanation] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    order: int = Field(ge=1)
    question: str
    target_criterion: str | None = None
    source_chunk_id: str | None = None


class DsmInterviewPlanRequest(DsmAgentRequest):
    clinical_context: str | None = None


class DsmInterviewPlanOutput(BaseModel):
    plan_title: str
    questions: list[InterviewQuestion] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    used_chunks: list[UsedChunk] = Field(default_factory=list)


class DsmCriticRequest(DsmAgentRequest):
    report_text: str = Field(min_length=1)


class DsmCriticIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    issue: str
    recommendation: str
    source_chunk_id: str | None = None


class DsmCriticOutput(BaseModel):
    summary: str
    issues: list[DsmCriticIssue] = Field(default_factory=list)
    revised_clinical_text: str | None = None
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    used_chunks: list[UsedChunk] = Field(default_factory=list)


class DsmAgentResponse(BaseModel):
    query: str
    version_id: str
    output: DsmAnswerOutput | DsmInterviewPlanOutput | DsmCriticOutput
    chunks: list[DsmSearchResultItem]
    observability: AgentObservability
