"""Reviewer panel lifecycle, layout, and data refresh behavior."""

import json

from anki.cards import Card
from anki.notes import NoteId
from aqt import QAction, QMenu, QSplitter, Qt, QVBoxLayout, QWidget, mw, qconnect
from aqt.main import MainWindowState
from aqt.reviewer import Reviewer
from aqt.webview import AnkiWebView

from . import state
from .configuration import ConfigView, config
from .i18n import getTr
from .lifecycle import cleanup_webview
from .state import Connection, JsNoteNode, NoteNode, log
from .web_pages import links_page, new_graph_page


class ReviewerMixin:
    def onStateChange(self, newState: MainWindowState, oldState: MainWindowState):
        if newState == "review":
            self.onToggleReviewerLinksPanel(config["showLinksPageInReviewerAutomatically"])
            self.onToggleReviewerGraphPanel(config["showGraphPageInReviewerAutomatically"])

    def onProfileWillClose(self):
        if state.globalGraph is not None:
            state.globalGraph.close()
        if ConfigView.configView is not None:
            ConfigView.configView.close()
        self.onReviewerEnd()

    def onReviewerEnd(self):
        mw.reviewer.showLinksPage = False
        mw.reviewer.showGraphPage = False
        if hasattr(mw.reviewer, "linksPageSplitter"):
            linksPageSplitter = mw.reviewer.linksPageSplitter
            mw.setCentralWidget(mw.mwWidget)
            mw.mwWidget.setParent(mw)
            linksPageSplitter.deleteLater()
            del mw.reviewer.linksPageSplitter
        cleanup_webview(mw.reviewer, "linksPage")
        if hasattr(mw.reviewer, "linksPage"):
            del mw.reviewer.linksPage
        cleanup_webview(mw.reviewer, "graphPage")
        if hasattr(mw.reviewer, "graphPage"):
            del mw.reviewer.graphPage
        if hasattr(mw.reviewer, "panelSplitter"):
            del mw.reviewer.panelSplitter

    def onToggleReviewerLinksPanel(self, checked: bool):
        mw.reviewer.showLinksPage = checked
        if checked or (hasattr(mw.reviewer, "showGraphPage") and mw.reviewer.showGraphPage):
            self.injectReviewerPanelsToMainWindow()
            self.ensureReviewerLinksPage()
        self.updateReviewerPanelVisibility()
        if checked:
            self.refreshReviewerPanel(mw.reviewer.card, waitingForShowAnswer=mw.reviewer.state != "answer")

    def onToggleReviewerGraphPanel(self, checked: bool):
        mw.reviewer.showGraphPage = checked
        if checked or (hasattr(mw.reviewer, "showLinksPage") and mw.reviewer.showLinksPage):
            self.injectReviewerPanelsToMainWindow()
            self.ensureReviewerGraphPage()
        self.updateReviewerPanelVisibility()
        if checked:
            self.refreshReviewerPanel(mw.reviewer.card, waitingForShowAnswer=mw.reviewer.state != "answer")

    def injectContextMenuToReviewer(self, reviewer: Reviewer, menu: QMenu):
        toggleLinksAction = QAction(menu)
        toggleLinksAction.setText(getTr("Show Links Panel"))
        toggleLinksAction.setCheckable(True)
        toggleLinksAction.setChecked(getattr(reviewer, "showLinksPage", False))

        toggleGraphAction = QAction(menu)
        toggleGraphAction.setText(getTr("Show Graph Panel"))
        toggleGraphAction.setCheckable(True)
        toggleGraphAction.setChecked(getattr(reviewer, "showGraphPage", False))

        qconnect(toggleLinksAction.triggered, self.onToggleReviewerLinksPanel)
        qconnect(toggleGraphAction.triggered, self.onToggleReviewerGraphPanel)
        menu.addSeparator()
        menu.addAction(toggleLinksAction)
        menu.addAction(toggleGraphAction)
        menu.addSeparator()

    def refreshReviewerPanel(self, card: Card, waitingForShowAnswer=False):
        if not hasattr(mw.reviewer, "linksPage") and not hasattr(mw.reviewer, "graphPage"):
            return
        links_show = getattr(mw.reviewer, "showLinksPage", False)
        graph_show = getattr(mw.reviewer, "showGraphPage", False)
        if links_show or graph_show:
            log("-----refresh reviewer panel")
            if waitingForShowAnswer:
                if links_show and hasattr(mw.reviewer, "linksPage"):
                    mw.reviewer.linksPage.eval(
                        f"reloadPage([], [], waitingForShowAnswer = true, {json.dumps(config['showForwardLinkTitleInLinksPage'])})"
                    )
                if graph_show and hasattr(mw.reviewer, "graphPage"):
                    mw.reviewer.graphPage.eval("reloadPage([], [], false, false)")
                return

            currentNode = self.noteToNoteNode(card.note())
            showForwardLinkTitle = config["showForwardLinkTitleInLinksPage"]
            childLinkTitles = (
                self.findChildLinkTitles(currentNode.id, " ".join(card.note().fields)) if showForwardLinkTitle else {}
            )
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

            if links_show and hasattr(mw.reviewer, "linksPage"):
                mw.reviewer.linksPage.eval(
                    f"""reloadPage(
                                {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                                {json.dumps(childJsNodes, default=lambda o: o.__dict__)},
                                false,
                                {json.dumps(config["showForwardLinkTitleInLinksPage"])}
                            )"""
                )

            if graph_show and hasattr(mw.reviewer, "graphPage"):
                allNodes = parentNodes | set(childNodes) | {currentNode}
                allJsNodes = (
                    childJsNodes
                    + [x for x in parentJsNodes if x.id not in duplicatedJsNodeIds]
                    + [currentNode.toJsNoteNode("me")]
                )
                allIds = currentNode.parentIds | set(currentNode.childIds) | {currentNode.id}
                allConnections: list[Connection] = []
                for parentNode in allNodes:
                    for childId in parentNode.childIds:
                        if childId in allIds:
                            allConnections.append(Connection(parentNode.id, childId))
                mw.reviewer.graphPage.eval(
                    f"""reloadPage(
                    {json.dumps(allJsNodes, default=lambda o: o.__dict__)},
                    {json.dumps(allConnections, default=lambda o: o.__dict__)},
                    {json.dumps(True)},
                    {json.dumps(True)}
                    )"""
                )
            try:
                if state.globalGraph is not None:
                    state.globalGraph.centerOnNote(card.note().id)
            except (AttributeError, RuntimeError) as error:
                log("Unable to center the closing global graph window:", error)

    def injectReviewerPanelsToMainWindow(self):
        if hasattr(mw.reviewer, "linksPageSplitter"):
            return
        mw.reviewer.linksPageSplitter = QSplitter()
        mw.reviewer.panelSplitter = QSplitter()
        mw.reviewer.panelSplitter.setOrientation(Qt.Orientation.Vertical)
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
            mw.reviewer.panelSplitter.setContentsMargins(10, 0, 0, 0)
            mw.reviewer.linksPageSplitter.setOrientation(Qt.Orientation.Horizontal)
            mw.reviewer.linksPageSplitter.addWidget(mw.reviewer.panelSplitter)
            mw.reviewer.linksPageSplitter.addWidget(wrappedMwWidget)
            sizes = [panelR, mwR]
        elif location == "right":
            mw.reviewer.panelSplitter.setContentsMargins(0, 0, 10, 0)
            mw.reviewer.linksPageSplitter.setOrientation(Qt.Orientation.Horizontal)
            mw.reviewer.linksPageSplitter.addWidget(wrappedMwWidget)
            mw.reviewer.linksPageSplitter.addWidget(mw.reviewer.panelSplitter)
            sizes = [mwR, panelR]
        else:
            raise ValueError("Invalid value for config key location")

        mw.reviewer.linksPageSplitter.setSizes(sizes)
        mw.setCentralWidget(mw.reviewer.linksPageSplitter)

    def ensureReviewerLinksPage(self):
        if hasattr(mw.reviewer, "linksPage"):
            return
        mw.reviewer.linksPage = AnkiWebView(parent=mw.reviewer.panelSplitter, title="links_page")
        mw.reviewer.linksPage.set_bridge_command(lambda s: s, mw.reviewer.linksPage)
        mw.reviewer.linksPage.stdHtml(links_page("REVIEWER"))
        mw.reviewer.panelSplitter.addWidget(mw.reviewer.linksPage)

    def ensureReviewerGraphPage(self):
        if hasattr(mw.reviewer, "graphPage"):
            return
        mw.reviewer.graphPage = AnkiWebView(parent=mw.reviewer.panelSplitter, title="graph_page")
        mw.reviewer.graphPage.set_bridge_command(lambda s: s, mw.reviewer.graphPage)
        mw.reviewer.graphPage.stdHtml(new_graph_page("REVIEWER"))
        mw.reviewer.panelSplitter.addWidget(mw.reviewer.graphPage)

    def updateReviewerPanelVisibility(self):
        if not hasattr(mw.reviewer, "panelSplitter"):
            return
        linksShow = getattr(mw.reviewer, "showLinksPage", False)
        graphShow = getattr(mw.reviewer, "showGraphPage", False)
        if linksShow and hasattr(mw.reviewer, "linksPage"):
            mw.reviewer.linksPage.show()
        elif hasattr(mw.reviewer, "linksPage"):
            mw.reviewer.linksPage.hide()
        if graphShow and hasattr(mw.reviewer, "graphPage"):
            mw.reviewer.graphPage.show()
        elif hasattr(mw.reviewer, "graphPage"):
            mw.reviewer.graphPage.hide()

        if linksShow and graphShow and hasattr(mw.reviewer, "linksPage") and hasattr(mw.reviewer, "graphPage"):
            topR, bottomR = [int(r) * 10000 for r in config["splitRatioBetweenLinksPageAndGraphPage"].split(":")]
            mw.reviewer.panelSplitter.setSizes([topR, bottomR])

        if linksShow or graphShow:
            mw.reviewer.panelSplitter.show()
        else:
            mw.reviewer.panelSplitter.hide()
