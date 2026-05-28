"""Validate DSM JSON files without importing them."""
import argparse

from app.services.dsm_ingestion import DsmIngestionService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-json", required=True)
    parser.add_argument("--registry", required=True)
    args = parser.parse_args()
    service = DsmIngestionService(session=None)  # type: ignore[arg-type]
    docs = service.load_final_json(__import__("pathlib").Path(args.final_json))
    minimal = service.load_registry_file(__import__("pathlib").Path(args.registry) / "minimal_all.json", "MINIMAL")
    excluded = service.load_registry_file(__import__("pathlib").Path(args.registry) / "excluded_all.json", "EXCLUDE")
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
