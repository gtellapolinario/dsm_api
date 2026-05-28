"""Validate DSM JSON files without importing them."""

import argparse
import json
from pathlib import Path

from app.services.dsm_ingestion import DsmIngestionService


def resolve_paths(
    release_path: str | None, final_json: str | None, registry: str | None
) -> tuple[Path, Path]:
    if release_path:
        release_dir = Path(release_path)
        manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
        paths = manifest.get("paths", {})
        final_json = str(release_dir / str(paths.get("final_json", "final_json")))
        registry = str(
            release_dir
            / Path(
                str(paths.get("minimal_registry", "normalized_registry/minimal_all.json"))
            ).parent
        )
    if not final_json or not registry:
        raise SystemExit("Provide --release-path or both --final-json and --registry")
    return Path(final_json), Path(registry)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-path", help="Release directory containing manifest.json")
    parser.add_argument("--final-json")
    parser.add_argument("--registry")
    args = parser.parse_args()
    service = DsmIngestionService(session=None)  # type: ignore[arg-type]
    final_json_path, registry_path = resolve_paths(
        args.release_path, args.final_json, args.registry
    )
    docs = service.load_final_json(final_json_path)
    minimal = service.load_registry_file(registry_path / "minimal_all.json", "MINIMAL")
    excluded = service.load_registry_file(registry_path / "excluded_all.json", "EXCLUDE")
    errors, warnings = service.validate_all(docs, minimal + excluded)
    print(f"Documents: {len(docs)}")
    print(f"Minimal: {len(minimal)}")
    print(f"Excluded: {len(excluded)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
