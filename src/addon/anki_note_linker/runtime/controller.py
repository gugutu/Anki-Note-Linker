"""Register Anki hooks and compose the add-on's runtime controllers."""

from typing import Optional, Set

from aqt import QAction, QMenu, gui_hooks, mw, qconnect
from aqt.editor import Editor

from . import state
from .bridge import BridgeMixin
from .configuration import ConfigView
from .editor_actions import EditorActionsMixin
from .editor_panels import EditorPanelsMixin
from .global_graph import GlobalGraph
from .i18n import getTr
from .notes import NoteServiceMixin
from .reviewer import ReviewerMixin


class AnkiNoteLinker(
    ReviewerMixin,
    EditorActionsMixin,
    EditorPanelsMixin,
    NoteServiceMixin,
    BridgeMixin,
):
    """Coordinate hooks while delegating behavior to focused mixins."""

    def __init__(self) -> None:
        self.editors: Set[Editor] = set()
        self._register_hooks()
        self._add_menu()

    def _register_hooks(self) -> None:
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
        profile_will_close = getattr(gui_hooks, "profile_will_close", None)
        if profile_will_close is not None:
            profile_will_close.append(self.onProfileWillClose)

    def _add_menu(self) -> None:
        menu = QMenu("Anki Note Linker", mw.form.menubar)
        graph_action = QAction(menu)
        graph_action.setMenuRole(QAction.MenuRole.NoRole)
        graph_action.setText(getTr("Global Relationship Graph"))
        qconnect(graph_action.triggered, lambda _checked: self.openGlobalGraph())
        menu.addAction(graph_action)

        config_action = QAction(menu)
        config_action.setMenuRole(QAction.MenuRole.NoRole)
        config_action.setText(getTr("Config"))
        qconnect(config_action.triggered, lambda _checked: ConfigView.openConfigView())
        menu.addAction(config_action)
        mw.form.menubar.addMenu(menu)

    def openGlobalGraph(self) -> None:
        if state.globalGraph is None:
            state.globalGraph = GlobalGraph()
        else:
            state.globalGraph.showNormal()
            state.globalGraph.activateWindow()


_addon: Optional[AnkiNoteLinker] = None


def initialize() -> AnkiNoteLinker:
    """Initialize the add-on once and return its controller."""
    global _addon
    if _addon is None:
        _addon = AnkiNoteLinker()
        state.addon = _addon
    return _addon
