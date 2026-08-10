"""Dispatch validated WebView commands to Anki services."""

from typing import Any

import aqt
from anki import notetypes_pb2
from anki.notes import NoteId
from aqt import mw
from aqt.browser import Browser
from aqt.editor import Editor
from aqt.utils import tooltip

from ..core.bridge import BridgeAction, parse_bridge_command
from ..core.links import find_new_link_title
from .editor_windows import MyAddCards
from .i18n import getTr

try:
    from anki.models import StockNotetype
except ImportError:
    StockNotetype = None


class BridgeMixin:
    def handlePycmd(self, handled: tuple[bool, Any], message: str, context: Any):
        """Handle commands received from add-on WebViews."""

        def validateNid(nid):
            if len(aqt.mw.col.find_notes(f"nid:{nid}")) == 0:
                tooltip(getTr("The corresponding note does not exist"))
                return False
            return True

        command = parse_bridge_command(message)
        if command is None:
            return handled

        if command.note_id is not None:
            nid = command.note_id
            if not validateNid(nid):
                return True, None
            if command.action is BridgeAction.SET_NOTE_TO_EDITOR:
                editor: Editor = context
                editor.set_note(aqt.mw.col.get_note(NoteId(nid)), focusTo=0)
            elif command.action is BridgeAction.OPEN_NOTE_IN_BROWSER:
                self.openNoteInBrowser(context, nid)
            elif command.action is BridgeAction.OPEN_NOTE_IN_EDITOR:
                self.openNoteInNewEditor(context, nid)
            elif command.action is BridgeAction.OPEN_NOTE_IN_PREVIEWER:
                self.openNoteInPreviewer(context, nid)
            return True, None

        if command.action is BridgeAction.OPEN_ADD_NOTE_WINDOW:
            placeholder = command.payload
            if placeholder is None:
                return handled
            editor: Editor = context
            if editor.addMode:
                tooltip(getTr("Please add the current note first"))
                return True, None
            text = find_new_link_title(editor.note.joined_fields(), placeholder) or ""
            note = aqt.mw.col.new_note(editor.note.note_type())
            if (
                StockNotetype is not None
                and note.note_type().get("originalStockKind")
                == StockNotetype.OriginalStockKind.ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION
            ):
                for flds in note.note_type()["flds"]:
                    if flds["tag"] == notetypes_pb2.IMAGE_OCCLUSION_FIELD_HEADER:
                        note.fields[flds["ord"]] = text
                        break
            else:
                note.fields[0] = text
            add = MyAddCards(editor.note, placeholder)
            add.set_note(note, editor.note.cards()[0].did)
            return True, None

        if command.action is BridgeAction.SEARCH_TAG:
            tag = command.payload
            if tag is None:
                return handled
            browser: Browser = aqt.dialogs.open("Browser", aqt.mw)
            browser.activateWindow()
            browser.search_for("tag:" + tag)
            return True, None

        if command.action is BridgeAction.SWITCH_TO_LEGACY_RENDERER:
            if isinstance(context, Editor):
                self.switchToOldRenderer(context)
            elif hasattr(mw.reviewer, "graphPage") and context == mw.reviewer.graphPage:
                self.switchReviewerGraphToOldRenderer()
            elif hasattr(context, "switchToOldRenderer"):
                context.switchToOldRenderer()
            return True, None
        return handled
