"""Shared runtime paths, graph value objects, and preview state."""

from pathlib import Path
from typing import Optional

import anki
from anki.notes import NoteId
from aqt import gui_hooks, mw
from aqt.browser.previewer import BrowserPreviewer

from .lifecycle import remove_hook_safely


def log(*args):
    debug = 0
    if debug:
        print(*args)


mw.addonManager.setWebExports(__name__, "web/.*")
_ADDON_ROOT = Path(__file__).resolve().parents[2]
addon_path = str(_ADDON_ROOT)
addon_folder = _ADDON_ROOT.name
links_html = (_ADDON_ROOT / "web" / "links.html").read_text(encoding="utf-8")
graph_html = (_ADDON_ROOT / "web" / "graph.html").read_text(encoding="utf-8")
newGraph_html = (_ADDON_ROOT / "web" / "newGraph.html").read_text(encoding="utf-8")
config_html = (_ADDON_ROOT / "web" / "config.html").read_text(encoding="utf-8")


def getWebFileLink(fileName: str):
    return f"http://127.0.0.1:{mw.mediaServer.getPort()}/_addons/{addon_folder}/web/{fileName}"


globalGraph = None
addon = None


class Connection:
    def __init__(self, source_id, target_id):
        self.source = source_id
        self.target = target_id


class NoteNode:
    def __init__(
        self, nid: NoteId, childIds: list[NoteId], parentIds: set[NoteId], mainField: str, isTag: bool = False
    ):
        self.id = nid
        self.childIds: list[NoteId] = childIds
        self.parentIds: set[NoteId] = parentIds
        self.mainField: str = mainField
        self.isTag: bool = isTag

    def toJsNoteNode(self, type):
        return JsNoteNode(self.id, self.mainField, "tag" if self.isTag else type)


class JsNoteNode:
    def __init__(self, nid: int, mainField: str, type: str, linkTitle: Optional[str] = None):
        self.id = nid
        self.mainField = mainField
        self.type = type
        self.linkTitle = linkTitle


class PreviewState:
    def __init__(self, cards):
        self.previewer: Optional[BrowserPreviewer] = None
        self.cards = cards
        self.index = 0
        self.card = cards[self.index]
        self.singleCard = True
        gui_hooks.operation_did_execute.append(self.onOp)

    def onOp(self, changes: anki.collection.OpChanges, handler):
        if (changes.note_text or changes.card) and self.previewer:
            try:
                self.previewer.render_card()
            except anki.errors.NotFoundError:
                self.previewer.close()

    def onNextCard(self):
        if self.has_next_card() and self.previewer is not None:
            self.index += 1
            try:
                self.card = self.cards[self.index]
                self.previewer.render_card()
            except anki.errors.NotFoundError:
                self.index -= 1
                self.card = self.cards[self.index]
            except IndexError:
                self.index -= 1

    def onPreviousCard(self):
        if self.has_previous_card() and self.previewer is not None:
            self.index -= 1
            try:
                self.card = self.cards[self.index]
                self.previewer.render_card()
            except anki.errors.NotFoundError:
                self.index += 1
                self.card = self.cards[self.index]
            except IndexError:
                self.index += 1

    def has_previous_card(self):
        return self.index > 0

    def has_next_card(self):
        return self.index < len(self.cards) - 1

    def setPreviewer(self, previewer):
        self.previewer = previewer

    def cleanUpState(self):
        remove_hook_safely(gui_hooks.operation_did_execute, self.onOp)
        self.previewer = None
