import aqt

from aqt import QMainWindow, QDialogButtonBox, QPushButton, QKeySequence, QShortcut, Qt
from anki.collection import OpChanges
from anki.notes import Note, NoteId
from aqt import gui_hooks, qconnect
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.editor import Editor
from aqt.operations.note import add_note
from aqt.sound import av_player
from aqt.utils import tooltip, tr, restoreGeom, shortcut


class MyEditCurrent(EditCurrent):
    def __init__(self, noteId: NoteId):
        QMainWindow.__init__(self, None, Qt.WindowType.Window)
        note = aqt.mw.col.get_note(noteId)

        self.mw = aqt.mw
        self.form = aqt.forms.editcurrent.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(tr.editing_edit_current())
        self.setMinimumHeight(400)
        self.setMinimumWidth(250)
        self.editor = aqt.editor.Editor(
            self.mw,
            self.form.fieldsArea,
            self,
            editor_mode=aqt.editor.EditorMode.EDIT_CURRENT,
        )
        self.editor.card = note.cards()[0]  # 这里改了
        self.editor.set_note(note, focusTo=0)  # 这里改了
        restoreGeom(self, "editcurrent")
        close_button = self.form.buttonBox.button(QDialogButtonBox.StandardButton.Close)
        close_button.setShortcut(QKeySequence("Ctrl+Return"))
        # qt5.14+ doesn't handle numpad enter on Windows
        self.compat_add_shorcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        qconnect(self.compat_add_shorcut.activated, close_button.click)
        gui_hooks.operation_did_execute.append(self.on_operation_did_execute)
        self.show()


class MyAddCards(AddCards):
    def __init__(self, backLinkNote: Note, placeholder: str):
        self.backLinkNote = backLinkNote
        self.placeholder = placeholder
        AddCards.__init__(self, aqt.mw)

    def setupButtons(self) -> None:
        bb = self.form.buttonBox
        ar = QDialogButtonBox.ButtonRole.ActionRole
        # add
        self.addButton = bb.addButton(tr.actions_add(), ar)
        qconnect(self.addButton.clicked, self.add_current_note)
        self.addButton.setShortcut(QKeySequence("Ctrl+Return"))
        # qt5.14+ doesn't handle numpad enter on Windows
        self.compat_add_shorcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        qconnect(self.compat_add_shorcut.activated, self.addButton.click)
        self.addButton.setToolTip(shortcut(tr.adding_add_shortcut_ctrlandenter()))
        # close
        self.closeButton = QPushButton(tr.actions_close())
        self.closeButton.setAutoDefault(False)
        bb.addButton(self.closeButton, QDialogButtonBox.ButtonRole.RejectRole)
        qconnect(self.closeButton.clicked, self.close)

    def _add_current_note(self) -> None:
        note = self.editor.note

        if not self._note_can_be_added(note):
            return

        target_deck_id = self.deck_chooser.selected_deck_id

        def on_success(changes: OpChanges) -> None:
            tooltip(tr.adding_added(), period=500)
            av_player.stop_and_clear_queue()

            self.backLinkNote.fields = map(
                lambda it: it.replace('new' + self.placeholder, 'nid' + str(note.id)),
                self.backLinkNote.fields
            )
            aqt.mw.col.update_note(self.backLinkNote)
            self._load_new_note(sticky_fields_from=note)
            gui_hooks.add_cards_did_add_note(note)
            self.close()

        add_note(parent=self, note=note, target_deck_id=target_deck_id).success(
            on_success
        ).run_in_background()
