"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import os

import anki
from anki.notes import NoteId
from aqt.browser.previewer import BrowserPreviewer
from aqt.utils import tooltip

from .translation import getTr


def log(*args):
    debug = 0
    if debug:
        print(*args)


addon_path = os.path.dirname(__file__)
links_html = open(os.path.join(addon_path, 'links.html'), 'r', encoding='utf-8').read()
graph_html = open(os.path.join(addon_path, 'graph.html'), 'r', encoding='utf-8').read()
# globalGraph_html = open(os.path.join(addon_path, 'globalGraph.html'), 'r', encoding='utf-8').read()
translation_js = open(os.path.join(addon_path, 'translation.js'), 'r', encoding='utf-8').read()
force_graph_js = open(os.path.join(addon_path, 'force-graph.js'), 'r', encoding='utf-8').read()
d3_js = open(os.path.join(addon_path, 'd3.js'), 'r', encoding='utf-8').read()
globalGraph = None
addon = None


class Connection:
    def __init__(self, source_id, target_id):
        self.source = source_id
        self.target = target_id


class NoteNode:
    def __init__(self, nid: NoteId, childIds: list[NoteId], parentIds: set[NoteId], mainField: str):
        self.id = nid
        self.childIds: list[NoteId] = childIds
        self.parentIds: set[NoteId] = parentIds
        self.mainField: str = mainField

    def toJsNoteNode(self, type):
        return JsNoteNode(self.id, self.mainField, type)


class JsNoteNode:
    def __init__(self, nid: int, mainField: str, type: str):
        self.id = nid
        self.mainField = mainField
        self.type = type


class PreviewState:
    def __init__(self, cards):
        self.previewer: None | BrowserPreviewer = None
        self.cards = cards
        self.index = 0
        self.card = cards[self.index]
        self.singleCard = True

    def onNextCard(self):
        if self.has_next_card() and self.previewer is not None:
            self.index += 1
            self.card = self.cards[self.index]
            try:
                self.previewer.render_card()
            except anki.errors.NotFoundError:
                self.index -= 1
                self.card = self.cards[self.index]
                tooltip(getTr('Current note has been deleted'))

    def onPreviousCard(self):
        if self.has_previous_card() and self.previewer is not None:
            self.index -= 1
            self.card = self.cards[self.index]
            try:
                self.previewer.render_card()
            except anki.errors.NotFoundError:
                self.index += 1
                self.card = self.cards[self.index]
                tooltip(getTr('Current note has been deleted'))

    def has_previous_card(self):
        return self.index > 0

    def has_next_card(self):
        return self.index < len(self.cards) - 1

    def setPreviewer(self, previewer):
        self.previewer = previewer
