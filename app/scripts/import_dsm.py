"""CLI for importing a DSM release."""

import argparse
import asyncio
import json
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.schemas.ingestion import DsmImportRequest
from app.services.dsm_ingestion import DsmIngestionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized DSM JSON into PostgreSQL")
    parser.add_argument("--release-path", help="Release directory containing manifest.json")
    parser.add_argument("--final-json")
    parser.add_argument("--registry")
    parser.add_argument("--version-id")
    parser.add_argument("--label")
    parser.add_argument("--source-package")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--generate-embeddings", action="store_true")
    return parser.parse_args()


def resolve_release_args(args: argparse.Namespace) -> tuple[str, str, str, str, str | None]:
    final_json = args.final_json
    registry = args.registry
    version_id = args.version_id
    label = args.label
    source_package = args.source_package
    if args.release_path:
        release_dir = Path(args.release_path)
        manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
        paths = manifest.get("paths", {})
        final_json = str(release_dir / str(paths.get("final_json", "final_json")))
        registry = str(
            release_dir
            / Path(
                str(paths.get("minimal_registry", "normalized_registry/minimal_all.json"))
            ).parent
        )
        version_id = version_id or manifest.get("version_id")
        label = label or manifest.get("label")
        source_package = source_package or manifest.get("source_package")
    missing = [
        name
        for name, value in {
            "final_json": final_json,
            "registry": registry,
            "version_id": version_id,
            "label": label,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required arguments: {', '.join(missing)}")
    return str(final_json), str(registry), str(version_id), str(label), source_package


async def main() -> None:
    args = parse_args()
    final_json, registry, version_id, label, source_package = resolve_release_args(args)
    request = DsmImportRequest(
        final_json_path=final_json,
        registry_path=registry,
        version_id=version_id,
        label=label,
        source_package=source_package,
        activate=args.activate,
        generate_embeddings=args.generate_embeddings,
    )
    async with AsyncSessionLocal() as session:
        result = await DsmIngestionService(session).import_release(request)
    print(f"Version: {result.version_id}")
    print(f"Documents imported: {result.documents_imported}")
    print(f"Registry minimal: {result.registry_minimal}")
    print(f"Registry excluded: {result.registry_excluded}")
    print(f"Chunks generated: {result.chunks_generated}")
    print(f"Embeddings generated: {result.embeddings_generated}")
    print(f"Errors: {len(result.errors)}")
    print(f"Status: {result.status}")
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}")


if __name__ == "__main__":
    asyncio.run(main())
