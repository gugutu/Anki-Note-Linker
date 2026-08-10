"""Editor context-menu, shortcut, link, and navigation actions."""

import importlib
import re
import uuid

import aqt
from anki.cards import Card
from anki.notes import NoteId
from aqt import QAction, QApplication, QKeySequence, QMenu, QShortcut, mw, qconnect
from aqt.browser import Browser
from aqt.browser.previewer import BrowserPreviewer
from aqt.editor import Editor, EditorWebView
from aqt.utils import tooltip

from ..core.links import NOTE_LINK_PATTERN, escape_title, format_new_link, format_note_link
from .configuration import config
from .editor_windows import MyEditCurrent
from .i18n import getTr
from .state import PreviewState


class EditorActionsMixin:
    def injectRightClickMenu(self, context, menu: QMenu):
        if isinstance(context, EditorWebView):
            if context.editor.currentField is not None:
                menu.addSeparator()
                insertLinkWithClipboardIDAction = QAction(context)
                insertLinkWithClipboardIDAction.setText(getTr("Insert link with copied note ID"))
                insertLinkWithClipboardIDAction.setShortcut(config["shortcuts-insertLinkWithClipboardID"])
                qconnect(
                    insertLinkWithClipboardIDAction.triggered,
                    lambda _, c=context: self.insertLinkWithClipboardID(c.editor),
                )
                menu.addAction(insertLinkWithClipboardIDAction)

                insertNewLinkAction = QAction(context)
                insertNewLinkAction.setText(getTr("Insert new link"))
                insertNewLinkAction.setShortcut(config["shortcuts-insertNewLink"])
                qconnect(insertNewLinkAction.triggered, lambda _, c=context: self.insertNewLink(c.editor))
                menu.addAction(insertNewLinkAction)

                insertLinkTemplateAction = QAction(context)
                insertLinkTemplateAction.setText(getTr("Insert link template"))
                insertLinkTemplateAction.setShortcut(config["shortcuts-insertLinkTemplate"])
                qconnect(insertLinkTemplateAction.triggered, lambda _, c=context: self.insertLinkTemplate(c.editor))
                menu.addAction(insertLinkTemplateAction)
                menu.addSeparator()
            if context.editor.addMode:
                return
        menu.addSeparator()
        copyNoteIdAction = QAction(context)
        copyNoteIdAction.setText(getTr("Copy current note ID"))
        copyNoteIdAction.setShortcut(config["shortcuts-copyNoteID"])
        qconnect(copyNoteIdAction.triggered, lambda _, c=context: self.copyNoteID(c))
        menu.addAction(copyNoteIdAction)

        copyNoteLinkAction = QAction(context)
        copyNoteLinkAction.setText(getTr("Copy current note link"))
        copyNoteLinkAction.setShortcut(config["shortcuts-copyNoteLink"])
        qconnect(copyNoteLinkAction.triggered, lambda _, c=context: self.copyNoteLink(c))
        menu.addAction(copyNoteLinkAction)

        openNoteInNewWindowAction = QAction(context)
        openNoteInNewWindowAction.setText(getTr("Open current note in new window"))
        openNoteInNewWindowAction.setShortcut(config["shortcuts-openNoteInNewWindow"])
        qconnect(openNoteInNewWindowAction.triggered, lambda _, c=context: self.openNoteInNewEditor(c))
        menu.addAction(openNoteInNewWindowAction)
        menu.addSeparator()

    def injectShortcuts(self, web: EditorWebView):
        QShortcut(
            QKeySequence(config["shortcuts-insertLinkWithClipboardID"]),
            web,
            lambda: self.insertLinkWithClipboardID(web.editor),
        )
        QShortcut(QKeySequence(config["shortcuts-insertNewLink"]), web, lambda: self.insertNewLink(web.editor))
        QShortcut(
            QKeySequence(config["shortcuts-insertLinkTemplate"]), web, lambda: self.insertLinkTemplate(web.editor)
        )
        if not web.editor.addMode:
            QShortcut(QKeySequence(config["shortcuts-copyNoteID"]), web, lambda: self.copyNoteID(web))
            QShortcut(QKeySequence(config["shortcuts-copyNoteLink"]), web, lambda: self.copyNoteLink(web))
            QShortcut(QKeySequence(config["shortcuts-openNoteInNewWindow"]), web, lambda: self.openNoteInNewEditor(web))

    def convertLink(self, text: str, card: Card, kind: str):
        """Convert note links to HTML hyperlinks, set add-on active flag"""
        return "<script>window.AnkiNoteLinkerIsActive = true</script>" + NOTE_LINK_PATTERN.sub(
            lambda match: f'<a class="noteLink" href="javascript:pycmd(`AnkiNoteLinker-openNoteInPreviewer`+`{match.group(2)}`)" '
            f'oncontextmenu="event.preventDefault();pycmd(`AnkiNoteLinker-openNoteInNewEditor`+`{match.group(2)}`)">'
            + match.group(1).replace("\\[", "[")
            + "</a>",
            text,
        )

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
            tooltip(getTr("Copied note ID"))

    def copyNoteLink(self, context):
        nid = self._getNoteIDFromContext(context)
        if nid is not None:
            QApplication.clipboard().setText(format_note_link(int(nid)))
            tooltip(getTr("Copied note link"))

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
                hjp = importlib.import_module("1420819673")
                previewer = hjp.lib.common_tools.funcs.MonkeyPatch.BrowserPreviewer(
                    previewState,
                    mw,
                    previewState.cleanUpState,
                )
            except Exception:
                previewer: BrowserPreviewer = BrowserPreviewer(previewState, mw, previewState.cleanUpState)
            previewState.setPreviewer(previewer)
            previewer.open()

    def openNoteInBrowser(self, context, nid=None):
        if nid is None:
            nid = self._getNoteIDFromContext(context)
        if nid is not None:
            browser: Browser = aqt.dialogs.open("Browser", aqt.mw)
            browser.activateWindow()

            card = aqt.mw.col.get_note(NoteId(nid)).cards()[0]
            browser.table.select_single_card(card.id)
            if not browser.table.has_current():
                browser.search_for('"deck:' + aqt.mw.col.decks.get(card.did)["name"] + '"')
                browser.table.select_single_card(card.id)

    def insertLinkTemplate(self, editor: Editor):
        text = escape_title(editor.web.selectedText())
        editor.doPaste(f"[{text}|nid]", True)

    def insertLinkWithClipboardID(self, editor: Editor):
        text = editor.web.selectedText()
        idText = QApplication.clipboard().text()
        if re.fullmatch(r"\d{13}", idText):
            editor.doPaste(format_note_link(int(idText), text), True)
        else:
            tooltip(getTr("The content in the clipboard is not a note ID"))

    def insertNewLink(self, editor: Editor):
        text = editor.web.selectedText()
        placeholder = str(uuid.uuid4().int)[0:8]
        editor.doPaste(format_new_link(placeholder, text), True)
