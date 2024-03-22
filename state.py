"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import json
import os

import anki
from aqt.browser.previewer import BrowserPreviewer
from aqt.operations import QueryOp

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QHBoxLayout, QRadioButton
except ImportError:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QHBoxLayout, QRadioButton
from aqt import mw, qconnect
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
# globalGraph_html = open(os.path.join(addon_path, 'globalGraph.html'), 'r', encoding='utf-8').read()
translation_js = open(os.path.join(addon_path, 'translation.js'), 'r', encoding='utf-8').read()
force_graph_js = open(os.path.join(addon_path, 'force-graph.js'), 'r', encoding='utf-8').read()
d3_js = open(os.path.join(addon_path, 'd3.js'), 'r', encoding='utf-8').read()
linkMaxLines = str(config['linkMaxLines'])
globalGraph = None
addon = None


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
        self.linkCache = []
        self.noteCache = []
        self.setWindowTitle(getTr("Global Relationship Graph (Experimental)"))
        outerLayout = QVBoxLayout()
        topBarLayout = QHBoxLayout()
        topBarLayout.setContentsMargins(10, 5, 10, 0)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outerLayout)
        self.topBar = QWidget(self)
        self.topBar.setLayout(topBarLayout)
        self.topBar.setFixedHeight(30)
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
        outerLayout.addWidget(self.topBar)
        outerLayout.addWidget(self.web)
        self.lineEdit = QLineEdit()
        self.lineEdit.setText('deck:current')
        self.rButton = QRadioButton(getTr('Including single notes'), self)
        self.sButton = QPushButton(getTr('Search'))
        qconnect(self.sButton.clicked, self.refreshGlobalGraph)
        topBarLayout.addWidget(QLabel(getTr('Search notes:')))
        topBarLayout.addWidget(self.lineEdit)
        topBarLayout.addWidget(self.rButton)
        topBarLayout.addWidget(self.sButton)

        self.activateWindow()
        self.show()

    def refreshGlobalGraph(self):
        def op(col):
            ids = set(col.find_notes(self.lineEdit.text()))
            showSingle = self.rButton.isChecked()
            self.noteCache = [x.toJsNoteNode('child') for x in addon.noteCache.values()
                              if (x.id in ids and showSingle) or
                              (x.id in ids and (len(x.childIds) != 0 or len(x.parentIds) != 0))]

            self.linkCache = [x for x in addon.linkCache if x.source in ids and x.target in ids]

        QueryOp(parent=self, op=op, success=lambda c: self.web.eval(
            f'''reloadPage(
                {json.dumps(self.noteCache, default=lambda o: o.__dict__)},
                {json.dumps(self.linkCache, default=lambda o: o.__dict__)},
                false
            )'''
        )).run_in_background()

    def closeEvent(self, event):
        saveGeom(self, "GlobalGraph")
        self.web.cleanup()
        self.web.close()
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
