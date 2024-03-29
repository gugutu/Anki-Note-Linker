"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import json
import operator
import uuid
from typing import Set, Optional

import anki
from anki import notetypes_pb2
from anki.cards import Card
from anki.collection import OpChanges
from anki.notes import Note, NoteId
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.browser.previewer import BrowserPreviewer
from aqt.editor import Editor, EditorWebView, EditorMode
from aqt.operations import QueryOp
from aqt.utils import *
from aqt.webview import AnkiWebView

oldVersion = False
try:
    from anki.models import StockNotetype
except ImportError:
    oldVersion = True

from .editors import MyAddCards, MyEditCurrent
from .state import Connection, JsNoteNode, NoteNode, GlobalGraph, addon_path, log, config, translation_js, links_html, \
    linkMaxLines, d3_js, force_graph_js, graph_html, PreviewState
from .translation import getTr


class AnkiNoteLinker(object):
    def __init__(self):
        self.jumpRebuildCacheCount = 0
        self.editors: Set[Editor] = set()
        self.noteCache: dict[int, NoteNode] = {}

        gui_hooks.webview_did_receive_js_message.append(self.handlePycmd)
        gui_hooks.card_will_show.append(self.convertLink)
        gui_hooks.editor_did_init.append(self.injectPage)
        gui_hooks.editor_did_init_buttons.append(self.injectButton)
        gui_hooks.editor_did_load_note.append(self.onLoadNote)
        gui_hooks.collection_did_load.append(lambda o: self.rebuildCache())
        gui_hooks.editor_did_fire_typing_timer.append(self.onEditNote)
        gui_hooks.webview_will_set_content.append(self.appendJsToEditor)
        gui_hooks.operation_did_execute.append(self.onOpChange)
        gui_hooks.browser_will_show_context_menu.append(self.injectRightClickMenu)
        gui_hooks.editor_will_show_context_menu.append(self.injectRightClickMenu)
        gui_hooks.add_cards_did_add_note.append(self.onNoteAdded)

        def cleanUpEditor(editor):
            self.editors.discard(editor)
            if hasattr(editor, "linksPage") and editor.linksPage:
                editor.linksPage.cleanup()
                editor.linksPage.close()
            if hasattr(editor, "graphPage") and editor.graphPage:
                editor.graphPage.cleanup()
                editor.graphPage.close()

        Editor.cleanup = anki.hooks.wrap(Editor.cleanup, cleanUpEditor)

        openGlobalGraphAction = QAction(mw.form.menuTools)
        openGlobalGraphAction.setText(getTr("Global Relationship Graph (Experimental)"))
        qconnect(openGlobalGraphAction.triggered, lambda _: self.openGlobalGraph())
        mw.form.menuTools.addAction(openGlobalGraphAction)

    def injectRightClickMenu(self, context, menu: QMenu):
        if isinstance(context, EditorWebView):
            if context.editor.currentField is not None:
                menu.addSeparator()
                insertLinkWithClipboardIDAction = QAction(context)
                insertLinkWithClipboardIDAction.setText(getTr("Insert link with copied note ID"))
                insertLinkWithClipboardIDAction.setShortcut(config['shortcuts']['insertLinkWithClipboardID'])
                qconnect(insertLinkWithClipboardIDAction.triggered,
                         lambda _, c=context: self.insertLinkWithClipboardID(c.editor))
                menu.addAction(insertLinkWithClipboardIDAction)

                insertNewLinkAction = QAction(context)
                insertNewLinkAction.setText(getTr("Insert new link"))
                insertNewLinkAction.setShortcut(config['shortcuts']['insertNewLink'])
                qconnect(insertNewLinkAction.triggered, lambda _, c=context: self.insertNewLink(c.editor))
                menu.addAction(insertNewLinkAction)

                insertLinkTemplateAction = QAction(context)
                insertLinkTemplateAction.setText(getTr("Insert link template"))
                insertLinkTemplateAction.setShortcut(config['shortcuts']['insertLinkTemplate'])
                qconnect(insertLinkTemplateAction.triggered, lambda _, c=context: self.insertLinkTemplate(c.editor))
                menu.addAction(insertLinkTemplateAction)
                menu.addSeparator()
            if context.editor.addMode:
                return
        menu.addSeparator()
        copyNoteIdAction = QAction(context)
        copyNoteIdAction.setText(getTr("Copy note ID"))
        copyNoteIdAction.setShortcut(config['shortcuts']['copyNoteID'])
        qconnect(copyNoteIdAction.triggered, lambda _, c=context: self.copyNoteID(c))
        menu.addAction(copyNoteIdAction)

        copyNoteLinkAction = QAction(context)
        copyNoteLinkAction.setText(getTr("Copy note link"))
        copyNoteLinkAction.setShortcut(config['shortcuts']['copyNoteLink'])
        qconnect(copyNoteLinkAction.triggered, lambda _, c=context: self.copyNoteLink(c))
        menu.addAction(copyNoteLinkAction)

        openNoteInNewWindowAction = QAction(context)
        openNoteInNewWindowAction.setText(getTr("Open note in new window"))
        openNoteInNewWindowAction.setShortcut(config['shortcuts']['openNoteInNewWindow'])
        qconnect(openNoteInNewWindowAction.triggered, lambda _, c=context: self.openNoteInNewWindow(c))
        menu.addAction(openNoteInNewWindowAction)
        menu.addSeparator()

    def injectShortcuts(self, web: EditorWebView):
        QShortcut(QKeySequence(config['shortcuts']['insertLinkWithClipboardID']), web,
                  lambda: self.insertLinkWithClipboardID(web.editor))
        QShortcut(QKeySequence(config['shortcuts']['insertNewLink']), web, lambda: self.insertNewLink(web.editor))
        QShortcut(QKeySequence(config['shortcuts']['insertLinkTemplate']), web,
                  lambda: self.insertLinkTemplate(web.editor))
        if not web.editor.addMode:
            QShortcut(QKeySequence(config['shortcuts']['copyNoteID']), web, lambda: self.copyNoteID(web))
            QShortcut(QKeySequence(config['shortcuts']['copyNoteLink']), web, lambda: self.copyNoteLink(web))
            QShortcut(QKeySequence(config['shortcuts']['openNoteInNewWindow']), web,
                      lambda: self.openNoteInNewWindow(web))

    def convertLink(self, text: str, card: Card, kind: str):
        """Convert note links to HTML hyperlinks, set add-on active flag"""
        return (
                '<script>AnkiNoteLinkerIsActive = true;</script>' +
                re.sub(
                    r'\[((?:[^\[]|\\\[)*?)\|(nid\d{13})\]',
                    lambda
                        match: f'<a onclick="pycmd(`r`+`{match.group(2)}`);" oncontextmenu="event.preventDefault();pycmd(`p`+`{match.group(2)}`);" style="cursor: pointer">' +
                               match.group(1).replace('\\[', '[') + '</a>', text
                )
        )

    def injectLinksPage(self, editor: Editor):
        editor.linksPage = AnkiWebView(parent=editor.innerSplitter, title="links_page")
        editor.linksPage.set_bridge_command(lambda s: s, editor)
        editor.linksPage.stdHtml(
            f'<script>{translation_js}\n const ankiLanguage = "{anki.lang.current_lang}";</script>' +
            r'<style>.link-button-text{-webkit-line-clamp: ' + linkMaxLines + '; line-clamp: ' + linkMaxLines + ';}</style>' +
            links_html
        )

    def injectGraphPage(self, editor: Editor):
        editor.graphPage = AnkiWebView(parent=editor.innerSplitter, title="graph_page")
        editor.graphPage.set_bridge_command(lambda s: s, editor)
        editor.graphPage.stdHtml(
            f'<script>\n{d3_js}{force_graph_js}{translation_js}\n const ankiLanguage = "{anki.lang.current_lang}";</script>' +
            graph_html
        )

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
                self.refreshPage(e, reason='toggleLinksPage')

        def toggleGraphPage(e: Editor):
            if hasattr(e, 'graphPage'):
                if e.graphPage.isHidden():
                    e.innerSplitter.show()
                    e.graphPage.show()
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
                self.refreshPage(e, reason='toggleGraphPage')

        icons_dir = os.path.join(addon_path, "icons")
        toggleLinksPageButton = editor.addButton(
            icon=os.path.join(icons_dir, "showLinksPage.svg"),
            cmd="_editor_toggle_links",
            tip=getTr("Toggle Links Page"),
            func=toggleLinksPage,
            disables=False,
        )
        toggleGraphPageButton = editor.addButton(
            icon=os.path.join(icons_dir, "showGraphPage.svg"),
            cmd="_editor_toggle_graph",
            tip=getTr("Toggle Graph Page"),
            func=toggleGraphPage,
            disables=False,
        )
        buttons.append(toggleLinksPageButton)
        buttons.append(toggleGraphPageButton)

    def onLoadNote(self, editor: Editor):
        self.editors = set(filter(lambda it: it.note is not None, self.editors))
        if editor.addMode:
            return
        self.editors.add(editor)
        # log(json.dumps(editor.note.note_type(), default=lambda o: o.__dict__, indent = 4))
        self.refreshPage(editor, resetCenter=True, reason='loaded note')

    def onEditNote(self, note: Note):
        if note.id == 0:
            return
        if not self.updateNodeCache(note):
            return
        log('-----update cache: mainField or links of note changed')
        for editor in self.editors:
            self.refreshPage(editor, reason='mainField or links of note changed')
        if state.globalGraph is not None:
            state.globalGraph.refreshGlobalGraph()

    def onNoteAdded(self, note: Note):
        self.jumpRebuildCacheCount += 1
        log('-----update cache: note added')
        self.updateNodeCache(note)
        for editor in self.editors:
            self.refreshPage(editor, reason='note added')
        if state.globalGraph is not None:
            state.globalGraph.refreshGlobalGraph()

    def onOpChange(self, changes: OpChanges, handler: Optional[object]):
        # self.printChanges(changes)
        if changes.study_queues or changes.notetype:
            if self.jumpRebuildCacheCount > 0:
                self.jumpRebuildCacheCount -= 1
                return
            self.rebuildCache()

    def refreshPage(self, editor: Editor, resetCenter: bool = False, reason: str = ''):
        if editor.note is None or editor.addMode:
            return
        if not hasattr(editor, "linksPage") and not hasattr(editor, "graphPage"):
            return
        currentId = int(editor.note.id)
        if currentId in self.noteCache:
            currentNode = self.noteCache[currentId]
        else:
            return
        log(f'-----refresh page: {reason}, at', editor)
        allIds = currentNode.parentIds + currentNode.childIds + [currentId]

        parentNodes: set[NoteNode] = set()
        childNodes: list[NoteNode] = []
        parentJsNodes: list[JsNoteNode] = []
        childJsNodes: list[JsNoteNode] = []
        duplicatedJsNodeIds: set[int] = set()

        for parentId in currentNode.parentIds:
            parentNode = self.noteCache[parentId]
            parentNodes.add(parentNode)
            parentJsNodes.append(parentNode.toJsNoteNode('parent'))

        for childId in currentNode.childIds:
            childNode = self.noteCache[childId]
            childNodes.append(childNode)
            jsNode = childNode.toJsNoteNode('child')
            childJsNodes.append(jsNode)
            if childNode in parentNodes:  # When a node is both a parent node and a child node
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
        if hasattr(editor, "linksPage"):
            editor.linksPage.eval(
                f'''reloadPage(
                    {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                    {json.dumps(childJsNodes, default=lambda o: o.__dict__)}
                )'''
            )
        if hasattr(editor, "graphPage"):
            editor.graphPage.eval(
                f'''reloadPage(
                {json.dumps(allJsNodes, default=lambda o: o.__dict__)},
                {json.dumps(allConnections, default=lambda o: o.__dict__)},
                {json.dumps(resetCenter)}
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
                        pycmd('r'+st);
                    }else if (newreg.test(st)){
                        pycmd(st)
                    }
                }
            });
            document.addEventListener("keydown", function (event) {
                if (event.altKey && event.key.toLowerCase() === "k") {
                    event.preventDefault();
                    pycmd(`insertLinkWithPlaceholder`);
                } else if (event.altKey && event.key.toLowerCase() === "j") {
                    event.preventDefault();
                    pycmd(`insertLink`);
                } else if (event.altKey && event.key.toLowerCase() === "l") {
                    event.preventDefault();
                    pycmd(`insertLinkWithClipboardID`);
                }
            });
            </script>
            """
        web_content.head += script_str

    def _findChildIds(self, myId, joinedFields: str):
        idSet = set()  # Used to remove duplicates
        idList: list[int] = []
        matches = re.finditer(r'\[(?:[^\[]|\\\[)*?\|nid(\d{13})\]', joinedFields)
        if matches:
            for match in matches:
                childId = int(match.group(1))
                if myId != childId and childId not in idSet:  # Shield self ring connection and remove duplicates
                    idSet.add(childId)
                    idList.append(childId)
        return idList

    def rebuildCache(self):
        log('-----rebuild cache !!!')

        def op(col):
            self.noteCache = {}
            for noteId in col.find_notes(''):
                note = col.get_note(noteId)
                self.updateNodeCache(note)

        def onSuccess(p):
            for editor in self.editors:
                self.refreshPage(editor, reason='cache rebuild')
            if state.globalGraph is not None:
                state.globalGraph.refreshGlobalGraph()

        QueryOp(parent=None, op=op, success=onSuccess).run_in_background()

    def updateNodeCache(self, note: Note) -> bool:
        """Set the node for the note link, return False to indicate that there is no need to modify the node"""
        noteId = int(note.id)
        childIds = self._findChildIds(noteId, ' '.join(note.fields))
        oldChildIds = set()
        mainField = self.getMainField(note)
        # Set the forward link
        node = self.noteCache.get(noteId, None)  # Get the current node's information in the cache
        if node is not None:  # If the node already exists
            oldChildIds = node.childIds
            if node.mainField == mainField and operator.eq(oldChildIds, childIds):
                return False
            node.mainField = mainField  # Set the node's first field as the new main field
            node.childIds = childIds  # Update its forward link to the new childIds list
        else:
            # If the node doesn't exist, create a new NoteNode object and insert it into the cache
            self.noteCache[noteId] = NoteNode(noteId, childIds, [], mainField)

        # Remove the reverse link of old child nodes (need optimization: Operate only on nodes with changes)
        for id in oldChildIds:
            if id in self.noteCache:
                self.noteCache[id].parentIds.remove(noteId)

        # Set the back link of child nodes
        for childId in childIds:
            if childId in self.noteCache:  # If the node already exists
                childNode = self.noteCache[childId]  # Get the information of the forward-linked node in the cache
                if noteId not in childNode.parentIds:  # Prevent adding duplicate IDs
                    childNode.parentIds.append(noteId)  # Add the current node ID to its back link list
            else:
                # If the node doesn't exist, create a new NoteNode object and insert it into the cache
                self.noteCache[childId] = NoteNode(childId, [], [noteId], None)
        return True

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
        mainField = re.sub(r'\[((?:[^\[]|\\\[)*?)\|(nid\d{13})\]',
                           r'\1', mainField).replace('\\[', '[')
        # Clear Cloze Format
        pattern = r'\{\{c\d+?::((:?(?!\{\{c\d+?::).|\n)*?)\}\}'
        while re.search(pattern, mainField):
            mainField = re.sub(pattern, '[...]' if config['collapseClozeInLinksPage'] else r'\1', mainField)
        return mainField

    def handlePycmd(self, handled: tuple[bool, Any], message: str, context: Any):
        """Handling web js events"""
        if re.match(r'lnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            if isinstance(context, GlobalGraph):
                self.openNoteInNewWindow(context, nid)
                return True, None
            editor: Editor = context
            if editor.editorMode == EditorMode.BROWSER:
                self.openNoteInBrowser(context, nid)
            elif editor.editorMode == EditorMode.EDIT_CURRENT:
                editor.set_note(aqt.mw.col.get_note(NoteId(nid)), focusTo=0)
            elif editor.editorMode == EditorMode.ADD_CARDS:
                ed = MyEditCurrent(NoteId(nid))
                ed.activateWindow()
            return True, None
        elif re.match(r'rnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            if isinstance(context, GlobalGraph):
                self.openNoteInPreviewer(context, nid)
                return True, None
            self.openNoteInNewWindow(context, nid)
            return True, None
        elif re.match(r'mnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            self.openNoteInBrowser(context, nid)
            return True, None
        elif re.match(r'pnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            self.openNoteInPreviewer(context, nid)
            return True, None
        elif re.match(r'new\d{8}', message):
            placeholder = message[3:]
            editor: Editor = context
            if editor.addMode:
                tooltip(getTr('Please add the current note first'))
                return True, None
            match = re.search(r'\[((?:[^\[]|\\\[)*?)\|' + message + ']', editor.note.joined_fields())
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
        elif message == 'insertLinkWithPlaceholder':
            editor: Editor = context
            self.insertNewLink(editor)
            return True, None
        elif message == 'insertLinkWithClipboardID':
            editor: Editor = context
            self.insertLinkWithClipboardID(editor)
            return True, None
        elif message == 'insertLink':
            editor: Editor = context
            self.insertLinkTemplate(editor)
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

    def openNoteInNewWindow(self, context, nid=None):
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

    def openGlobalGraph(self):
        if state.globalGraph is None:
            state.globalGraph = GlobalGraph()
            state.globalGraph.refreshGlobalGraph()
        else:
            state.globalGraph.showNormal()
            state.globalGraph.activateWindow()


state.addon = AnkiNoteLinker()
