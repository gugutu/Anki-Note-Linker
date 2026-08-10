from anki_note_linker.config.migration import migrate_config
from anki_note_linker.config.schema import default_config


def test_fills_missing_defaults_without_overwriting_existing_values() -> None:
    defaults = default_config(is_mac=True)

    migrated = migrate_config({"linkMaxLines": 12, "custom-key": "kept"}, defaults)

    assert migrated["linkMaxLines"] == 12
    assert migrated["custom-key"] == "kept"
    assert migrated["shortcuts-copyNoteID"] == "Ctrl+Alt+C"


def test_migrates_historical_nested_configuration() -> None:
    defaults = default_config(is_mac=False)
    migrated = migrate_config(
        {
            "shortcuts": {"copyNoteID": "Ctrl+C"},
            "globalGraph": {
                "defaultSearchText": "tag:test",
                "nodeColor": [1, 2, 3],
            },
            "Use the previewer of hjp-linkmaster if it is installed": False,
        },
        defaults,
    )

    assert "shortcuts" not in migrated
    assert "globalGraph" not in migrated
    assert migrated["shortcuts-copyNoteID"] == "Ctrl+C"
    assert migrated["shortcuts-copyNoteLink"] == "Alt+Shift+L"
    assert migrated["globalGraph-defaultSearchText"] == "tag:test"
    assert migrated["globalGraph-nodeColor"] == [1, 2, 3]
    assert migrated["globalGraph-defaultHighlightFilter"] == "is:due"
    assert migrated["useHjpPreviewer"] is False


def test_migration_does_not_mutate_input() -> None:
    raw = {"shortcuts": {"copyNoteID": "Ctrl+C"}}

    migrate_config(raw, default_config(is_mac=False))

    assert raw == {"shortcuts": {"copyNoteID": "Ctrl+C"}}
