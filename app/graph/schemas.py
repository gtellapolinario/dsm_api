"""Pydantic schemas for the derived DSM knowledge graph."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GraphNodeType = Literal[
    "Version",
    "Chapter",
    "Disorder",
    "RegistryItem",
    "Criterion",
    "Cluster",
    "SeverityType",
    "Specifier",
    "Subtype",
    "OperationalProfile",
    "Differential",
    "KeyQuestion",
    "Alert",
    "Chunk",
    "StructureType",
    "UiMode",
]

GraphEdgeType = Literal[
    "HAS_CHAPTER",
    "BELONGS_TO_CHAPTER",
    "HAS_CRITERION",
    "HAS_CLUSTER",
    "HAS_SEVERITY_TYPE",
    "HAS_SPECIFIER",
    "HAS_SUBTYPE",
    "HAS_OPERATIONAL_PROFILE",
    "HAS_DIFFERENTIAL",
    "HAS_KEY_QUESTION",
    "HAS_ALERT",
    "HAS_CHUNK",
    "HAS_STRUCTURE_TYPE",
    "HAS_UI_MODE",
    "REGISTRY_BELONGS_TO_CHAPTER",
    "CROSS_REFERENCES",
    "SHARES_SEVERITY_TYPE",
    "SHARES_STRUCTURE_TYPE",
    "RELATED_TO",
]


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphExport(BaseModel):
    version_id: str
    generated_at: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)


class GraphQueryRequest(BaseModel):
    version_id: str = "active"
    node_type: str | None = None
    edge_type: str | None = None
    query: str | None = None
    node_id: str | None = None
    depth: int = 1
    limit: int = 100


class GraphRebuildRequest(BaseModel):
    version_id: str = "active"
    persist: bool = True
    send_to_graphify: bool = False
