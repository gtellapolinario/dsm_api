"""Local JSON store for derived DSM graph exports."""
from __future__ import annotations

import json
from pathlib import Path

from app.graph.schemas import GraphExport


class LocalGraphStore:
    def __init__(self, export_dir: str):
        self.export_dir = Path(export_dir)

    async def save(self, graph: GraphExport) -> Path:
        version_dir = self.export_dir / graph.version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        graph_path = version_dir / "graph.json"
        graph_path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        (version_dir / "nodes.json").write_text(json.dumps([n.model_dump() for n in graph.nodes], ensure_ascii=False, indent=2), encoding="utf-8")
        (version_dir / "edges.json").write_text(json.dumps([e.model_dump() for e in graph.edges], ensure_ascii=False, indent=2), encoding="utf-8")
        (version_dir / "GRAPH_REPORT.md").write_text(self._report(graph), encoding="utf-8")
        return graph_path

    async def load(self, version_id: str) -> GraphExport | None:
        if version_id == "active":
            candidates = sorted(self.export_dir.glob("*/graph.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            graph_path = candidates[0] if candidates else None
        else:
            graph_path = self.export_dir / version_id / "graph.json"
        if graph_path is None or not graph_path.exists():
            return None
        return GraphExport.model_validate_json(graph_path.read_text(encoding="utf-8"))

    async def list_exports(self) -> list[dict]:
        if not self.export_dir.exists():
            return []
        rows = []
        for graph_path in sorted(self.export_dir.glob("*/graph.json")):
            stat = graph_path.stat()
            rows.append({
                "version_id": graph_path.parent.name,
                "graph_path": str(graph_path),
                "updated_at": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
        return rows

    def _report(self, graph: GraphExport) -> str:
        count_lines = "\n".join(f"- {key}: {value}" for key, value in sorted(graph.counts.items()))
        warning_lines = "\n".join(f"- {warning}" for warning in graph.warnings) or "- none"
        return f"""# DSM Knowledge Graph Export\n\n- Version: `{graph.version_id}`\n- Generated at: `{graph.generated_at}`\n- Nodes: {len(graph.nodes)}\n- Edges: {len(graph.edges)}\n\n## Counts\n\n{count_lines}\n\n## Warnings\n\n{warning_lines}\n"""
