"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""

import json
from typing import Optional

from anki.collection import Collection, OpChanges
from anki.errors import SearchError
from anki.notes import Note, NoteId
from aqt import (
    QCheckBox,
    QColor,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    gui_hooks,
    qconnect,
)
from aqt.errors import show_exception
from aqt.operations import QueryOp
from aqt.utils import restoreGeom, saveGeom, tooltip
from aqt.webview import AnkiWebView

from ..core.graph import build_global_graph_note_search, build_global_graph_search
from . import state
from .configuration import config
from .i18n import getTr
from .lifecycle import cleanup_webview, enable_immediate_profile_close, remove_hook_safely
from .state import Connection, NoteNode, log
from .web_pages import legacy_graph_page, new_graph_page


class GlobalGraph(QWidget):
    def __init__(self):
        super().__init__()
        self._closed = False
        gui_hooks.operation_did_execute.append(self.onOpChange)
        gui_hooks.collection_did_load.append(self.refreshGlobalGraph)
        gui_hooks.editor_did_update_tags.append(self.onTagUpdate)
        self.noteCache: dict[int, NoteNode] = {}
        self.searchedIds: set[NoteId] = set()
        self.needRefreshAgain = False
        self.inRefreshProcess = False
        self.lastSearchState = None
        self.linkCache: list[Connection] = []
        self.noteCacheList = []
        self.hlIds = set()
        self.setWindowTitle(getTr("Global Relationship Graph"))
        outerLayout = QVBoxLayout()
        topBarLayout = QHBoxLayout()
        topBarLayout.setContentsMargins(10, 7, 10, 0)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outerLayout)
        self.topBar = QWidget(self)
        self.topBar.setLayout(topBarLayout)
        self.topBar.setFixedHeight(30)
        restoreGeom(self, "GlobalGraph", default_size=(1000, 600))
        self.web = AnkiWebView(self, title="GlobalGraph")
        self.web.stdHtml(new_graph_page("GLOBAL_GRAPH"))
        self.web.set_bridge_command(lambda s: s, self)
        outerLayout.addWidget(self.topBar)
        outerLayout.addWidget(self.web)
        self.lineEdit = QLineEdit()
        self.lineEdit.setText(config["globalGraph-defaultSearchText"])
        self.lineEdit2 = QLineEdit()
        self.lineEdit2.setText(config["globalGraph-defaultHighlightFilter"])
        self.showSingleNodesCheckBox = QCheckBox(getTr("Display single nodes"))
        self.showSingleNodesCheckBox.setChecked(config["globalGraph-defaultShowSingleNode"])
        self.showTagNodesCheckBox = QCheckBox(getTr("Display tag nodes"))
        self.showTagNodesCheckBox.setChecked(config["globalGraph-defaultShowTags"])
        self.showSuspendedNotesCheckBox = QCheckBox(getTr("Display suspended notes"))
        self.showSuspendedNotesCheckBox.setChecked(config["globalGraph-defaultShowSuspended"])
        self.showSuspendedNotesCheckBox.setToolTip(
            getTr("When this option is off, notes remain visible if at least one of their cards is not suspended.")
        )
        self.sButton = QPushButton(getTr("Search"))
        qconnect(
            self.sButton.clicked, lambda: self.refreshGlobalGraph(resetCenter=True, reason="Search Button Clicked")
        )
        topBarLayout.addWidget(QLabel(getTr("Search notes:")))
        topBarLayout.addWidget(self.lineEdit)
        topBarLayout.addWidget(QLabel(getTr("Highlight specified notes:")))
        topBarLayout.addWidget(self.lineEdit2)
        topBarLayout.addWidget(self.showSingleNodesCheckBox)
        topBarLayout.addWidget(self.showTagNodesCheckBox)
        topBarLayout.addWidget(self.showSuspendedNotesCheckBox)
        topBarLayout.addWidget(self.sButton)

        enable_immediate_profile_close(self)
        self.activateWindow()
        self.show()
        self.refreshGlobalGraph(adaptScale=True, reason="Init Global Graph")

    def switchToOldRenderer(self):
        if self._closed or self.web is None:
            return
        self.web.stdHtml(legacy_graph_page("GLOBAL_GRAPH"))
        self.refreshGlobalGraph(adaptScale=True, reason="Switch To Old Renderer")
        tooltip(
            getTr(
                'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.'
            ),
            10000,
        )

    def onOpChange(self, changes: OpChanges, handler: Optional[object]):
        if not self._closed and (changes.study_queues or changes.notetype):
            self.refreshGlobalGraph(reason="onOpChange")

    def onTagUpdate(self, note: Note):
        if not self._closed and self.showTagNodesCheckBox.isChecked():
            self.refreshGlobalGraph(reason="tag of note changed", changedTagNote=note)

    def rebuildCache(
        self,
        col: Collection,
        searchText: str,
        highlightText: str,
        showTags: bool,
        showSuspended: bool,
        keepTagNote: Note = None,
    ):
        self.noteCache = {}
        self.searchedIds = set(col.find_notes(build_global_graph_search(searchText, showSuspended)))

        if highlightText == "":
            self.hlIds = set()
        else:
            self.hlIds = set(col.find_notes(highlightText))
        for noteId in self.searchedIds:
            note = col.get_note(noteId)
            self.updateNodeCache(note, keepTagNote, showTags)

    def updateNodeCache(self, note: Note, keepTagNote: Note = None, showTags: bool = False):
        """Update one note and the related forward and reverse link cache entries."""
        if self._closed or self.needRefreshAgain:
            raise Exception("-----Interrupted Refresh Global Graph Process")
        noteId = note.id
        childIds = state.addon.findChildIds(noteId, " ".join(note.fields), rangeIdSet=self.searchedIds)
        mainField = state.addon.getMainField(note)
        node = self.noteCache.get(noteId)
        if node is not None:
            oldChildIds = node.childIds
            node.mainField = mainField
            node.childIds = childIds
            for child_id in oldChildIds:
                if child_id in self.noteCache:
                    self.noteCache[child_id].parentIds.discard(noteId)
        else:
            node = self.noteCache[noteId] = NoteNode(noteId, childIds, set(), mainField)

        if showTags:
            for tag in keepTagNote.tags if keepTagNote is not None and keepTagNote.id == note.id else note.tags:
                if tag == "":
                    continue

                if tag in self.noteCache:
                    self.noteCache[tag].childIds.append(noteId)
                else:
                    self.noteCache[tag] = NoteNode(tag, [noteId], set(), tag, isTag=True)

                node.parentIds.add(tag)

        for childId in childIds:
            if childId in self.noteCache:
                childNode = self.noteCache[childId]
                if noteId not in childNode.parentIds:
                    childNode.parentIds.add(noteId)
            else:
                self.noteCache[childId] = NoteNode(childId, [], {noteId}, None)

    def refreshGlobalGraph(
        self,
        onlyChangedNote: Note = None,
        reason: str = "",
        adaptScale=False,
        resetCenter=False,
        changedTagNote: Note = None,
    ):
        if self._closed:
            return
        if isinstance(onlyChangedNote, Collection):
            onlyChangedNote = None
            reason = "collection_did_load"
        if self.inRefreshProcess:
            self.needRefreshAgain = True
            return

        self.inRefreshProcess = True
        searchText = self.lineEdit.text()
        highlightText = self.lineEdit2.text()
        showSingle = self.showSingleNodesCheckBox.isChecked()
        showTags = self.showTagNodesCheckBox.isChecked()
        showSuspended = self.showSuspendedNotesCheckBox.isChecked()
        searchState = (searchText, highlightText, showTags, showSuspended)

        def op(col):
            if onlyChangedNote is not None and searchState == self.lastSearchState:
                log("-----Refresh Global Graph With Update Single Node: ", reason)
                matches_search = bool(
                    col.find_notes(build_global_graph_note_search(onlyChangedNote.id, searchText, showSuspended))
                )
                was_searched = onlyChangedNote.id in self.searchedIds
                if matches_search != was_searched:
                    self.rebuildCache(
                        col,
                        searchText,
                        highlightText,
                        showTags,
                        showSuspended,
                        keepTagNote=changedTagNote,
                    )
                elif matches_search:
                    self.updateNodeCache(onlyChangedNote, showTags=showTags)
            else:
                log("-----Refresh Global Graph With Rebuild Cache: ", reason)
                self.rebuildCache(
                    col,
                    searchText,
                    highlightText,
                    showTags,
                    showSuspended,
                    keepTagNote=changedTagNote,
                )

            self.noteCacheList = [
                x for x in self.noteCache.values() if showSingle or len(x.childIds) != 0 or len(x.parentIds) != 0
            ]

            self.linkCache = []
            for parentNode in self.noteCacheList:
                for childId in parentNode.childIds:
                    self.linkCache.append(Connection(parentNode.id, childId))

        def onSuccess(p):
            self.inRefreshProcess = False
            if self._closed:
                return
            if self.needRefreshAgain:
                self.needRefreshAgain = False
                self.refreshGlobalGraph(onlyChangedNote, "backlog")
                return

            self.lastSearchState = searchState
            self.web.eval(
                f'''reloadPage(
                            {json.dumps([x.toJsNoteNode("highlight") if x.id in self.hlIds else x.toJsNoteNode("normal") for x in self.noteCacheList], default=lambda o: o.__dict__)},
                            {json.dumps(self.linkCache, default=lambda o: o.__dict__)},
                            {json.dumps(resetCenter)},
                            {json.dumps(adaptScale)},
                            "{self.qColorToString(QColor.fromRgb(*config["globalGraph-nodeColor"]))}",
                            "{self.qColorToString(QColor.fromRgb(*config["globalGraph-highlightedNodeColor"]))}",
                            "{self.qColorToString(QColor.fromRgb(*config["globalGraph-tagNodeColor"]))}",
                            {config["globalGraph-backgroundColor"]},
                            {json.dumps(config["globalGraph-nodeDegreeSizing"])}
                        )'''
            )

        def onFailure(e: Exception):
            self.inRefreshProcess = False
            if self._closed:
                return
            if isinstance(e, SearchError):
                show_exception(parent=self, exception=e)
            else:
                log(type(e).__name__, e)

            if self.needRefreshAgain:
                self.needRefreshAgain = False
                self.refreshGlobalGraph(onlyChangedNote, "backlog")

        QueryOp(parent=self, op=op, success=onSuccess).failure(onFailure).run_in_background()

    def closeEvent(self, event):
        if self._closed:
            event.accept()
            return
        self._closed = True
        self.needRefreshAgain = False
        remove_hook_safely(gui_hooks.operation_did_execute, self.onOpChange)
        remove_hook_safely(gui_hooks.collection_did_load, self.refreshGlobalGraph)
        remove_hook_safely(gui_hooks.editor_did_update_tags, self.onTagUpdate)
        saveGeom(self, "GlobalGraph")
        cleanup_webview(self, "web")
        state.globalGraph = None
        event.accept()

    def qColorToString(self, qColor: QColor):
        return f"rgb({qColor.red()},{qColor.green()},{qColor.blue()})"

    def centerOnNote(self, nid: int):
        """Ask the active graph renderer to center on a note when layout is ready."""
        try:
            if self._closed or not hasattr(self, "web") or self.web is None:
                return
            self.web.eval(f"window.AnkiNoteLinkerNewGraph?.focusNode({json.dumps(nid)})")
        except Exception as e:
            log("centerOnNote error", e)

    def printChanges(self, changes):
        """Used for debugging and developing new features"""
        if changes.card:
            print("changed ------------------ " + "card")
        if changes.note:
            print("changed ------------------ " + "note")
        if changes.deck:
            print("changed ------------------ " + "deck")
        if changes.tag:
            print("changed ------------------ " + "tag")
        if changes.notetype:
            print("changed ------------------ " + "notetype")
        if changes.config:
            print("changed ------------------ " + "config")
        if changes.deck_config:
            print("changed ------------------ " + "deck_config")
        if changes.mtime:
            print("changed ------------------ " + "mtime")
        if changes.browser_table:
            print("changed ------------------ " + "browser_table")
        if changes.browser_sidebar:
            print("changed ------------------ " + "browser_sidebar")
        if changes.note_text:
            print("changed ------------------ " + "note_text")
        if changes.study_queues:
            print("changed ------------------ " + "study_queues")
