"""Validate DSM release files and emit JSON/Markdown reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.dsm_ingestion import DsmIngestionService  # noqa: E402


def resolve_paths(release_path: str | None, final_json: str | None, registry: str | None) -> tuple[Path | None, Path, Path, dict]:
    manifest: dict = {}
    release_dir: Path | None = None
    if release_path:
        release_dir = Path(release_path).resolve()
        manifest_path = release_dir / "manifest.json"
        if not manifest_path.exists():
            raise SystemExit(f"manifest.json not found in {release_dir}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths = manifest.get("paths", {})
        final_json = str(release_dir / str(paths.get("final_json", "final_json")))
        registry = str(release_dir / Path(str(paths.get("minimal_registry", "normalized_registry/minimal_all.json"))).parent)
    if not final_json or not registry:
        raise SystemExit("Provide --release-path or both --final-json and --registry")
    return release_dir, Path(final_json), Path(registry), manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate DSM operational release files")
    parser.add_argument("--release-path", help="Release directory containing manifest.json")
    parser.add_argument("--final-json")
    parser.add_argument("--registry")
    parser.add_argument("--report-json", default="validation_report.json")
    parser.add_argument("--report-md", default="validation_report.md")
    args = parser.parse_args()
    service = DsmIngestionService(session=None)
    release_dir, final_json_path, registry_path, manifest = resolve_paths(args.release_path, args.final_json, args.registry)
    docs = service.load_final_json(final_json_path)
    minimal = service.load_registry_file(registry_path / "minimal_all.json", "MINIMAL")
    excluded = service.load_registry_file(registry_path / "excluded_all.json", "EXCLUDE")
    report = service.validate_release_payload(docs, minimal, excluded, manifest=manifest, release_path=release_dir)

    Path(args.report_json).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_md).write_text(report.to_markdown(), encoding="utf-8")

    print(f"Documents: {report.counts['renderable']}")
    print(f"Minimal: {report.counts['minimal']}")
    print(f"Excluded: {report.counts['exclude']}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Errors: {len(report.errors)}")
    print(f"Report JSON: {args.report_json}")
    print(f"Report Markdown: {args.report_md}")
    for error in report.errors:
        print(f"ERROR: {error}")
    raise SystemExit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
