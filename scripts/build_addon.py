"""Build a deterministic Anki add-on archive from the add-on source tree."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Iterator, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_SOURCE = Path("src/addon")
ARCHIVE_TIMESTAMP = (2020, 1, 1, 0, 0, 0)
IGNORED_PARTS = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_ADDON_FILES = (
    "__init__.py",
    "config.json",
    "config.md",
    "anki_note_linker/__init__.py",
    "anki_note_linker/runtime/controller.py",
    "icons/showGraphPage.svg",
    "icons/showLinksPage.svg",
    "web/config.html",
    "web/graph.html",
    "web/links.html",
    "web/newGraph.html",
    "web/js/detectClick.js",
    "web/js/translation.js",
)
REQUIRED_FRONTEND_FILES = (
    "web/dist/config.js",
    "web/dist/graph-core.js",
    "web/dist/links.js",
    "web/dist/new-graph.js",
    "web/dist/vendor/d3.js",
    "web/dist/vendor/force-graph.js",
    "web/dist/vendor/katex.css",
    "web/dist/vendor/katex.js",
    "web/dist/vendor/pixi.js",
    "web/dist/vendor/fonts/KaTeX_Main-Regular.woff2",
)


def _is_packaged_file(path: Path) -> bool:
    return not any(part in IGNORED_PARTS for part in path.parts) and path.suffix not in IGNORED_SUFFIXES


def iter_source_files(project_root: Path = PROJECT_ROOT) -> Iterator[Tuple[Path, Path]]:
    """Yield source paths and archive paths in deterministic order."""
    addon_source = project_root / ADDON_SOURCE
    candidates = [(project_root / "LICENSE", Path("LICENSE"))]
    for source in addon_source.rglob("*"):
        if source.is_file() and _is_packaged_file(source):
            candidates.append((source, source.relative_to(addon_source)))

    yield from sorted(candidates, key=lambda item: item[1].as_posix())


def create_manifest(version_label: str) -> bytes:
    manifest = {
        "package": "Anki_Note_Linker",
        "name": f"Anki Note Linker {version_label}",
    }
    return (json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def validate_project(project_root: Path = PROJECT_ROOT) -> None:
    """Require the complete add-on tree and generated browser assets."""
    addon_source = project_root / ADDON_SOURCE
    if not (project_root / "LICENSE").is_file():
        raise ValueError("Project LICENSE is missing")

    missing_addon_files = [
        relative_name for relative_name in REQUIRED_ADDON_FILES if not (addon_source / relative_name).is_file()
    ]
    if missing_addon_files:
        raise ValueError(f"Add-on source is missing: {', '.join(missing_addon_files)}")

    missing = [
        relative_name for relative_name in REQUIRED_FRONTEND_FILES if not (addon_source / relative_name).is_file()
    ]
    if missing:
        raise ValueError(
            f"Frontend build is missing: {', '.join(missing)}. "
            "Run `npm --prefix frontend ci && npm --prefix frontend run build` first."
        )


def _write_bytes(archive: zipfile.ZipFile, archive_path: str, content: bytes) -> None:
    info = zipfile.ZipInfo(archive_path, ARCHIVE_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, content)


def build_archive(output: Path, version_label: str, project_root: Path = PROJECT_ROOT) -> Path:
    """Create an add-on archive and return its path."""
    validate_project(project_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        _write_bytes(archive, "manifest.json", create_manifest(version_label))
        for source, archive_path in iter_source_files(project_root):
            _write_bytes(archive, archive_path.as_posix(), source.read_bytes())
    return output


def validate_archive(archive_path: Path) -> None:
    """Reject archives containing development files or nested build directories."""
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
    required_names = {"LICENSE", "manifest.json", *REQUIRED_ADDON_FILES, *REQUIRED_FRONTEND_FILES}
    missing = sorted(required_names.difference(names))
    if missing:
        raise ValueError(f"Archive is missing required add-on files: {', '.join(missing)}")
    invalid_prefixes = (".github/", "frontend/", "node_modules/", "package/", "scripts/", "src/", "tests/")
    invalid = [
        name
        for name in names
        if name.startswith(invalid_prefixes) or "/__pycache__/" in name or name.endswith(tuple(IGNORED_SUFFIXES))
    ]
    if invalid:
        raise ValueError(f"Archive contains development files: {', '.join(invalid)}")
    if names != ["manifest.json", *sorted(name for name in names if name != "manifest.json")]:
        raise ValueError("Archive entries are not in deterministic order")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release label stored in manifest.json")
    parser.add_argument("--output", type=Path, help="Output .ankiaddon path")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", args.version)
    output = args.output or PROJECT_ROOT / "dist" / f"{safe_name}.ankiaddon"
    archive = build_archive(output.resolve(), args.version)
    validate_archive(archive)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
