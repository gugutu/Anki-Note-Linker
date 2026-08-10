import json
import zipfile
from pathlib import Path

import pytest

from scripts.build_addon import (
    ADDON_PACKAGE_ID,
    REQUIRED_ADDON_FILES,
    REQUIRED_FRONTEND_FILES,
    build_archive,
    create_manifest,
    validate_archive,
    validate_project,
)


def test_manifest_contains_stable_package_identifier() -> None:
    assert json.loads(create_manifest("v.test")) == {
        "package": ADDON_PACKAGE_ID,
        "name": "Anki Note Linker v.test",
    }
    assert ADDON_PACKAGE_ID == "1077002392"


def test_builds_deterministic_allowlisted_archive(tmp_path: Path) -> None:
    project = tmp_path / "project"
    addon_source = project / "src" / "addon"
    (project / "tests").mkdir(parents=True)
    (project / "LICENSE").write_text("license\n", encoding="utf-8")
    for relative_name in REQUIRED_ADDON_FILES:
        path = addon_source / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source {relative_name}\n", encoding="utf-8")
    (addon_source / "anki_note_linker" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (addon_source / "web" / "app.js").write_text("export {};\n", encoding="utf-8")
    (project / "tests" / "test_runtime.py").write_text("assert False\n", encoding="utf-8")
    (project / "frontend" / "package.json").parent.mkdir()
    (project / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    for relative_name in REQUIRED_FRONTEND_FILES:
        path = addon_source / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"generated {relative_name}\n", encoding="utf-8")

    first = build_archive(tmp_path / "first.ankiaddon", "v.test", project)
    second = build_archive(tmp_path / "second.ankiaddon", "v.test", project)

    assert first.read_bytes() == second.read_bytes()
    validate_archive(first)
    with zipfile.ZipFile(first) as archive:
        assert "meta.json" not in archive.namelist()
        assert archive.namelist() == [
            "manifest.json",
            *sorted(
                [
                    "LICENSE",
                    *REQUIRED_ADDON_FILES,
                    "anki_note_linker/core.py",
                    "web/app.js",
                    *REQUIRED_FRONTEND_FILES,
                ]
            ),
        ]


def test_requires_frontend_build(tmp_path: Path) -> None:
    project = tmp_path / "project"
    addon_source = project / "src" / "addon"
    (project / "LICENSE").parent.mkdir(parents=True)
    (project / "LICENSE").write_text("license\n", encoding="utf-8")
    for relative_name in REQUIRED_ADDON_FILES:
        path = addon_source / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source\n", encoding="utf-8")

    with pytest.raises(ValueError, match="npm --prefix frontend ci"):
        validate_project(project)


def test_requires_complete_addon_source(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("license\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Add-on source is missing"):
        validate_project(tmp_path)


def test_rejects_nested_package_directories(tmp_path: Path) -> None:
    archive_path = tmp_path / "invalid.ankiaddon"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name in sorted({"LICENSE", "manifest.json", *REQUIRED_ADDON_FILES, *REQUIRED_FRONTEND_FILES}):
            archive.writestr(name, "")
        archive.writestr("package/config.json", "{}")

    with pytest.raises(ValueError, match="development files"):
        validate_archive(archive_path)
