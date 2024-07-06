"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import json
from typing import Optional

import anki
from anki.collection import OpChanges, Collection
from anki.errors import SearchError
from anki.notes import NoteId, Note
from aqt.errors import show_exception
from aqt.operations import QueryOp
from aqt import QColor, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QHBoxLayout, QCheckBox, gui_hooks
from aqt import mw, qconnect
from aqt.utils import restoreGeom, saveGeom, tooltip
from aqt.webview import AnkiWebView

from . import state
from .config import config
from .translation import getTr
from .state import Connection, graph_html, NoteNode, log, newGraph_html, getWebFileLink


class GlobalGraph(QWidget):
    def __init__(self):
        super().__init__()
        gui_hooks.operation_did_execute.append(self.onOpChange)
        gui_hooks.collection_did_load.append(self.refreshGlobalGraph)
        self.noteCache: dict[int, NoteNode] = {}
        self.searchedIds: set[NoteId] = set()
        self.needRefreshAgain = False
        self.inRefreshProcess = False
        self.lastSearchText = None
        self.linkCache: list[Connection] = []
        self.noteCacheList = []
        self.hlIds = set()
        self.setWindowTitle(getTr("Global Relationship Graph (Experimental)"))
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
        self.web.stdHtml(
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            f'<script src="{getWebFileLink("js/d3.js")}"></script>'
            f'<script src="{getWebFileLink("js/pixi.js")}"></script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>' + newGraph_html
        )
        self.web.set_bridge_command(lambda s: s, self)
        outerLayout.addWidget(self.topBar)
        outerLayout.addWidget(self.web)
        self.lineEdit = QLineEdit()
        self.lineEdit.setText(config['globalGraph']['defaultSearchText'])
        self.lineEdit2 = QLineEdit()
        self.lineEdit2.setText(config['globalGraph']['defaultHighlightFilter'])
        self.checkBox = QCheckBox(getTr('Display single notes'))
        self.checkBox.setChecked(config['globalGraph']['defaultShowSingleNode'])
        self.sButton = QPushButton(getTr('Search'))
        qconnect(self.sButton.clicked,
                 lambda: self.refreshGlobalGraph(resetCenter=True, reason='Search Button Clicked'))
        topBarLayout.addWidget(QLabel(getTr('Search notes:')))
        topBarLayout.addWidget(self.lineEdit)
        topBarLayout.addWidget(QLabel(getTr('Highlight specified notes:')))
        topBarLayout.addWidget(self.lineEdit2)
        topBarLayout.addWidget(self.checkBox)
        topBarLayout.addWidget(self.sButton)

        self.activateWindow()
        self.show()
        self.refreshGlobalGraph(adaptScale=True, reason='Init Global Graph')

    def switchToOldRenderer(self):
        self.web.stdHtml(
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            f'<script src="{getWebFileLink("js/d3.js")}"></script>'
            f'<script src="{getWebFileLink("js/force-graph.js")}"></script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>' + graph_html
        )
        self.refreshGlobalGraph(adaptScale=True, reason='Switch To Old Renderer')
        tooltip(getTr(
            'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.'),
            10000)

    def onOpChange(self, changes: OpChanges, handler: Optional[object]):
        # self.printChanges(changes)
        if changes.study_queues or changes.notetype:
            self.refreshGlobalGraph(reason='onOpChange')

    def rebuildCache(self, col: Collection):
        self.noteCache = {}  # 清空缓存
        self.searchedIds = set(col.find_notes(self.lineEdit.text()))  # 获取搜索节点id
        # 获取高亮节点id
        if self.lineEdit2.text() == '':
            self.hlIds = set()
        else:
            self.hlIds = set(col.find_notes(self.lineEdit2.text()))
        for noteId in self.searchedIds:  # 遍历符合搜索条件的笔记的id
            note = col.get_note(noteId)
            self.updateNodeCache(note)

    def updateNodeCache(self, note: Note):
        """Set the node for the note link"""
        if self.needRefreshAgain:  # 如果此时又有了新的刷新请求，则抛出异常使当前刷新操作退出
            raise Exception('-----Interrupted Refresh Global Graph Process')
        noteId = note.id
        childIds = state.addon.findChildIds(noteId, ' '.join(note.fields), rangeIdSet=self.searchedIds)  # 找出当前节点的子节点id
        mainField = state.addon.getMainField(note)
        # Set the forward link
        node = self.noteCache.get(noteId, None)  # Get the current node's information in the cache 在缓存中获取当前笔记节点信息
        if node is not None:  # If the node already exists 如果当前笔记节点存在于缓存中
            oldChildIds = node.childIds  # 获取当前节点的旧的子节点id
            node.mainField = mainField  # Set the node's first field as the new main field 更新当前笔记的主字段
            node.childIds = childIds  # Update its forward link to the new childIds list 更新当前笔记子节点

            # Remove the reverse link of old child nodes (need optimization: Operate only on nodes with changes)
            # 删除旧子节点的反向链接
            for id in oldChildIds:
                if id in self.noteCache:
                    self.noteCache[id].parentIds.discard(noteId)
        else:
            # If the node doesn't exist, create a new NoteNode object and insert it into the cache
            # 如果当前节点不存在缓存中，创建一个新的NoteNode对象并将其插入缓存
            self.noteCache[noteId] = NoteNode(noteId, childIds, set(), mainField)

        # Set the back link of child nodes 为当前节点的子节点设置反向链接
        for childId in childIds:
            if childId in self.noteCache:  # If the node already exists 如果子节点已经存在缓存中
                # Get the information of the forward-linked node in the cache 获取子节点信息
                childNode = self.noteCache[childId]
                if noteId not in childNode.parentIds:  # Prevent adding duplicate IDs
                    childNode.parentIds.add(noteId)  # Add the current node ID to its back link list 将当前id添加到子节点的父节点中
            else:
                # If the node doesn't exist, create a new NoteNode object and insert it into the cache
                self.noteCache[childId] = NoteNode(childId, [], {noteId}, None)

    def refreshGlobalGraph(self, onlyChangedNote: Note = None, reason: str = '', adaptScale=False, resetCenter=False):
        if isinstance(onlyChangedNote, Collection):
            onlyChangedNote = None
            reason = 'collection_did_load'
        if self.inRefreshProcess:
            self.needRefreshAgain = True
            return

        self.inRefreshProcess = True

        def op(col):
            # 如果只改变了一个笔记且此次搜索条件没发生变化
            if onlyChangedNote is not None and self.lineEdit.text() + self.lineEdit2.text() == self.lastSearchText:
                log('-----Refresh Global Graph With Update Single Node: ', reason)
                # 目前存在的问题：如果修改一个笔记使其不符合搜索条件，自动刷新不会使该笔记消失，需要手动刷新
                self.updateNodeCache(onlyChangedNote)  # 只更新改变了的笔记
            else:
                log('-----Refresh Global Graph With Rebuild Cache: ', reason)
                self.rebuildCache(col)  # 重新构造缓存

            showSingle = self.checkBox.isChecked()
            self.noteCacheList = [x for x in self.noteCache.values()
                                  if showSingle or len(x.childIds) != 0 or len(x.parentIds) != 0]

            self.linkCache = []
            for parentNode in self.noteCacheList:
                for childId in parentNode.childIds:
                    self.linkCache.append(Connection(parentNode.id, childId))

        def onSuccess(p):
            self.inRefreshProcess = False
            if self.needRefreshAgain:
                self.needRefreshAgain = False
                self.refreshGlobalGraph(onlyChangedNote, 'backlog')
                return

            self.lastSearchText = self.lineEdit.text() + self.lineEdit2.text()
            self.web.eval(
                f'''reloadPage(
                            {json.dumps([x.toJsNoteNode('highlight') if x.id in self.hlIds else x.toJsNoteNode('normal') for x in self.noteCacheList], default=lambda o: o.__dict__)},
                            {json.dumps(self.linkCache, default=lambda o: o.__dict__)},
                            {json.dumps(resetCenter)},
                            {json.dumps(adaptScale)},
                            "{self.qColorToString(QColor.fromRgb(*config["globalGraph"]["nodeColor"]))}",
                            "{self.qColorToString(QColor.fromRgb(*config["globalGraph"]["highlightedNodeColor"]))}",
                            {config["globalGraph"]["graphBackgroundColor"]}
                        )'''
            )

        def onFailure(e: Exception):
            self.inRefreshProcess = False
            if isinstance(e, SearchError):
                show_exception(parent=self, exception=e)
            else:
                log(type(e).__name__, e)

            if self.needRefreshAgain:
                self.needRefreshAgain = False
                self.refreshGlobalGraph(onlyChangedNote, 'backlog')

        QueryOp(parent=self, op=op, success=onSuccess).failure(onFailure).run_in_background()

    def closeEvent(self, event):
        gui_hooks.operation_did_execute.remove(self.onOpChange)
        gui_hooks.collection_did_load.remove(self.refreshGlobalGraph)
        saveGeom(self, "GlobalGraph")
        self.web.cleanup()
        self.web.close()
        state.globalGraph = None
        event.accept()

    def qColorToString(self, qColor: QColor):
        return f"rgb({qColor.red()},{qColor.green()},{qColor.blue()})"

    def printChanges(self, changes):
        """Used for debugging and developing new features"""
        if changes.card:
            print('changed ------------------ ' + 'card')
        if changes.note:
            print('changed ------------------ ' + 'note')
        if changes.deck:
            print('changed ------------------ ' + 'deck')
        if changes.tag:
            print('changed ------------------ ' + 'tag')
        if changes.notetype:
            print('changed ------------------ ' + 'notetype')
        if changes.config:
            print('changed ------------------ ' + 'config')
        if changes.deck_config:
            print('changed ------------------ ' + 'deck_config')
        if changes.mtime:
            print('changed ------------------ ' + 'mtime')
        if changes.browser_table:
            print('changed ------------------ ' + 'browser_table')
        if changes.browser_sidebar:
            print('changed ------------------ ' + 'browser_sidebar')
        if changes.note_text:
            print('changed ------------------ ' + 'note_text')
        if changes.study_queues:
            print('changed ------------------ ' + 'study_queues')
