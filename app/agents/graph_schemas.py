"""Typed schemas returned by DSM graph agents."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UsedGraphNode(BaseModel):
    id: str
    type: str
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsedGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsedChunk(BaseModel):
    id: str
    document_item_id: str | None = None
    chapter_id: str | None = None
    chunk_type: str | None = None
    title: str | None = None
    text: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphAgentAnswer(BaseModel):
    answer: str
    version_id: str
    confidence: Literal["high", "medium", "low"]
    used_nodes: list[UsedGraphNode] = Field(default_factory=list)
    used_edges: list[UsedGraphEdge] = Field(default_factory=list)
    used_chunks: list[UsedChunk] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)


class GraphAuditFinding(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    node_id: str | None = None
    edge_id: str | None = None
    problem: str
    evidence: str | None = None
    recommendation: str


class GraphAuditResult(BaseModel):
    version_id: str
    status: Literal["PASS", "PASS_WITH_WARNINGS", "BLOCKED"]
    findings: list[GraphAuditFinding] = Field(default_factory=list)
    checked_rules: list[str] = Field(default_factory=list)


class GraphQueryPlan(BaseModel):
    query: str
    version_id: str
    intended_operations: list[str]
    node_filters: dict[str, str | None] = Field(default_factory=dict)
    edge_filters: dict[str, str | None] = Field(default_factory=dict)
    traversal_depth: int = 1
    requires_vector_search: bool = False
    requires_graph_traversal: bool = True
