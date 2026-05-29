"""Optional Graphify CLI adapter.

Graphify is intentionally not imported as a Python dependency. The canonical DSM
source remains PostgreSQL; this adapter only attempts an optional CLI ingest of a
local JSON export.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path


class GraphifyAdapter:
    def __init__(self, enabled: bool, cli_path: str | None):
        self.enabled = enabled
        self.cli_path = cli_path or None

    async def is_available(self) -> bool:
        if not self.enabled or not self.cli_path:
            return False
        return shutil.which(self.cli_path) is not None or Path(self.cli_path).exists()

    async def ingest_graph(self, graph_path: Path, version_id: str) -> dict:
        if not self.enabled or not self.cli_path:
            return {
                "enabled": False,
                "available": False,
                "message": "Graphify CLI not configured. Local graph export generated only.",
            }
        if not await self.is_available():
            return {
                "enabled": True,
                "available": False,
                "message": f"Graphify CLI not available at {self.cli_path}. Local graph export generated only.",
            }
        try:
            proc = await asyncio.create_subprocess_exec(
                self.cli_path,
                "ingest",
                "--input",
                str(graph_path),
                "--version-id",
                version_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return {
                "enabled": True,
                "available": True,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors="replace")[-4000:],
                "stderr": stderr.decode(errors="replace")[-4000:],
                "message": "Graphify CLI completed" if proc.returncode == 0 else "Graphify CLI failed; local export is still available.",
            }
        except Exception as exc:  # noqa: BLE001 - adapter must never break the API
            return {
                "enabled": True,
                "available": False,
                "message": f"Graphify ingest failed; local export is still available: {exc}",
            }
