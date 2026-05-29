"""Export the derived DSM knowledge graph from canonical DB tables."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.graph_service import DsmGraphService


async def _run(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as session:
        graph, graph_path, graphify = await DsmGraphService(session).export_graph(
            version_id=args.version_id,
            persist=args.persist,
            send_to_graphify=args.send_to_graphify,
        )
        print(json.dumps({
            "version_id": graph.version_id,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "warnings": graph.warnings,
            "graph_path": str(graph_path) if graph_path else None,
            "graphify": graphify,
        }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export DSM derived knowledge graph")
    parser.add_argument("--version-id", default="active")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--send-to-graphify", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
