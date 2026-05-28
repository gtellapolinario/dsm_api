"""CLI for importing a DSM release."""
import argparse
import asyncio

from app.core.database import AsyncSessionLocal
from app.schemas.ingestion import DsmImportRequest
from app.services.dsm_ingestion import DsmIngestionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized DSM JSON into PostgreSQL")
    parser.add_argument("--final-json", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--version-id", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--source-package")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--generate-embeddings", action="store_true")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    request = DsmImportRequest(
        final_json_path=args.final_json, registry_path=args.registry, version_id=args.version_id, label=args.label,
        source_package=args.source_package, activate=args.activate, generate_embeddings=args.generate_embeddings,
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
