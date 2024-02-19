"""
MIT License
Copyright (c) 2024 Wang Rui (https://github.com/gugutu)
"""
import json
import operator
from typing import Set, Optional
import uuid

import anki
from anki import notetypes_pb2
from anki.models import StockNotetype
from anki.cards import Card
from anki.notes import Note, NoteId
from anki.collection import OpChanges
from aqt import gui_hooks
from aqt.browser import Browser
from aqt.editor import Editor, EditorWebView, EditorMode
from aqt.utils import *
from aqt.webview import AnkiWebView
from aqt import mw

from .translation import getTr
from .editors import MyAddCards, MyEditCurrent
from .state import Connection, JsNoteNode, NoteNode


def log(*args):
    debug = 0
    if debug:
        print(*args)


config = mw.addonManager.getConfig(__name__)
addon_path = os.path.dirname(__file__)
page_html = open(os.path.join(addon_path, 'page.html'), 'r').read()
force_graph_js = open(os.path.join(addon_path, 'force-graph.js'), 'r').read()
d3_js = open(os.path.join(addon_path, 'd3.js'), 'r').read()


class AnkiPlugin(object):
    def __init__(self):
        self.editors: Set[Editor] = set()
        self.noteCache: dict[int, NoteNode] = {}
        self.linkCache: list[Connection] = []

        gui_hooks.webview_did_receive_js_message.append(self.handlePycmd)
        gui_hooks.card_will_show.append(self.convertLink)
        gui_hooks.editor_did_init.append(self.injectPage)
        gui_hooks.editor_did_init_buttons.append(self.injectButton)
        gui_hooks.editor_did_load_note.append(self.onLoadNote)
        gui_hooks.collection_did_load.append(lambda o: self.rebuildCache())
        gui_hooks.editor_did_fire_typing_timer.append(self.onEditNote)
        gui_hooks.webview_will_set_content.append(self.appendJsToEditor)
        gui_hooks.operation_did_execute.append(self.onOpChange)
        gui_hooks.browser_will_show_context_menu.append(self.addTableMenu)
        gui_hooks.editor_will_show_context_menu.append(self.addEditorMenu)

    def addEditorMenu(self, editorWebView: EditorWebView, menu: QMenu):
        copyNidAction = QAction(editorWebView)
        copyNidAction.setText(getTr("Copy note ID"))
        qconnect(
            copyNidAction.triggered,
            lambda _, e=editorWebView: QApplication.clipboard().setText(str(e.editor.note.id))
        )
        menu.addAction(copyNidAction)
        copyLinkAction = QAction(editorWebView)
        copyLinkAction.setText(getTr("Copy note link"))
        qconnect(
            copyLinkAction.triggered,
            lambda _, e=editorWebView: QApplication.clipboard().setText('[]{nid' + str(e.editor.note.id) + '}')
        )
        menu.addAction(copyLinkAction)
        openNoteAtNewWindowAction = QAction(editorWebView)
        openNoteAtNewWindowAction.setText(getTr("Open note in new window"))
        qconnect(
            openNoteAtNewWindowAction.triggered,
            lambda _, e=editorWebView: self.handlePycmd((True, None), 'rnid' + str(e.editor.note.id), e.editor)
        )
        menu.addAction(openNoteAtNewWindowAction)

    def addTableMenu(self, browser: Browser, menu: QMenu):
        copyNidAction = QAction(browser)
        copyNidAction.setText(getTr("Copy note ID"))
        qconnect(
            copyNidAction.triggered,
            lambda _, b=browser: self.tableMenuAction(b, 'copyNidAction')
        )
        menu.addAction(copyNidAction)
        copyLinkAction = QAction(browser)
        copyLinkAction.setText(getTr("Copy note link"))
        qconnect(
            copyLinkAction.triggered,
            lambda _, b=browser: self.tableMenuAction(b, 'copyLinkAction')
        )
        menu.addAction(copyLinkAction)
        openNoteInNewWindowAction = QAction(browser)
        openNoteInNewWindowAction.setText(getTr("Open note in new window"))
        qconnect(
            openNoteInNewWindowAction.triggered,
            lambda _, b=browser: self.tableMenuAction(b, 'openNoteInNewWindowAction')
        )
        menu.addAction(openNoteInNewWindowAction)

    def tableMenuAction(self, browser: Browser, actionName: str):
        if browser.card is None:
            tooltip(getTr("Please select a single note/card"))
            return
        if actionName == 'copyNidAction':
            QApplication.clipboard().setText(str(browser.card.nid))
        elif actionName == 'copyLinkAction':
            QApplication.clipboard().setText('[|nid' + str(browser.card.nid) + ']')
        elif actionName == 'openNoteInNewWindowAction':
            self.handlePycmd((True, None), 'rnid' + str(browser.card.nid), browser)

    def convertLink(self, text: str, card: Card, kind: str):
        """Convert note links to HTML hyperlinks"""
        return (re.sub(r'\[((?:[^\[]|\\\[)*?)\|(nid\d{13})\]',
                       r'<a onclick="javascript:pycmd(`r`+`\2`);" style="cursor: pointer">\1</a>', text)
                .replace('\\[', '['))

    def injectPage(self, editor: Editor):
        if editor.addMode:
            return
        self.editors.add(editor)
        editor.linksPage = AnkiWebView(title="links_page")
        editor.linksPage.setHtml(
            f'<script>\n{d3_js}{force_graph_js}\n const ankiLanguage = "{anki.lang.current_lang}";</script>{page_html}')
        editor.linksPage.set_bridge_command(lambda s: s, editor)

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
        split = QSplitter()

        if location == "left":
            split.setOrientation(Qt.Orientation.Horizontal)
            split.addWidget(editor.linksPage)
            split.addWidget(wrappedWeb)
            sizes = [editorR, mainR]
        elif location == "right":
            split.setOrientation(Qt.Orientation.Horizontal)
            split.addWidget(wrappedWeb)
            split.addWidget(editor.linksPage)
            sizes = [mainR, editorR]
        else:
            raise ValueError("Invalid value for config key location")

        split.setSizes(sizes)
        layout.insertWidget(web_index, split)
        if not config['showLinksPageAutomatically']:
            editor.linksPage.hide()

    def injectButton(self, buttons: list[str], editor: Editor):
        if editor.addMode:
            return

        icons_dir = os.path.join(addon_path, "icons")
        b = editor.addButton(
            icon=os.path.join(icons_dir, "show.svg"),
            cmd="_editor_toggle_links",
            tip=getTr("Show/Hide Link Page"),
            func=lambda e: e.linksPage.show() if e.linksPage.isHidden() else e.linksPage.hide(),
            disables=False,
        )
        buttons.append(b)

    def onLoadNote(self, editor: Editor):
        self.editors = set(filter(lambda it: it.note is not None, self.editors))
        log('-----reFlash page: loaded note')
        # log(json.dumps(editor.note.note_type(), default=lambda o: o.__dict__, indent = 4))
        self.reFlashPage(editor, resetCenter=True)

    def onEditNote(self, note: Note):
        if not self.updateNodeCache(note):
            log('-----jumped reFlashing page: links or titel not changed')
            return
        for editor in self.editors:
            log('-----reFlash page: note edited', editor)
            self.reFlashPage(editor)

    def onOpChange(self, changes: OpChanges, handler: Optional[object]):
        # self.printChanges(changes)
        if changes.study_queues or changes.notetype:
            log('-----rebuild cache: note(s) added/removed or notetype changed')
            self.rebuildCache()
            for editor in self.editors:
                log('-----reFlash page: note(s) added/removed or notetype changed', editor)
                self.reFlashPage(editor)

    def reFlashPage(self, editor: Editor, resetCenter: bool = False):
        if editor.note is None:
            return
        if editor.addMode:
            return
        currentId = int(editor.note.id)
        currentNode = self.noteCache[currentId]
        allIds = currentNode.parentIds + currentNode.childIds + [currentId]

        parentNodes: set[NoteNode] = set()
        childNodes: list[NoteNode] = []
        parentJsNodes: list[JsNoteNode] = []
        childJsNodes: list[JsNoteNode] = []
        duplicatedJsNodes: set[JsNoteNode] = set()

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
                duplicatedJsNodes.add(jsNode)

        allNodes = parentNodes | set(childNodes) | {currentNode}
        allJsNodes = parentJsNodes + [x for x in childJsNodes if x not in duplicatedJsNodes] + [
            currentNode.toJsNoteNode('me')]

        allConnections: list[Connection] = []
        for parentNode in allNodes:
            for childId in parentNode.childIds:
                if childId in allIds:
                    allConnections.append(Connection(parentNode.id, childId))

        editor.linksPage.eval(
            f'''reloadPage(
                {json.dumps(parentJsNodes, default=lambda o: o.__dict__)},
                {json.dumps(childJsNodes, default=lambda o: o.__dict__)},
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
            document.addEventListener("keydown", function(event) {
              if (event.altKey && event.key === "k") {
                  event.preventDefault();
                  pycmd(`insertLinkWithPlaceholder`);
              }else if (event.altKey && event.key === "j"){
                  event.preventDefault();
                  pycmd(`insertLink`);
              }
            });
            </script>
            """
        web_content.head += script_str

    def _findChildIds(self, myId, joinedFields: str):
        idSet = set()  # Used to remove duplicates
        idList: list[int] = []
        matches = re.findall(r'nid\d{13}', joinedFields)
        if matches:
            for match in matches:
                childId = int(match[3:])
                if myId != childId and childId not in idSet:  # Shield self ring connection and remove duplicates
                    idSet.add(childId)
                    idList.append(childId)
        return idList

    def rebuildCache(self):
        self.noteCache = {}
        self.linkCache = []
        for noteId in aqt.mw.col.find_notes(''):
            note = aqt.mw.col.get_note(noteId)
            self.updateNodeCache(note)

    def updateNodeCache(self, note: Note) -> bool:
        """Set the node for the note link, return False to indicate that there is no need to modify the node"""
        noteId = int(note.id)
        childIds = self._findChildIds(noteId, ' '.join(note.fields))
        oldChildIds = set()
        mainField = self.getMainField(note)
        # Set the forward link
        if noteId in self.noteCache:  # If the node already exists
            node = self.noteCache[noteId]  # Get the current node's information in the cache
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
            self.linkCache.append(Connection(noteId, childId))
        return True

    def getMainField(self, note: Note) -> str:
        """If it is an image occlusion type, return its "Title" field; otherwise, return the first field"""
        if note.note_type().get("originalStockKind",
                                None) == StockNotetype.OriginalStockKind.ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION:
            for flds in note.note_type()['flds']:
                if flds['tag'] == notetypes_pb2.IMAGE_OCCLUSION_FIELD_HEADER:
                    return note.fields[flds['ord']]
        else:
            return note.fields[0]

    def handlePycmd(self, handled: tuple[bool, Any], message: str, context: Any):
        """Handling web js events"""
        if re.match(r'lnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            editor: Editor = context
            if editor.editorMode == EditorMode.BROWSER:
                browser: Browser = aqt.dialogs.open('Browser', aqt.mw)
                browser.activateWindow()
                browser.editor.set_note(aqt.mw.col.get_note(NoteId(nid)), focusTo=0)
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
            ed = MyEditCurrent(NoteId(nid))
            ed.activateWindow()
            return True, None
        elif re.match(r'mnid\d{13}', message):
            nid = int(message[4:])
            if len(aqt.mw.col.find_notes(f'nid:{nid}')) == 0:
                tooltip(getTr('The corresponding note does not exist'))
                return True, None
            browser: Browser = aqt.dialogs.open('Browser', aqt.mw)
            browser.activateWindow()
            browser.editor.set_note(aqt.mw.col.get_note(NoteId(nid)), focusTo=0)
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
            if note.note_type().get("originalStockKind",
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
            text = editor.web.selectedText().replace('[', '\\[')
            placeholder = str(uuid.uuid4().int)[0:8]
            editor.doPaste(f'[{text}|new{placeholder}]', True)
            return True, None
        elif message == 'insertLink':
            editor: Editor = context
            text = editor.web.selectedText().replace('[', '\\[')
            editor.doPaste(f'[{text}|nid]', True)
            return True, None
        else:
            return handled

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


AnkiPlugin()
