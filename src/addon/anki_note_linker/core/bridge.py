"""Parse the stable string protocol used by Anki WebView bridge messages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class BridgeAction(str, Enum):
    SET_NOTE_TO_EDITOR = "set_note_to_editor"
    OPEN_NOTE_IN_BROWSER = "open_note_in_browser"
    OPEN_NOTE_IN_EDITOR = "open_note_in_editor"
    OPEN_NOTE_IN_PREVIEWER = "open_note_in_previewer"
    OPEN_ADD_NOTE_WINDOW = "open_add_note_window"
    SEARCH_TAG = "search_tag"
    SWITCH_TO_LEGACY_RENDERER = "switch_to_legacy_renderer"
    EDITOR_ACTION = "editor_action"


class EditorAction(str, Enum):
    INSERT_LINK_WITH_CLIPBOARD_ID = "insertLinkWithClipboardID"
    INSERT_NEW_LINK = "insertNewLink"
    INSERT_LINK_TEMPLATE = "insertLinkTemplate"
    COPY_NOTE_ID = "copyNoteID"
    COPY_NOTE_LINK = "copyNoteLink"
    OPEN_NOTE_IN_EDITOR = "openNoteInNewEditor"


@dataclass(frozen=True)
class BridgeCommand:
    action: BridgeAction
    payload: Optional[str] = None
    editor_action: Optional[EditorAction] = None
    selected_text: Optional[str] = None

    @property
    def note_id(self) -> Optional[int]:
        if self.payload is None or not self.payload.isdigit() or len(self.payload) != 13:
            return None
        return int(self.payload)


_NUMERIC_COMMANDS: Tuple[Tuple[str, BridgeAction, int], ...] = (
    ("AnkiNoteLinker-setNoteToEditor", BridgeAction.SET_NOTE_TO_EDITOR, 13),
    ("AnkiNoteLinker-openNoteInBrowser", BridgeAction.OPEN_NOTE_IN_BROWSER, 13),
    ("AnkiNoteLinker-openNoteInNewEditor", BridgeAction.OPEN_NOTE_IN_EDITOR, 13),
    ("AnkiNoteLinker-openNoteInPreviewer", BridgeAction.OPEN_NOTE_IN_PREVIEWER, 13),
    ("AnkiNoteLinker-openAddNoteWindow", BridgeAction.OPEN_ADD_NOTE_WINDOW, 8),
)


def parse_bridge_command(message: str) -> Optional[BridgeCommand]:
    editor_prefix = "AnkiNoteLinker-editorAction"
    if message.startswith(editor_prefix):
        try:
            data = json.loads(message[len(editor_prefix) :])
            if not isinstance(data, dict) or not isinstance(data.get("selectedText"), str):
                return None
            editor_action = EditorAction(data.get("action"))
        except (ValueError, TypeError):
            return None
        return BridgeCommand(
            BridgeAction.EDITOR_ACTION, editor_action=editor_action, selected_text=data["selectedText"]
        )

    if message == "AnkiNoteLinker-switchToOldRenderer":
        return BridgeCommand(BridgeAction.SWITCH_TO_LEGACY_RENDERER)

    tag_prefix = "AnkiNoteLinker-tagSearch"
    if message.startswith(tag_prefix):
        tag = message[len(tag_prefix) :]
        return BridgeCommand(BridgeAction.SEARCH_TAG, tag) if tag else None

    for prefix, action, payload_length in _NUMERIC_COMMANDS:
        if not message.startswith(prefix):
            continue
        payload = message[len(prefix) :]
        if re.fullmatch(rf"\d{{{payload_length}}}", payload):
            return BridgeCommand(action, payload)
        return None
    return None
