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
from aqt.utils import tooltip, tr, restoreGeom, saveGeom, shortcut

from .lifecycle import mark_managed_dialog_closed, register_managed_dialog, remove_hook_safely


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
        button_box = getattr(self.form, "buttonBox", None)
        if button_box is None:
            button_box = QDialogButtonBox(Qt.Orientation.Horizontal)
            self.form.verticalLayout.insertWidget(1, button_box)
            button_box.addButton(QDialogButtonBox.StandardButton.Close)
            qconnect(button_box.rejected, self.close)
        self.buttonbox = button_box
        close_button = button_box.button(QDialogButtonBox.StandardButton.Close)
        assert close_button is not None
        close_button.setShortcut(QKeySequence("Ctrl+Return"))
        # qt5.14+ doesn't handle numpad enter on Windows
        self.compat_add_shorcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        qconnect(self.compat_add_shorcut.activated, close_button.click)
        self._cleaned_up = False
        gui_hooks.operation_did_execute.append(self.on_operation_did_execute)
        register_managed_dialog(self, "edit-current")
        self.show()

    def cleanup(self) -> None:
        if self._cleaned_up:
            return
        self._cleaned_up = True
        mark_managed_dialog_closed(self)
        remove_hook_safely(gui_hooks.operation_did_execute, self.on_operation_did_execute)
        self.editor.cleanup()
        saveGeom(self, "editcurrent")


class MyAddCards(AddCards):
    def __init__(self, backLinkNote: Note, placeholder: str):
        self.backLinkNote = backLinkNote
        self.placeholder = placeholder
        AddCards.__init__(self, aqt.mw)
        self._anki_note_linker_closed = False
        register_managed_dialog(self, "add-cards")

    def _close(self) -> None:
        if getattr(self, "_anki_note_linker_closed", False):
            return
        self._anki_note_linker_closed = True
        dialogs = getattr(aqt, "dialogs", None)
        entries = getattr(dialogs, "_dialogs", None)
        standard_entry = entries.get("AddCards") if isinstance(entries, dict) else None
        try:
            super()._close()
        finally:
            if standard_entry is not None:
                entries["AddCards"] = standard_entry
            mark_managed_dialog_closed(self)

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
