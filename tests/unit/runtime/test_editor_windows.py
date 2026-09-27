"""Verify linked-note creation without starting Anki or Qt."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def linked_note_window(monkeypatch):
    class NotFoundError(Exception):
        pass

    collection = SimpleNamespace(get_note=Mock(), update_note=Mock())
    hooks = SimpleNamespace(add_cards_did_add_note=Mock())
    operation = Mock()
    operation.success.return_value = operation
    add_note = Mock(return_value=operation)
    dependencies: dict[str, dict[str, object]] = {
        "anki": {},
        "anki.collection": {"OpChanges": object},
        "anki.errors": {"NotFoundError": NotFoundError},
        "anki.notes": {"Note": object, "NoteId": int},
        "aqt": {"mw": SimpleNamespace(col=collection), "gui_hooks": hooks},
        "aqt.addcards": {"AddCards": object},
        "aqt.editcurrent": {"EditCurrent": object},
        "aqt.operations": {},
        "aqt.operations.note": {"add_note": add_note},
        "aqt.sound": {"av_player": SimpleNamespace(stop_and_clear_queue=Mock())},
        "aqt.utils": {
            "restoreGeom": Mock(),
            "saveGeom": Mock(),
            "shortcut": Mock(),
            "tooltip": Mock(),
            "tr": SimpleNamespace(adding_added=lambda: "Added"),
        },
        "anki_note_linker.runtime.lifecycle": {
            "mark_managed_dialog_closed": Mock(),
            "register_managed_dialog": Mock(),
            "remove_hook_safely": Mock(),
        },
    }
    for symbol in ("QDialogButtonBox", "QKeySequence", "QMainWindow", "QPushButton", "QShortcut", "Qt", "qconnect"):
        dependencies["aqt"][symbol] = object
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "anki_note_linker.runtime.editor_windows"
    path = Path(__file__).resolve().parents[3] / "src/addon/anki_note_linker/runtime/editor_windows.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    window = module.MyAddCards.__new__(module.MyAddCards)
    window.backLinkNote = SimpleNamespace(id=1234567890123, fields=["[Child|new12345678] original"])
    window.placeholder = "12345678"
    window.editor = SimpleNamespace(note=SimpleNamespace(id=2345678901234))
    window.deck_chooser = SimpleNamespace(selected_deck_id=1)
    window._note_can_be_added = Mock(return_value=True)
    window._load_new_note = Mock()
    window.close = Mock()
    return SimpleNamespace(
        window=window, collection=collection, hooks=hooks, operation=operation, add_note=add_note, error=NotFoundError
    )


def finish_addition(context):
    callback = context.operation.success.call_args.args[0]
    callback(SimpleNamespace())


def test_link_creation_preserves_parent_edits_made_while_addition_is_pending(linked_note_window):
    context = linked_note_window
    context.window._add_current_note()
    context.collection.get_note.assert_not_called()
    latest_parent = SimpleNamespace(
        id=context.window.backLinkNote.id,
        fields=["[Edited title|new12345678] newer text", "Updated second field"],
        tags=["new-tag"],
    )
    context.collection.get_note.return_value = latest_parent

    finish_addition(context)

    context.collection.get_note.assert_called_once_with(latest_parent.id)
    context.collection.update_note.assert_called_once_with(latest_parent)
    assert latest_parent.fields == ["[Edited title|nid2345678901234] newer text", "Updated second field"]
    assert latest_parent.tags == ["new-tag"]
    assert context.window.backLinkNote.fields == ["[Child|new12345678] original"]
    context.window._load_new_note.assert_called_once_with(sticky_fields_from=context.window.editor.note)
    context.hooks.add_cards_did_add_note.assert_called_once_with(context.window.editor.note)
    context.window.close.assert_called_once()


def test_removed_placeholder_does_not_trigger_parent_write(linked_note_window):
    context = linked_note_window
    context.collection.get_note.return_value = SimpleNamespace(
        id=context.window.backLinkNote.id, fields=["The link was removed"]
    )
    context.window._add_current_note()

    finish_addition(context)

    context.collection.update_note.assert_not_called()
    context.hooks.add_cards_did_add_note.assert_called_once_with(context.window.editor.note)
    context.window.close.assert_called_once()


def test_deleted_parent_does_not_break_successful_child_creation(linked_note_window):
    context = linked_note_window
    context.collection.get_note.side_effect = context.error
    context.window._add_current_note()

    finish_addition(context)

    context.collection.update_note.assert_not_called()
    context.hooks.add_cards_did_add_note.assert_called_once_with(context.window.editor.note)
    context.window.close.assert_called_once()


def test_invalid_child_is_not_added_or_linked(linked_note_window):
    context = linked_note_window
    context.window._note_can_be_added.return_value = False

    context.window._add_current_note()

    context.add_note.assert_not_called()
    context.collection.get_note.assert_not_called()
    context.collection.update_note.assert_not_called()
