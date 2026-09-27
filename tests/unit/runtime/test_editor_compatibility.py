"""Exercise editor adapters without initializing Qt or an Anki collection."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def runtime(monkeypatch):
    class Editor:
        pass

    class Browser:
        pass

    class NotFoundError(Exception):
        pass

    mw = SimpleNamespace(col=SimpleNamespace(get_note=Mock()))
    config = {"showForwardLinkTitleInLinksPage": False}
    state = SimpleNamespace(globalGraph=None)
    tooltip = Mock()
    dependencies: dict[str, dict[str, object]] = {
        "anki": {},
        "anki.cards": {"Card": object},
        "anki.notes": {"Note": object, "NoteId": int},
        "anki.errors": {"NotFoundError": NotFoundError},
        "aqt": {"mw": mw, "gui_hooks": SimpleNamespace(editor_did_paste=Mock())},
        "aqt.browser": {"Browser": Browser},
        "aqt.browser.previewer": {"BrowserPreviewer": object},
        "aqt.editor": {"Editor": Editor, "EditorWebView": object},
        "aqt.utils": {"tooltip": tooltip},
        "anki_note_linker.runtime.configuration": {"config": config},
        "anki_note_linker.runtime.editor_windows": {"MyEditCurrent": object},
        "anki_note_linker.runtime.i18n": {"getTr": lambda text: text},
        "anki_note_linker.runtime.state": {"NoteNode": object, "PreviewState": object, "globalGraph": None},
    }
    for symbol in ("QAction", "QApplication", "QKeySequence", "QMenu", "QShortcut", "qconnect"):
        dependencies["aqt"][symbol] = object
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    package = __import__("anki_note_linker.runtime", fromlist=["runtime"])
    monkeypatch.setattr(package, "state", state, raising=False)
    runtime_root = Path(__file__).resolve().parents[3] / "src/addon/anki_note_linker/runtime"
    loaded = []
    for name in ("notes", "editor_actions"):
        module_name = f"anki_note_linker.runtime.{name}"
        spec = importlib.util.spec_from_file_location(module_name, runtime_root / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, module_name, module)
        spec.loader.exec_module(module)
        loaded.append(module)
    controller = type("Controller", (loaded[0].NoteServiceMixin, loaded[1].EditorActionsMixin), {})()
    controller.editors = set()
    controller.refreshPage = Mock()
    return SimpleNamespace(
        controller=controller, mw=mw, state=state, Editor=Editor, Browser=Browser, tooltip=tooltip, error=NotFoundError
    )


def new_editor(note_id=1234567890123, hidden=False):
    return SimpleNamespace(
        nid=note_id,
        widget=SimpleNamespace(isHidden=lambda: hidden),
        web=Mock(),
        set_note=Mock(),
        addMode=False,
    )


def test_browser_table_actions_require_single_selection(runtime):
    browser = runtime.Browser()
    browser.editor = new_editor()
    browser.card = None

    assert runtime.controller._getEditorFromContext(browser) is None
    assert runtime.controller._getNoteIDFromContext(browser) is None
    runtime.tooltip.assert_called_once_with("Please select a single note/card")
    runtime.mw.col.get_note.assert_not_called()

    browser.card = SimpleNamespace(nid=2345678901234)
    assert runtime.controller._getNoteIDFromContext(browser) == browser.card.nid


@pytest.mark.parametrize("hidden", [False, True])
def test_resolves_new_editor_note_only_when_visible(runtime, hidden):
    editor = new_editor(hidden=hidden)
    note = SimpleNamespace(id=editor.nid)
    runtime.mw.col.get_note.return_value = note
    assert runtime.controller.getEditorNote(editor) == (None if hidden else note)


def test_missing_or_deleted_note_does_not_return_cached_id(runtime):
    editor = new_editor()
    runtime.mw.col.get_note.side_effect = runtime.error
    assert runtime.controller._getNoteIDFromContext(editor) is None
    runtime.mw.col = None
    assert runtime.controller.getEditorNote(editor) is None


@pytest.mark.parametrize("handler_kind", ["window", "editor", "other"])
def test_saved_note_refreshes_new_editor_for_all_actual_handlers(runtime, handler_kind):
    editor = new_editor()
    legacy = runtime.Editor()
    legacy.note = SimpleNamespace(id=editor.nid)
    runtime.mw.col.get_note.return_value = legacy.note
    runtime.controller.editors = [editor, legacy]
    graph = Mock()
    runtime.state.globalGraph = graph
    handler = {"window": SimpleNamespace(editor=editor), "editor": editor, "other": object()}[handler_kind]
    changes = SimpleNamespace(note_text=True, study_queues=False, notetype=False)

    runtime.controller.onOperationDidExecute(changes, handler)

    runtime.controller.refreshPage.assert_called_once_with(editor, adaptScale=False, reason="note text changed")
    graph.refreshGlobalGraph.assert_called_once()


def test_unrelated_operation_does_not_refresh_panels(runtime):
    runtime.controller.editors = [new_editor()]
    runtime.controller.onOperationDidExecute(SimpleNamespace(note_text=False), object())
    runtime.controller.refreshPage.assert_not_called()
    runtime.mw.col.get_note.assert_not_called()


def test_legacy_insert_uses_legacy_paste_and_selected_text(runtime):
    editor = runtime.Editor()
    editor.note = object()
    editor.web = Mock()
    editor.web.selectedText.return_value = "Title"
    editor.doPaste = Mock()
    runtime.controller.insertLinkTemplate(editor)
    editor.doPaste.assert_called_once_with("[Title|nid]", True)


def test_new_editor_shortcut_requests_frontend_selection(runtime):
    editor = new_editor()
    runtime.controller.insertLinkTemplate(editor)
    editor.web.eval.assert_called_once_with('window.AnkiNoteLinkerEditor.runAction("insertLinkTemplate");')

    editor.web.eval.reset_mock()
    runtime.controller.insertLinkTemplate(editor, "中文标题")
    editor.web.eval.assert_called_once_with(
        'window.AnkiNoteLinkerEditor.pasteHtml("[\\u4e2d\\u6587\\u6807\\u9898|nid]", true);'
    )


def test_unchanged_editor_does_not_skip_other_editors_or_global_graph(runtime):
    note = SimpleNamespace(id=1234567890123, fields=["Summary"])
    unchanged = runtime.Editor()
    unchanged.note = note
    unchanged.noteNode = SimpleNamespace(mainField="Summary", childIds=[])
    changed = runtime.Editor()
    changed.note = note
    changed.noteNode = SimpleNamespace(mainField="Old summary", childIds=[])
    runtime.controller.editors = [unchanged, changed]
    runtime.controller.getMainField = lambda note: note.fields[0]
    runtime.controller.findChildIds = lambda *args: []
    graph = Mock(searchedIds={note.id})
    runtime.state.globalGraph = graph

    runtime.controller.onEditNote(note)

    runtime.controller.refreshPage.assert_called_once_with(
        changed, adaptScale=False, reason="mainField or links of note changed"
    )
    graph.refreshGlobalGraph.assert_called_once_with(note, "mainField or links of note changed")
