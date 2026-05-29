"""Build a derived DSM knowledge graph from canonical PostgreSQL tables."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.schemas import GraphEdge, GraphExport, GraphNode
from app.models import DiagnosticChunk, DiagnosticDocument, DiagnosticRegistry, DiagnosticVersion

SIMILARITY_EDGE_LIMIT = 200


def _safe_part(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value not in (None, "") else fallback).strip()
    return text.replace(" ", "_").replace("/", "_").replace(":", "_") or fallback


def _item_label(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("label", "name", "title", "text", "description", "value", "criterion"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return "; ".join(f"{k}: {v}" for k, v in value.items() if not isinstance(v, (dict, list)))[:240] or str(value)[:240]
    return str(value)


def get_list_field(document: dict[str, Any], aliases: Iterable[str]) -> list[Any]:
    """Return the first list-ish field found by aliases, tolerating nested DSM JSON variations."""
    for alias in aliases:
        if alias in document:
            value = document[alias]
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for nested_key in ("items", "criteria", "criterios", "entries", "values"):
                    nested = value.get(nested_key)
                    if isinstance(nested, list):
                        return nested
                return list(value.values())
            if isinstance(value, str) and value.strip():
                return [value]
    for container in ("diagnostic_criteria", "diagnostico", "structured_interview", "clinical_features"):
        nested = document.get(container)
        if isinstance(nested, dict):
            found = get_list_field(nested, aliases)
            if found:
                return found
    return []


class DsmGraphBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.warnings: list[str] = []

    async def build_graph(self, version_id: str) -> GraphExport:
        resolved_version_id = await self._resolve_version_id(version_id)
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        def add_node(node: GraphNode) -> None:
            nodes.setdefault(node.id, node)

        def add_edge(edge: GraphEdge) -> None:
            if edge.source in nodes and edge.target in nodes:
                edges.setdefault(edge.id, edge)
            else:
                self.warnings.append(f"Skipping orphan edge {edge.id}: {edge.source} -> {edge.target}")

        add_node(GraphNode(id=f"version:{resolved_version_id}", type="Version", label=resolved_version_id))

        documents = list((await self.session.scalars(
            select(DiagnosticDocument)
            .where(DiagnosticDocument.version_id == resolved_version_id, DiagnosticDocument.active.is_(True))
            .order_by(DiagnosticDocument.chapter_id, DiagnosticDocument.name)
        )).all())
        registry_rows = list((await self.session.scalars(
            select(DiagnosticRegistry)
            .where(DiagnosticRegistry.version_id == resolved_version_id, DiagnosticRegistry.active.is_(True))
            .order_by(DiagnosticRegistry.chapter_id, DiagnosticRegistry.name)
        )).all())
        chunks = list((await self.session.scalars(
            select(DiagnosticChunk)
            .where(DiagnosticChunk.version_id == resolved_version_id)
            .order_by(DiagnosticChunk.document_item_id, DiagnosticChunk.chunk_type)
        )).all())

        chapters: dict[str, str] = {}
        for doc in documents:
            chapters[doc.chapter_id] = doc.chapter_name
        for row in registry_rows:
            if row.chapter_id:
                chapters[row.chapter_id] = row.chapter_name or row.chapter_id
            if row.canonical_chapter_id:
                chapters.setdefault(row.canonical_chapter_id, row.canonical_chapter_name or row.canonical_chapter_id)
        for chunk in chunks:
            chapters.setdefault(chunk.chapter_id, chunk.chapter_id)

        for chapter_id, chapter_name in sorted(chapters.items()):
            chapter_node = f"chapter:{chapter_id}"
            add_node(GraphNode(id=chapter_node, type="Chapter", label=chapter_name or chapter_id, metadata={"chapter_id": chapter_id}))
            add_edge(GraphEdge(id=f"version:{resolved_version_id}:HAS_CHAPTER:{chapter_id}", source=f"version:{resolved_version_id}", target=chapter_node, type="HAS_CHAPTER"))

        disorder_ids: set[str] = set()
        severity_groups: dict[str, list[str]] = defaultdict(list)
        structure_groups: dict[str, list[str]] = defaultdict(list)
        for doc in documents:
            disorder_id = f"disorder:{doc.item_id}"
            disorder_ids.add(disorder_id)
            add_node(GraphNode(
                id=disorder_id,
                type="Disorder",
                label=doc.name,
                metadata={
                    "item_id": doc.item_id,
                    "chapter_id": doc.chapter_id,
                    "category": doc.category,
                    "estrutura_diagnostica": doc.estrutura_diagnostica,
                    "severity_type": doc.severity_type,
                    "ui_mode": doc.ui_mode,
                    "render_structured_interview": doc.render_structured_interview,
                },
            ))
            add_edge(GraphEdge(id=f"{disorder_id}:BELONGS_TO_CHAPTER:{doc.chapter_id}", source=disorder_id, target=f"chapter:{doc.chapter_id}", type="BELONGS_TO_CHAPTER"))
            self._taxonomy_edge(add_node, add_edge, disorder_id, "StructureType", "structure", doc.estrutura_diagnostica, "HAS_STRUCTURE_TYPE")
            self._taxonomy_edge(add_node, add_edge, disorder_id, "UiMode", "ui_mode", doc.ui_mode, "HAS_UI_MODE")
            self._taxonomy_edge(add_node, add_edge, disorder_id, "SeverityType", "severity", doc.severity_type, "HAS_SEVERITY_TYPE")
            severity_groups[doc.severity_type].append(disorder_id)
            structure_groups[doc.estrutura_diagnostica].append(disorder_id)
            self._extract_document_nodes(add_node, add_edge, disorder_id, doc.item_id, doc.document or {})

        for row in registry_rows:
            registry_id = f"registry:{row.item_id}:{row.category}"
            add_node(GraphNode(
                id=registry_id,
                type="RegistryItem",
                label=row.name,
                metadata={
                    "item_id": row.item_id,
                    "category": row.category,
                    "registry_type": row.registry_type,
                    "chapter_id": row.chapter_id,
                    "reason": row.reason,
                    "canonical_chapter_id": row.canonical_chapter_id,
                },
            ))
            if row.chapter_id:
                add_edge(GraphEdge(id=f"{registry_id}:REGISTRY_BELONGS_TO_CHAPTER:{row.chapter_id}", source=registry_id, target=f"chapter:{row.chapter_id}", type="REGISTRY_BELONGS_TO_CHAPTER"))
            if row.canonical_chapter_id:
                add_edge(GraphEdge(id=f"{registry_id}:CROSS_REFERENCES:{row.canonical_chapter_id}", source=registry_id, target=f"chapter:{row.canonical_chapter_id}", type="CROSS_REFERENCES"))

        for chunk in chunks:
            chunk_id = f"chunk:{chunk.id}"
            add_node(GraphNode(
                id=chunk_id,
                type="Chunk",
                label=chunk.chunk_title or chunk.chunk_type,
                metadata={
                    "chunk_id": str(chunk.id),
                    "chunk_type": chunk.chunk_type,
                    "document_item_id": chunk.document_item_id,
                    "chapter_id": chunk.chapter_id,
                },
            ))
            source = f"disorder:{chunk.document_item_id}"
            if source in disorder_ids:
                add_edge(GraphEdge(id=f"{source}:HAS_CHUNK:{chunk.id}", source=source, target=chunk_id, type="HAS_CHUNK"))
            else:
                self.warnings.append(f"Chunk {chunk.id} points to missing disorder {chunk.document_item_id}")

        self._add_similarity_edges(edges, severity_groups, "SHARES_SEVERITY_TYPE", "severity_type")
        self._add_similarity_edges(edges, structure_groups, "SHARES_STRUCTURE_TYPE", "structure_type")

        counts = self._counts(nodes.values(), edges.values())
        return GraphExport(
            version_id=resolved_version_id,
            generated_at=datetime.now(UTC).isoformat(),
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            counts=counts,
            warnings=list(dict.fromkeys(self.warnings)),
        )

    async def _resolve_version_id(self, version_id: str) -> str:
        if version_id != "active":
            return version_id
        active = await self.session.scalar(select(DiagnosticVersion).where(DiagnosticVersion.status == "active"))
        if active is None:
            raise ValueError("No active DSM version found")
        return active.id

    def _taxonomy_edge(self, add_node, add_edge, disorder_id: str, node_type: str, prefix: str, value: str, edge_type: str) -> None:
        node_id = f"{prefix}:{_safe_part(value)}"
        add_node(GraphNode(id=node_id, type=node_type, label=value or "unknown"))
        add_edge(GraphEdge(id=f"{disorder_id}:{edge_type}:{_safe_part(value)}", source=disorder_id, target=node_id, type=edge_type))

    def _extract_document_nodes(self, add_node, add_edge, disorder_id: str, item_id: str, document: dict[str, Any]) -> None:
        specs = [
            ("criterion", "Criterion", "HAS_CRITERION", ["criteria", "criterios"]),
            ("cluster", "Cluster", "HAS_CLUSTER", ["clusters", "clusteres"]),
            ("specifier", "Specifier", "HAS_SPECIFIER", ["specifiers", "especificadores"]),
            ("subtype", "Subtype", "HAS_SUBTYPE", ["subtypes_presentations", "subtypes", "presentations", "subtipos_apresentacoes"]),
            ("operational_profile", "OperationalProfile", "HAS_OPERATIONAL_PROFILE", ["operational_profiles", "perfis_operacionais"]),
            ("differential", "Differential", "HAS_DIFFERENTIAL", ["critical_differentials", "diferenciais_criticos", "differentials"]),
            ("key_question", "KeyQuestion", "HAS_KEY_QUESTION", ["key_questions", "perguntas_chave"]),
            ("alert", "Alert", "HAS_ALERT", ["alerts", "alertas"]),
        ]
        for prefix, node_type, edge_type, aliases in specs:
            for index, value in enumerate(get_list_field(document, aliases), start=1):
                label = _item_label(value)
                if not label:
                    continue
                node_id = f"{prefix}:{item_id}:{index}"
                add_node(GraphNode(id=node_id, type=node_type, label=label[:240], metadata={"item_id": item_id, "raw": value}))
                add_edge(GraphEdge(id=f"{disorder_id}:{edge_type}:{index}", source=disorder_id, target=node_id, type=edge_type))

    def _add_similarity_edges(self, edges: dict[str, GraphEdge], groups: dict[str, list[str]], edge_type: str, key_name: str) -> None:
        created = 0
        truncated = False
        for value, ids in sorted(groups.items()):
            unique_ids = sorted(set(ids))
            for index, source in enumerate(unique_ids):
                for target in unique_ids[index + 1:]:
                    if created >= SIMILARITY_EDGE_LIMIT:
                        truncated = True
                        break
                    edge_id = f"{source}:{edge_type}:{target.split(':', 1)[1]}"
                    edges.setdefault(edge_id, GraphEdge(source=source, target=target, id=edge_id, type=edge_type, metadata={key_name: value}))
                    created += 1
                if truncated:
                    break
            if truncated:
                break
        if truncated:
            self.warnings.append(f"{edge_type} limited to {SIMILARITY_EDGE_LIMIT} edges to avoid combinatorial explosion")

    def _counts(self, nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> dict[str, int]:
        counts: dict[str, int] = {"nodes": 0, "edges": 0}
        for node in nodes:
            counts["nodes"] += 1
            counts[f"nodes_{node.type}"] = counts.get(f"nodes_{node.type}", 0) + 1
        for edge in edges:
            counts["edges"] += 1
            counts[f"edges_{edge.type}"] = counts.get(f"edges_{edge.type}", 0) + 1
        return counts
