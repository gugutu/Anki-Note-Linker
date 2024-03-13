"""
AGPL3 LICENSE
Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Creator Wang Rui <https://github.com/gugutu>
"""
import os

import anki
from aqt.browser.previewer import BrowserPreviewer

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
except ImportError:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from aqt import mw
from aqt.utils import restoreGeom, saveGeom, tooltip
from aqt.webview import AnkiWebView

from .translation import getTr


def log(*args):
    debug = 0
    if debug:
        print(*args)


config = mw.addonManager.getConfig(__name__)
addon_path = os.path.dirname(__file__)
links_html = open(os.path.join(addon_path, 'links.html'), 'r', encoding='utf-8').read()
graph_html = open(os.path.join(addon_path, 'graph.html'), 'r', encoding='utf-8').read()
globalGraph_html = open(os.path.join(addon_path, 'globalGraph.html'), 'r', encoding='utf-8').read()
translation_js = open(os.path.join(addon_path, 'translation.js'), 'r', encoding='utf-8').read()
force_graph_js = open(os.path.join(addon_path, 'force-graph.js'), 'r', encoding='utf-8').read()
d3_js = open(os.path.join(addon_path, 'd3.js'), 'r', encoding='utf-8').read()
linkMaxLines = str(config['linkMaxLines'])
globalGraph = None


class Connection:
    def __init__(self, source_id, target_id):
        self.source = source_id
        self.target = target_id


class NoteNode:
    def __init__(self, nid: int, childIds: list[int], parentIds: list[int], mainField: str):
        self.id = nid
        self.childIds: list[int] = childIds
        self.parentIds: list[int] = parentIds
        self.mainField: str = mainField

    def toJsNoteNode(self, type):
        return JsNoteNode(self.id, self.mainField, type)


class JsNoteNode:
    def __init__(self, nid: int, mainField: str, type: str):
        self.id = nid
        self.mainField = mainField
        self.type = type


class GlobalGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(getTr("Global Relationship Graph (Experimental)"))
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        restoreGeom(self, "GlobalGraph", default_size=(1000, 600))
        self.web = AnkiWebView(self, title="GlobalGraph")
        # self.web.stdHtml(
        #     f'<script>\n{d3_js}{translation_js}\n const ankiLanguage = "{anki.lang.current_lang}";</script>' +
        #     globalGraph_html
        # )
        self.web.stdHtml(
            f'<script>\n{d3_js}{force_graph_js}{translation_js}\n const ankiLanguage = "{anki.lang.current_lang}";</script>' +
            graph_html
        )
        self.web.set_bridge_command(lambda s: s, self)
        self.layout.addWidget(self.web)
        self.activateWindow()
        self.show()

    def closeEvent(self, event):
        saveGeom(self, "GlobalGraph")
        global globalGraph
        globalGraph = None
        event.accept()


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
