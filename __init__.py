"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import json
import operator
import uuid
from typing import Set

import anki
from anki import notetypes_pb2
from anki.cards import Card
from anki.errors import NotFoundError
from anki.notes import Note, NoteId
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.browser.previewer import BrowserPreviewer, Previewer
from aqt.editor import Editor, EditorWebView, EditorMode
from aqt.main import MainWindowState
from aqt.reviewer import Reviewer
from aqt.utils import *
from aqt.webview import AnkiWebView

oldVersion = False
import sys
import importlib
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
try:
    from anki.models import StockNotetype
except ImportError:
    oldVersion = True

from .config import ConfigView, config
from .editors import MyAddCards, MyEditCurrent
from .state import Connection, JsNoteNode, NoteNode, addon_path, log, links_html, \
    graph_html, PreviewState, newGraph_html, getWebFileLink
from .translation import getTr
from .globalGraph import GlobalGraph


class AnkiNoteLinker(object):
    def __init__(self):
        self.editors: Set[Editor] = set()

        gui_hooks.webview_did_receive_js_message.append(self.handlePycmd)
        gui_hooks.card_will_show.append(self.convertLink)
        gui_hooks.editor_did_init.append(self.injectPage)
        gui_hooks.editor_did_init_buttons.append(self.injectButton)
        gui_hooks.editor_did_load_note.append(self.onLoadNote)
        gui_hooks.editor_did_fire_typing_timer.append(self.onEditNote)
        gui_hooks.webview_will_set_content.append(self.appendJsToEditor)
        gui_hooks.browser_will_show_context_menu.append(self.injectRightClickMenu)
        gui_hooks.editor_will_show_context_menu.append(self.injectRightClickMenu)
        gui_hooks.reviewer_will_show_context_menu.append(self.injectContextMenuToReviewer)
        gui_hooks.state_did_change.append(self.onStateChange)
        gui_hooks.reviewer_will_end.append(self.onReviewerEnd)
        gui_hooks.reviewer_did_show_answer.append(self.refreshReviewerPanel)
        gui_hooks.reviewer_did_show_question.append(lambda card: self.refreshReviewerPanel(card, True))
        # gui_hooks.previewer_did_init.append(lambda p: print('init', p))

        def cleanUpPreviewerState(previewer: Previewer):
            previewerState = previewer._parent
            print(previewerState)
            if hasattr(previewerState, 'cleanUpState'):
                previewerState.cleanUpState()

        Previewer._on_close = anki.hooks.wrap(Previewer._on_close, cleanUpPreviewerState)

        def cleanUpEditor(editor):
            self.editors.discard(editor)
            if hasattr(editor, "linksPage") and editor.linksPage:
                editor.linksPage.cleanup()
                editor.linksPage.close()
            if hasattr(editor, "graphPage") and editor.graphPage:
                editor.graphPage.cleanup()
                editor.graphPage.close()

        Editor.cleanup = anki.hooks.wrap(Editor.cleanup, cleanUpEditor)

        menu = QMenu("Anki Note Linker", mw.form.menubar)
        openGlobalGraphAction = QAction(menu)
        openGlobalGraphAction.setText(getTr("Global Relationship Graph (Experimental)"))
        qconnect(openGlobalGraphAction.triggered, lambda _: self.openGlobalGraph())
        menu.addAction(openGlobalGraphAction)
        openConfigAction = QAction(menu)
        openConfigAction.setText(getTr("Config"))
        qconnect(openConfigAction.triggered, lambda _: ConfigView.openConfigView())
        menu.addAction(openConfigAction)
        mw.form.menubar.addMenu(menu)

    def onStateChange(self, newState: MainWindowState, oldState: MainWindowState):
        if newState == "review":
            self.onToggleReviewerPanel(config['showLinksPageInReviewerAutomatically'])

    def onReviewerEnd(self):
        self.onToggleReviewerPanel(False)
        mw.setCentralWidget(mw.mwWidget)
        mw.mwWidget.setParent(mw)
        del mw.reviewer.linksPageSplitter
        mw.reviewer.linksPage.cleanup()
        mw.reviewer.linksPage.close()
        del mw.reviewer.linksPage

    def onToggleReviewerPanel(self, checked: bool):
        mw.reviewer.showLinksPage = checked
        if checked:
            if hasattr(mw.reviewer, 'linksPage'):
                mw.reviewer.linksPage.show()
            else:
                self.injectLinksPageToMainWindow()
            self.refreshReviewerPanel(mw.reviewer.card, waitingForShowAnswer=mw.reviewer.state != 'answer')
        else:
            if hasattr(mw.reviewer, 'linksPage'):
                mw.reviewer.linksPage.hide()

    def injectContextMenuToReviewer(self, reviewer: Reviewer, menu: QMenu):
        togglePanelAction = QAction(menu)
        togglePanelAction.setText(getTr('Show Links Panel'))
        togglePanelAction.setCheckable(True)
        togglePanelAction.setChecked(reviewer.showLinksPage)

        qconnect(togglePanelAction.triggered, self.onToggleReviewerPanel)
        menu.addSeparator()
        menu.addAction(togglePanelAction)
        menu.addSeparator()

    def refreshReviewerPanel(self, card: Card, waitingForShowAnswer=False):
        # print(f'{datetime.now()}:{waitingForShowAnswer}')
        if not hasattr(mw.reviewer, 'linksPage'):
            return
        if mw.reviewer.showLinksPage:
            log(f'-----refresh reviewer panel')
            if waitingForShowAnswer:
                mw.reviewer.linksPage.eval(f'reloadPage([], [], waitingForShowAnswer = true)')
                return

            currentNode = self.noteToNoteNode(card.note())
            parentNodes: set[NoteNode] = set()
            parentNodeIds: set[NoteId] = set()
            childNodes: list[NoteNode] = []
            parentJsNodes: list[JsNoteNode] = []
            childJsNodes: list[JsNoteNode] = []

            for parentId in currentNode.parentIds:
                parentNode = self.idToNoteNode(parentId)
                parentNodes.add(parentNode)
                parentNodeIds.add(parentId)
                parentJsNodes.append(parentNode.toJsNoteNode('parent'))

            for childId in currentNode.childIds:
                childNode = self.idToNoteNode(childId)
                childNodes.append(childNode)
                jsNode = childNode.toJsNoteNode('child')
                childJsNodes.append(jsNode)
                if childNode.id in parentNodeIds:  # When a node is both a parent node and a child node
                    jsNode.type = 'parent child'

            mw.reviewer.linksPage.eval(
                f'''reloadPage(
                            {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                            {json.dumps(childJsNodes, default=lambda o: o.__dict__)}
                        )'''
            )

    def injectLinksPageToMainWindow(self):
        mw.reviewer.linksPageSplitter = QSplitter()
        mw.reviewer.linksPage = AnkiWebView(parent=mw.reviewer.linksPageSplitter, title="links_page")
        mw.reviewer.linksPage.set_bridge_command(lambda s: s, mw.reviewer.linksPage)
        mw.reviewer.linksPage.stdHtml(
            f'<script>const ankiContext = "REVIEWER"</script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            r'<style>.link-button-text{-webkit-line-clamp: ' + str(config['linkMaxLines']) + '; line-clamp: ' + str(
                config['linkMaxLines']) + ';}</style>' +
            links_html
        )
        mw.mwWidget = mw.centralWidget()
        wrappedMwWidget = QWidget()
        wrappedMwLayout = QVBoxLayout(wrappedMwWidget)
        wrappedMwLayout.setContentsMargins(0, 0, 0, 0)
        wrappedMwLayout.setSpacing(0)
        wrappedMwWidget.setLayout(wrappedMwLayout)
        wrappedMwLayout.addWidget(mw.mwWidget)
        mw.mwWidget.setParent(wrappedMwWidget)

        mwR, panelR = [int(r) * 10000 for r in config["splitRatioBetweenReviewerAndPanel"].split(":")]
        location = config["positionRelativeToReviewer"]

        if location == "left":
            mw.reviewer.linksPage.setContentsMargins(10, 0, 0, 0)
            mw.reviewer.linksPageSplitter.setOrientation(Qt.Orientation.Horizontal)
            mw.reviewer.linksPageSplitter.addWidget(mw.reviewer.linksPage)
            mw.reviewer.linksPageSplitter.addWidget(wrappedMwWidget)
            sizes = [panelR, mwR]
        elif location == "right":
            mw.reviewer.linksPage.setContentsMargins(0, 0, 10, 0)
            mw.reviewer.linksPageSplitter.setOrientation(Qt.Orientation.Horizontal)
            mw.reviewer.linksPageSplitter.addWidget(wrappedMwWidget)
            mw.reviewer.linksPageSplitter.addWidget(mw.reviewer.linksPage)
            sizes = [mwR, panelR]
        else:
            raise ValueError("Invalid value for config key location")

        mw.reviewer.linksPageSplitter.setSizes(sizes)
        mw.setCentralWidget(mw.reviewer.linksPageSplitter)

    def injectRightClickMenu(self, context, menu: QMenu):
        if isinstance(context, EditorWebView):
            if context.editor.currentField is not None:
                menu.addSeparator()
                insertLinkWithClipboardIDAction = QAction(context)
                insertLinkWithClipboardIDAction.setText(getTr("Insert link with copied note ID"))
                insertLinkWithClipboardIDAction.setShortcut(config['shortcuts-insertLinkWithClipboardID'])
                qconnect(insertLinkWithClipboardIDAction.triggered,
                         lambda _, c=context: self.insertLinkWithClipboardID(c.editor))
                menu.addAction(insertLinkWithClipboardIDAction)

                insertNewLinkAction = QAction(context)
                insertNewLinkAction.setText(getTr("Insert new link"))
                insertNewLinkAction.setShortcut(config['shortcuts-insertNewLink'])
                qconnect(insertNewLinkAction.triggered, lambda _, c=context: self.insertNewLink(c.editor))
                menu.addAction(insertNewLinkAction)

                insertLinkTemplateAction = QAction(context)
                insertLinkTemplateAction.setText(getTr("Insert link template"))
                insertLinkTemplateAction.setShortcut(config['shortcuts-insertLinkTemplate'])
                qconnect(insertLinkTemplateAction.triggered, lambda _, c=context: self.insertLinkTemplate(c.editor))
                menu.addAction(insertLinkTemplateAction)
                menu.addSeparator()
            if context.editor.addMode:
                return
        menu.addSeparator()
        copyNoteIdAction = QAction(context)
        copyNoteIdAction.setText(getTr("Copy current note ID"))
        copyNoteIdAction.setShortcut(config['shortcuts-copyNoteID'])
        qconnect(copyNoteIdAction.triggered, lambda _, c=context: self.copyNoteID(c))
        menu.addAction(copyNoteIdAction)

        copyNoteLinkAction = QAction(context)
        copyNoteLinkAction.setText(getTr("Copy current note link"))
        copyNoteLinkAction.setShortcut(config['shortcuts-copyNoteLink'])
        qconnect(copyNoteLinkAction.triggered, lambda _, c=context: self.copyNoteLink(c))
        menu.addAction(copyNoteLinkAction)

        openNoteInNewWindowAction = QAction(context)
        openNoteInNewWindowAction.setText(getTr("Open current note in new window"))
        openNoteInNewWindowAction.setShortcut(config['shortcuts-openNoteInNewWindow'])
        qconnect(openNoteInNewWindowAction.triggered, lambda _, c=context: self.openNoteInNewEditor(c))
        menu.addAction(openNoteInNewWindowAction)
        menu.addSeparator()

    def injectShortcuts(self, web: EditorWebView):
        QShortcut(QKeySequence(config['shortcuts-insertLinkWithClipboardID']), web,
                  lambda: self.insertLinkWithClipboardID(web.editor))
        QShortcut(QKeySequence(config['shortcuts-insertNewLink']), web, lambda: self.insertNewLink(web.editor))
        QShortcut(QKeySequence(config['shortcuts-insertLinkTemplate']), web,
                  lambda: self.insertLinkTemplate(web.editor))
        if not web.editor.addMode:
            QShortcut(QKeySequence(config['shortcuts-copyNoteID']), web, lambda: self.copyNoteID(web))
            QShortcut(QKeySequence(config['shortcuts-copyNoteLink']), web, lambda: self.copyNoteLink(web))
            QShortcut(QKeySequence(config['shortcuts-openNoteInNewWindow']), web,
                      lambda: self.openNoteInNewEditor(web))

    def convertLink(self, text: str, card: Card, kind: str):
        """Convert note links to HTML hyperlinks, set add-on active flag"""
        return (
                '<script>window.AnkiNoteLinkerIsActive = true</script>' +
                re.sub(
                    r'\[((?:[^\[]|\\\[)*?)\|nid(\d{13})\]',
                    lambda match:
                    f'<a class="noteLink" href="javascript:pycmd(`AnkiNoteLinker-openNoteInPreviewer`+`{match.group(2)}`)" '
                    f'oncontextmenu="event.preventDefault();pycmd(`AnkiNoteLinker-openNoteInNewEditor`+`{match.group(2)}`)">' +
                    match.group(1).replace('\\[', '[') + '</a>', text
                )
        )

    def injectLinksPage(self, editor: Editor):
        editor.linksPage = AnkiWebView(parent=editor.innerSplitter, title="links_page")
        editor.linksPage.set_bridge_command(lambda s: s, editor)
        context = 'BROWSER' if editor.editorMode == EditorMode.BROWSER else 'EDIT_CURRENT' if editor.editorMode == EditorMode.EDIT_CURRENT else 'ADD_CARDS'
        editor.linksPage.stdHtml(
            f'<script>const ankiContext = "{context}"</script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            r'<style>.link-button-text{-webkit-line-clamp: ' + str(config['linkMaxLines']) + '; line-clamp: ' + str(
                config['linkMaxLines']) + ';}</style>' +
            links_html
        )

    def injectGraphPage(self, editor: Editor):
        editor.graphPage = AnkiWebView(parent=editor.innerSplitter, title="graph_page")
        editor.graphPage.set_bridge_command(lambda s: s, editor)
        context = 'BROWSER' if editor.editorMode == EditorMode.BROWSER else 'EDIT_CURRENT' if editor.editorMode == EditorMode.EDIT_CURRENT else 'ADD_CARDS'
        editor.graphPage.stdHtml(
            f'<script>const ankiContext = "{context}"</script>'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            f'<script src="{getWebFileLink("js/d3.js")}"></script>'
            f'<script src="{getWebFileLink("js/pixi.js")}"></script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>' + newGraph_html
        )

    def switchToOldRenderer(self, e):
        context = 'BROWSER' if e.editorMode == EditorMode.BROWSER else 'EDIT_CURRENT' if e.editorMode == EditorMode.EDIT_CURRENT else 'ADD_CARDS'
        e.graphPage.stdHtml(
            f'<script>const ankiContext = "{context}"</script>'
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<link rel="stylesheet" href="{getWebFileLink("katex.css")}">'
            f'<script defer src="{getWebFileLink("js/katex.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-mhchem.js")}"></script>'
            f'<script defer src="{getWebFileLink("js/katex-auto-render.js")}"></script>'
            f'<script src="{getWebFileLink("js/d3.js")}"></script>'
            f'<script src="{getWebFileLink("js/force-graph.js")}"></script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>' + graph_html
        )
        self.refreshPage(e, resetCenter=True, reason='Switch To Old Renderer')

    def injectPage(self, editor: Editor):
        self.injectShortcuts(editor.web)
        if editor.addMode:
            return

        editor.innerSplitter = QSplitter()
        editor.innerSplitter.setOrientation(Qt.Orientation.Vertical)
        if not config['showLinksPageAutomatically'] and not config['showGraphPageAutomatically']:
            editor.innerSplitter.hide()
        else:
            if config['showLinksPageAutomatically']:
                self.injectLinksPage(editor)
                editor.innerSplitter.addWidget(editor.linksPage)
            if config['showGraphPageAutomatically']:
                self.injectGraphPage(editor)
                editor.innerSplitter.addWidget(editor.graphPage)

        editor.innerSplitter.setSizes(
            [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")])

        layout = editor.web.parentWidget().layout()
        if layout is None:
            layout = QVBoxLayout()
            editor.web.parentWidget().setLayout(layout)

        web_index = layout.indexOf(editor.web)
        layout.removeWidget(editor.web)

        wrappedWeb = QWidget()
        wrapLayout = QHBoxLayout()
        wrapLayout.setContentsMargins(0, 0, 0, 0)
        wrapLayout.setSpacing(0)
        wrappedWeb.setLayout(wrapLayout)
        wrapLayout.addWidget(editor.web)  # Wrap the web view layer by layer to improve compatibility with other plugins

        mainR, editorR = [int(r) * 10000 for r in config["splitRatio"].split(":")]
        location = config["location"]
        outerSplitter = QSplitter()

        if location == "left":
            outerSplitter.setOrientation(Qt.Orientation.Horizontal)
            outerSplitter.addWidget(editor.innerSplitter)
            outerSplitter.addWidget(wrappedWeb)
            sizes = [editorR, mainR]
        elif location == "right":
            outerSplitter.setOrientation(Qt.Orientation.Horizontal)
            outerSplitter.addWidget(wrappedWeb)
            outerSplitter.addWidget(editor.innerSplitter)
            sizes = [mainR, editorR]
        else:
            raise ValueError("Invalid value for config key location")

        outerSplitter.setSizes(sizes)
        layout.insertWidget(web_index, outerSplitter)

    def injectButton(self, buttons: list[str], editor: Editor):
        if editor.addMode:
            return

        def toggleLinksPage(e: Editor):
            if hasattr(e, 'linksPage'):
                if e.linksPage.isHidden():
                    e.innerSplitter.show()
                    e.linksPage.show()
                    self.refreshPage(e, target='linksPage', reason='toggleLinksPage')
                else:
                    e.linksPage.hide()
                    if not hasattr(e, 'graphPage') or e.graphPage.isHidden():
                        e.innerSplitter.hide()
            else:
                self.injectLinksPage(e)
                e.innerSplitter.insertWidget(0, e.linksPage)
                editor.innerSplitter.setSizes(
                    [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")])
                e.innerSplitter.show()
                self.refreshPage(e, target='linksPage', reason='toggleLinksPage')

        def toggleGraphPage(e: Editor):
            if hasattr(e, 'graphPage'):
                if e.graphPage.isHidden():
                    e.innerSplitter.show()
                    e.graphPage.show()
                    self.refreshPage(e, target='graphPage', reason='toggleGraphPage')
                else:
                    e.graphPage.hide()
                    if not hasattr(e, 'linksPage') or e.linksPage.isHidden():
                        e.innerSplitter.hide()
            else:
                self.injectGraphPage(e)
                e.innerSplitter.addWidget(e.graphPage)
                editor.innerSplitter.setSizes(
                    [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")])
                e.innerSplitter.show()
                self.refreshPage(e, target='graphPage', reason='toggleGraphPage')

        icons_dir = os.path.join(addon_path, "icons")
        toggleLinksPageButton = editor.addButton(
            icon=os.path.join(icons_dir, "showLinksPage.svg"),
            cmd="_editor_toggle_links",
            tip=getTr("Toggle Links Panel"),
            func=toggleLinksPage,
            disables=False,
        )
        toggleGraphPageButton = editor.addButton(
            icon=os.path.join(icons_dir, "showGraphPage.svg"),
            cmd="_editor_toggle_graph",
            tip=getTr("Toggle Graph Panel"),
            func=toggleGraphPage,
            disables=False,
        )
        buttons.append(toggleLinksPageButton)
        buttons.append(toggleGraphPageButton)

    def onLoadNote(self, editor: Editor):
        # self.editors = set(filter(lambda it: it.note is not None, self.editors))
        if editor.addMode:
            return
        self.editors.add(editor)
        # log(json.dumps(editor.note.note_type(), default=lambda o: o.__dict__, indent = 4))
        self.refreshPage(editor, resetCenter=True, reason='loaded note')

    def onEditNote(self, note: Note):
        if note.id == 0:
            return
        for editor in self.editors:
            if editor.note.id == note.id:
                if hasattr(editor, "noteNode") and \
                        editor.noteNode.mainField == self.getMainField(note) and \
                        operator.eq(editor.noteNode.childIds, self.findChildIds(note.id, ' '.join(note.fields))):
                    return
                else:
                    self.refreshPage(editor, adaptScale=False, reason='mainField or links of note changed')

        if state.globalGraph is not None and note.id in state.globalGraph.searchedIds:
            state.globalGraph.refreshGlobalGraph(note, 'mainField or links of note changed')

    def idToNoteNode(self, nid: NoteId):
        try:
            note = mw.col.get_note(nid)
        except NotFoundError:
            return NoteNode(nid, [], set(), None)
        return self.noteToNoteNode(note)

    def noteToNoteNode(self, note: Note):
        return NoteNode(note.id, self.findChildIds(note.id, ' '.join(note.fields)),
                        self.findParentIds(note.id), self.getMainField(note))

    def _isPanelsShow(self, e: Editor):
        if hasattr(e, "linksPage") and not e.linksPage.isHidden():
            linksPageShow = True
        else:
            linksPageShow = False
        if hasattr(e, "graphPage") and not e.graphPage.isHidden():
            graphPageShow = True
        else:
            graphPageShow = False
        return linksPageShow, graphPageShow

    def refreshPage(self, editor: Editor, resetCenter: bool = False, adaptScale: bool = True, target='all',
                    reason: str = ''):
        if editor.note is None or editor.addMode:
            return
        panelShows = self._isPanelsShow(editor)
        if not panelShows[0] and not panelShows[1]:
            return

        log(f'-----refresh page: {reason}, at', editor)

        currentId = editor.note.id
        currentNode = self.noteToNoteNode(editor.note)
        editor.noteNode = currentNode

        allIds = currentNode.parentIds | set(currentNode.childIds) | {currentId}

        parentNodes: set[NoteNode] = set()
        parentNodeIds: set[NoteId] = set()
        childNodes: list[NoteNode] = []
        parentJsNodes: list[JsNoteNode] = []
        childJsNodes: list[JsNoteNode] = []
        duplicatedJsNodeIds: set[int] = set()

        for parentId in currentNode.parentIds:
            parentNode = self.idToNoteNode(parentId)
            parentNodes.add(parentNode)
            parentNodeIds.add(parentId)
            parentJsNodes.append(parentNode.toJsNoteNode('parent'))

        for childId in currentNode.childIds:
            childNode = self.idToNoteNode(childId)
            childNodes.append(childNode)
            jsNode = childNode.toJsNoteNode('child')
            childJsNodes.append(jsNode)
            if childNode.id in parentNodeIds:  # When a node is both a parent node and a child node
                jsNode.type = 'parent child'
                duplicatedJsNodeIds.add(jsNode.id)

        allNodes = parentNodes | set(childNodes) | {currentNode}
        allJsNodes = childJsNodes + [x for x in parentJsNodes if x.id not in duplicatedJsNodeIds] + [
            currentNode.toJsNoteNode('me')]

        allConnections: list[Connection] = []
        for parentNode in allNodes:
            for childId in parentNode.childIds:
                if childId in allIds:
                    allConnections.append(Connection(parentNode.id, childId))
        if target != 'graphPage' and panelShows[0]:
            editor.linksPage.eval(
                f'''reloadPage(
                    {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                    {json.dumps(childJsNodes, default=lambda o: o.__dict__)}
                )'''
            )
        if target != 'linksPage' and panelShows[1]:
            editor.graphPage.eval(
                f'''reloadPage(
                {json.dumps(allJsNodes, default=lambda o: o.__dict__)},
                {json.dumps(allConnections, default=lambda o: o.__dict__)},
                {json.dumps(resetCenter)},
                {json.dumps(adaptScale)}
                )'''
            )

    def appendJsToEditor(self, web_content, context):
        """Enable the editor to support shortcut keys and double-click nid trigger operations"""
        if not isinstance(context, Editor):
            return
        script_str = """
            <script>
            window.addEventListener('dblclick', function (e) {
                var nidreg = /^nid\d{13}$/;
                var newreg = /^new\d{8}$/;
                const st = window.getSelection().toString();
                if (st != ''){
                    if (nidreg.test(st)){
                        const nid = st.slice(3)
                        pycmd('AnkiNoteLinker-openNoteInNewEditor' + nid);
                    }else if (newreg.test(st)){
                        const placeholder = st.slice(3)
                        pycmd('AnkiNoteLinker-openAddNoteWindow' + placeholder)
                    }
                }
            });
            </script>
            """
        web_content.head += script_str

    def findChildIds(self, myId: NoteId, joinedFields: str, rangeIdSet=None):
        duplicateIdSet = set()  # Used to remove duplicates
        idList: list[NoteId] = []
        matches = re.finditer(r'\[(?:[^\[]|\\\[)*?\|nid(\d{13})\]', joinedFields)
        if matches:
            for match in matches:
                childId = NoteId(int(match.group(1)))
                if myId != childId and childId not in duplicateIdSet:  # Shield self ring connection and remove duplicates
                    if rangeIdSet is None or childId in rangeIdSet:
                        duplicateIdSet.add(childId)
                        idList.append(childId)
        return idList

    def findParentIds(self, myId):
        parentIds = set(mw.col.find_notes('[*|nid' + str(myId) + ']'))
        parentIds.discard(myId)
        return parentIds

    def getMainField(self, note: Note) -> str:
        """If it is an image occlusion type, return its "Title" field; otherwise, return the first field"""
        mainField: str = ''
        if not oldVersion and note.note_type().get("originalStockKind",
                                                   None) == StockNotetype.OriginalStockKind.ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION:
            for flds in note.note_type()['flds']:
                if flds['tag'] == notetypes_pb2.IMAGE_OCCLUSION_FIELD_HEADER:
                    mainField = note.fields[flds['ord']]
                    break
        else:
            try:
                mainField = note.fields[0] if note.fields[0] != '' else note.fields[1]
            except IndexError:
                mainField = 'Empty note'

        # Clear Link Format
        mainField = re.sub(r'\[((?:[^\[]|\\\[)*?)\|(nid\d{13})\]', lambda m: m[1].replace('\\[', '['), mainField)
        # Clear Cloze Format
        pattern = r'\{\{c\d+?::((:?(?!\{\{c\d+?::).|\n)*?)\}\}'
        while re.search(pattern, mainField):
            mainField = re.sub(pattern, '[...]' if config['collapseClozeInLinksPage'] else r'\1', mainField)
        return mainField

    def handlePycmd(self, handled: tuple[bool, Any], message: str, context: Any):
        """Handling web js events"""

        def validateNid(nid):
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return False
            return True

        if re.match(r'AnkiNoteLinker-setNoteToEditor\d{13}', message):
            nid = int(message[30:])
            if not validateNid(nid):
                return True, None
            editor: Editor = context
            editor.set_note(aqt.mw.col.get_note(NoteId(nid)), focusTo=0)
            return True, None
        elif re.match(r'AnkiNoteLinker-openNoteInBrowser\d{13}', message):
            nid = int(message[32:])
            if not validateNid(nid):
                return True, None
            self.openNoteInBrowser(context, nid)
            return True, None
        elif re.match(r'AnkiNoteLinker-openNoteInNewEditor\d{13}', message):
            nid = int(message[34:])
            if not validateNid(nid):
                return True, None
            self.openNoteInNewEditor(context, nid)
            return True, None
        elif re.match(r'AnkiNoteLinker-openNoteInPreviewer\d{13}', message):
            nid = int(message[34:])
            if not validateNid(nid):
                return True, None
            self.openNoteInPreviewer(context, nid)
            return True, None
        elif re.match(r'AnkiNoteLinker-openNoteInBrowser\d{13}', message):
            nid = int(message[32:])
            if not validateNid(nid):
                return True, None
            self.openNoteInBrowser(context, nid)
            return True, None
        elif re.match(r'AnkiNoteLinker-openAddNoteWindow\d{8}', message):
            placeholder = message[32:]
            editor: Editor = context
            if editor.addMode:
                tooltip(getTr('Please add the current note first'))
                return True, None
            match = re.search(r'\[((?:[^\[]|\\\[)*?)\|new' + placeholder + ']', editor.note.joined_fields())
            text = ''
            if match:
                text = match.group(1).replace('\\[', '[')
            note = aqt.mw.col.new_note(editor.note.note_type())
            if not oldVersion and note.note_type().get("originalStockKind",
                                                       None) == StockNotetype.OriginalStockKind.ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION:
                for flds in note.note_type()['flds']:
                    if flds['tag'] == notetypes_pb2.IMAGE_OCCLUSION_FIELD_HEADER:
                        note.fields[flds['ord']] = text
                        break
            else:
                note.fields[0] = text
            add = MyAddCards(editor.note, placeholder)
            add.set_note(note, editor.note.cards()[0].did)
            return True, None
        elif re.match(r'AnkiNoteLinker-tagSearch.*', message):
            tag = message[24:]
            browser: Browser = aqt.dialogs.open('Browser', aqt.mw)
            browser.activateWindow()
            browser.search_for('tag:' + tag)
            return True, None
        elif message == 'AnkiNoteLinker-switchToOldRenderer':
            if isinstance(context, Editor):
                self.switchToOldRenderer(context)
            else:
                context.switchToOldRenderer()
            return True, None
        else:
            return handled

    def _getNoteIDFromContext(self, context):
        if isinstance(context, Editor):
            return context.note.id
        elif isinstance(context, EditorWebView):
            return context.editor.note.id
        elif isinstance(context, Browser):
            browser: Browser = context
            if browser.card is None:
                tooltip(getTr("Please select a single note/card"))
                return None
            return browser.card.nid
        else:
            return None

    def copyNoteID(self, context):
        nid = self._getNoteIDFromContext(context)
        if nid is not None:
            QApplication.clipboard().setText(str(nid))
            tooltip(getTr('Copied note ID'))

    def copyNoteLink(self, context):
        nid = self._getNoteIDFromContext(context)
        if nid is not None:
            QApplication.clipboard().setText('[|nid' + str(nid) + ']')
            tooltip(getTr('Copied note link'))

    def openNoteInNewEditor(self, context, nid=None):
        if nid is None:
            nid = self._getNoteIDFromContext(context)
        if nid is not None:
            ed = MyEditCurrent(NoteId(nid))
            ed.activateWindow()

    def openNoteInPreviewer(self, context, nid=None):
        if nid is None:
            nid = self._getNoteIDFromContext(context)
        if nid is not None:
            cards = aqt.mw.col.get_note(NoteId(nid)).cards()
            previewState = PreviewState(cards)
            # Attempt to support the review button for the hjp-linkmaster addon
            try:
                if not config["useHjpPreviewer"]:
                    raise Exception
                hjp = importlib.import_module('1420819673')
                previewer = hjp.lib.common_tools.funcs.MonkeyPatch.BrowserPreviewer(previewState, mw, lambda: None)
            except Exception:
                previewer: BrowserPreviewer = BrowserPreviewer(previewState, mw, lambda: None)
            previewState.setPreviewer(previewer)
            previewer.open()

    def openNoteInBrowser(self, context, nid=None):
        if nid is None:
            nid = self._getNoteIDFromContext(context)
        if nid is not None:
            browser: Browser = aqt.dialogs.open('Browser', aqt.mw)
            browser.activateWindow()

            card = aqt.mw.col.get_note(NoteId(nid)).cards()[0]
            browser.table.select_single_card(card.id)
            if not browser.table.has_current():
                browser.search_for('deck:' + aqt.mw.col.decks.get(card.did)['name'])
                browser.table.select_single_card(card.id)

    def insertLinkTemplate(self, editor: Editor):
        text = editor.web.selectedText().replace('[', '\\[')
        editor.doPaste(f'[{text}|nid]', True)

    def insertLinkWithClipboardID(self, editor: Editor):
        text = editor.web.selectedText().replace('[', '\\[')
        idText = QApplication.clipboard().text()
        if re.match(r'^\d{13}$', idText):
            editor.doPaste(f'[{text}|nid{idText}]', True)
        else:
            tooltip(getTr('The content in the clipboard is not a note ID'))

    def insertNewLink(self, editor: Editor):
        text = editor.web.selectedText().replace('[', '\\[')
        placeholder = str(uuid.uuid4().int)[0:8]
        editor.doPaste(f'[{text}|new{placeholder}]', True)

    def openGlobalGraph(self):
        if state.globalGraph is None:
            state.globalGraph = GlobalGraph()
        else:
            state.globalGraph.showNormal()
            state.globalGraph.activateWindow()


state.addon = AnkiNoteLinker()
