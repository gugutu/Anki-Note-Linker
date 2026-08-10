from typing import Optional

import pytest

from anki_note_linker.core.bridge import BridgeAction, parse_bridge_command


@pytest.mark.parametrize(
    ("message", "action", "payload"),
    [
        ("AnkiNoteLinker-setNoteToEditor1234567890123", BridgeAction.SET_NOTE_TO_EDITOR, "1234567890123"),
        ("AnkiNoteLinker-openNoteInBrowser1234567890123", BridgeAction.OPEN_NOTE_IN_BROWSER, "1234567890123"),
        ("AnkiNoteLinker-openNoteInNewEditor1234567890123", BridgeAction.OPEN_NOTE_IN_EDITOR, "1234567890123"),
        ("AnkiNoteLinker-openNoteInPreviewer1234567890123", BridgeAction.OPEN_NOTE_IN_PREVIEWER, "1234567890123"),
        ("AnkiNoteLinker-openAddNoteWindow12345678", BridgeAction.OPEN_ADD_NOTE_WINDOW, "12345678"),
        ("AnkiNoteLinker-tagSearchnested::tag", BridgeAction.SEARCH_TAG, "nested::tag"),
        ("AnkiNoteLinker-switchToOldRenderer", BridgeAction.SWITCH_TO_LEGACY_RENDERER, None),
    ],
)
def test_parses_supported_commands(message: str, action: BridgeAction, payload: Optional[str]) -> None:
    command = parse_bridge_command(message)

    assert command is not None
    assert command.action is action
    assert command.payload == payload


@pytest.mark.parametrize(
    "message",
    [
        "",
        "AnkiNoteLinker-openNoteInBrowser123",
        "AnkiNoteLinker-openAddNoteWindowabcdefgh",
        "AnkiNoteLinker-tagSearch",
        "AnkiNoteLinker-unknown1234567890123",
    ],
)
def test_rejects_invalid_commands(message: str) -> None:
    assert parse_bridge_command(message) is None


def test_exposes_note_id_only_for_note_commands() -> None:
    note_command = parse_bridge_command("AnkiNoteLinker-openNoteInBrowser1234567890123")
    new_note_command = parse_bridge_command("AnkiNoteLinker-openAddNoteWindow12345678")

    assert note_command is not None and note_command.note_id == 1234567890123
    assert new_note_command is not None and new_note_command.note_id is None
