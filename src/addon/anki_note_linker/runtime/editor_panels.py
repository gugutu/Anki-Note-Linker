"""Editor panel creation, layout, refresh, and renderer switching."""

import json
import os
import weakref

from anki.notes import NoteId
from aqt import QHBoxLayout, QSplitter, Qt, QVBoxLayout, QWidget, mw
from aqt.editor import Editor, EditorMode
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from . import state
from .configuration import config
from .i18n import getTr
from .lifecycle import cleanup_webview
from .state import (
    Connection,
    JsNoteNode,
    NoteNode,
    addon_path,
    getWebFileLink,
    log,
)
from .web_pages import legacy_graph_page, links_page, new_graph_page


class EditorPanelsMixin:
    def injectLinksPage(self, editor: Editor):
        editor.linksPage = AnkiWebView(parent=editor.innerSplitter, title="links_page")
        editor.linksPage.set_bridge_command(lambda s: s, editor)
        context = (
            "BROWSER"
            if editor.editorMode == EditorMode.BROWSER
            else "EDIT_CURRENT"
            if editor.editorMode == EditorMode.EDIT_CURRENT
            else "ADD_CARDS"
        )
        editor.linksPage.stdHtml(links_page(context))

    def injectGraphPage(self, editor: Editor):
        editor.graphPage = AnkiWebView(parent=editor.innerSplitter, title="graph_page")
        editor.graphPage.set_bridge_command(lambda s: s, editor)
        context = (
            "BROWSER"
            if editor.editorMode == EditorMode.BROWSER
            else "EDIT_CURRENT"
            if editor.editorMode == EditorMode.EDIT_CURRENT
            else "ADD_CARDS"
        )
        editor.graphPage.stdHtml(new_graph_page(context))

    def switchToOldRenderer(self, e):
        context = (
            "BROWSER"
            if e.editorMode == EditorMode.BROWSER
            else "EDIT_CURRENT"
            if e.editorMode == EditorMode.EDIT_CURRENT
            else "ADD_CARDS"
        )
        e.graphPage.stdHtml(legacy_graph_page(context))
        self.refreshPage(e, resetCenter=True, reason="Switch To Old Renderer")

    def switchReviewerGraphToOldRenderer(self):
        if not hasattr(mw.reviewer, "graphPage"):
            return
        mw.reviewer.graphPage.stdHtml(legacy_graph_page("REVIEWER"))
        self.refreshReviewerPanel(mw.reviewer.card, waitingForShowAnswer=mw.reviewer.state != "answer")
        tooltip(
            getTr(
                'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.'
            ),
            10000,
        )

    def injectPage(self, editor: Editor):
        editor_reference = weakref.ref(editor)
        editor.web.destroyed.connect(lambda _object=None, reference=editor_reference: self._cleanupEditor(reference))
        self.injectShortcuts(editor.web)
        if editor.addMode:
            return

        editor.innerSplitter = QSplitter()
        editor.innerSplitter.setOrientation(Qt.Orientation.Vertical)
        if not config["showLinksPageAutomatically"] and not config["showGraphPageAutomatically"]:
            editor.innerSplitter.hide()
        else:
            if config["showLinksPageAutomatically"]:
                self.injectLinksPage(editor)
                editor.innerSplitter.addWidget(editor.linksPage)
            if config["showGraphPageAutomatically"]:
                self.injectGraphPage(editor)
                editor.innerSplitter.addWidget(editor.graphPage)

        editor.innerSplitter.setSizes(
            [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")]
        )

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

    def _cleanupEditor(self, editor_reference):
        editor = editor_reference()
        if editor is None:
            return
        self.editors.discard(editor)
        cleanup_webview(editor, "linksPage")
        cleanup_webview(editor, "graphPage")

    def injectButton(self, buttons: list[str], editor: Editor):
        if editor.addMode:
            return

        def toggleLinksPage(e: Editor):
            if hasattr(e, "linksPage"):
                if e.linksPage.isHidden():
                    e.innerSplitter.show()
                    e.linksPage.show()
                    self.refreshPage(e, target="linksPage", reason="toggleLinksPage")
                else:
                    e.linksPage.hide()
                    if not hasattr(e, "graphPage") or e.graphPage.isHidden():
                        e.innerSplitter.hide()
            else:
                self.injectLinksPage(e)
                e.innerSplitter.insertWidget(0, e.linksPage)
                editor.innerSplitter.setSizes(
                    [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")]
                )
                e.innerSplitter.show()
                self.refreshPage(e, target="linksPage", reason="toggleLinksPage")

        def toggleGraphPage(e: Editor):
            if hasattr(e, "graphPage"):
                if e.graphPage.isHidden():
                    e.innerSplitter.show()
                    e.graphPage.show()
                    self.refreshPage(e, target="graphPage", reason="toggleGraphPage")
                else:
                    e.graphPage.hide()
                    if not hasattr(e, "linksPage") or e.linksPage.isHidden():
                        e.innerSplitter.hide()
            else:
                self.injectGraphPage(e)
                e.innerSplitter.addWidget(e.graphPage)
                editor.innerSplitter.setSizes(
                    [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")]
                )
                e.innerSplitter.show()
                self.refreshPage(e, target="graphPage", reason="toggleGraphPage")

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

    def _isPanelsShow(self, e: Editor):
        linksPageShow = bool(hasattr(e, "linksPage") and not e.linksPage.isHidden())
        graphPageShow = bool(hasattr(e, "graphPage") and not e.graphPage.isHidden())
        return linksPageShow, graphPageShow

    def refreshPage(
        self, editor: Editor, resetCenter: bool = False, adaptScale: bool = True, target="all", reason: str = ""
    ):
        if editor.note is None or editor.addMode:
            return
        panelShows = self._isPanelsShow(editor)
        if not panelShows[0] and not panelShows[1]:
            return

        log(f"-----refresh page: {reason}, at", editor)

        currentId = editor.note.id
        currentNode = self.noteToNoteNode(editor.note)
        showForwardLinkTitle = config["showForwardLinkTitleInLinksPage"]
        childLinkTitles = (
            self.findChildLinkTitles(currentId, " ".join(editor.note.fields)) if showForwardLinkTitle else {}
        )
        editor.noteNode = currentNode
        editor.childLinkTitles = childLinkTitles

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
            parentJsNodes.append(parentNode.toJsNoteNode("parent"))

        for childId in currentNode.childIds:
            childNode = self.idToNoteNode(childId)
            childNodes.append(childNode)
            jsNode = childNode.toJsNoteNode("child")
            if showForwardLinkTitle:
                jsNode.linkTitle = childLinkTitles.get(childId, None)
            childJsNodes.append(jsNode)
            if childNode.id in parentNodeIds:  # When a node is both a parent node and a child node
                jsNode.type = "parent child"
                duplicatedJsNodeIds.add(jsNode.id)

        allNodes = parentNodes | set(childNodes) | {currentNode}
        allJsNodes = (
            childJsNodes
            + [x for x in parentJsNodes if x.id not in duplicatedJsNodeIds]
            + [currentNode.toJsNoteNode("me")]
        )

        allConnections: list[Connection] = []
        for parentNode in allNodes:
            for childId in parentNode.childIds:
                if childId in allIds:
                    allConnections.append(Connection(parentNode.id, childId))
        if target != "graphPage" and panelShows[0]:
            editor.linksPage.eval(
                f"""reloadPage(
                    {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                    {json.dumps(childJsNodes, default=lambda o: o.__dict__)},
                    false,
                    {json.dumps(config["showForwardLinkTitleInLinksPage"])}
                )"""
            )
        if target != "linksPage" and panelShows[1]:
            editor.graphPage.eval(
                f"""reloadPage(
                {json.dumps(allJsNodes, default=lambda o: o.__dict__)},
                {json.dumps(allConnections, default=lambda o: o.__dict__)},
                {json.dumps(resetCenter)},
                {json.dumps(adaptScale)}
                )"""
            )
            try:
                if state.globalGraph is not None:
                    state.globalGraph.centerOnNote(currentId)
            except (AttributeError, RuntimeError) as error:
                log("Unable to center the closing global graph window:", error)

    def appendJsToEditor(self, web_content, context):
        """Enable the editor to support shortcut keys and double-click nid trigger operations"""
        if not isinstance(context, Editor):
            return
        web_content.head += f'<script src="{getWebFileLink("js/detectClick.js")}"></script>'
