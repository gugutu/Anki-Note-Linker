"""Exercise panel allocation and graph cache updates without Qt or Anki."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from anki_note_linker.config.schema import default_config


@pytest.fixture
def graph_runtime(monkeypatch):
    def make_node(note_id, child_ids, parent_ids, main_field, isTag=False):
        return SimpleNamespace(id=note_id, childIds=child_ids, parentIds=parent_ids, mainField=main_field, isTag=isTag)

    mw = SimpleNamespace(reviewer=SimpleNamespace(card=None, state="answer"))
    state = SimpleNamespace(
        addon=SimpleNamespace(
            findChildIds=lambda note_id, fields, rangeIdSet: [],
            getMainField=lambda note: note.fields[0],
        ),
    )
    config = default_config(False)
    dependencies: dict[str, dict[str, object]] = {
        "anki": {},
        "anki.cards": {"Card": object},
        "anki.collection": {"Collection": object, "OpChanges": object},
        "anki.errors": {"SearchError": Exception},
        "anki.notes": {"Note": object, "NoteId": int},
        "aqt": {"mw": mw, "gui_hooks": object},
        "aqt.main": {"MainWindowState": str},
        "aqt.reviewer": {"Reviewer": object},
        "aqt.errors": {"show_exception": Mock()},
        "aqt.operations": {"QueryOp": object},
        "aqt.utils": {"restoreGeom": Mock(), "saveGeom": Mock(), "tooltip": Mock()},
        "aqt.webview": {"AnkiWebView": object},
        "anki_note_linker.runtime.configuration": {"config": config, "ConfigView": object},
        "anki_note_linker.runtime.i18n": {"getTr": lambda text: text},
        "anki_note_linker.runtime.lifecycle": {
            "cleanup_webview": Mock(),
            "enable_immediate_profile_close": Mock(),
            "remove_hook_safely": Mock(),
        },
        "anki_note_linker.runtime.state": {
            "Connection": object,
            "JsNoteNode": object,
            "NoteNode": make_node,
            "log": Mock(),
        },
        "anki_note_linker.runtime.web_pages": {
            "legacy_graph_page": Mock(),
            "links_page": Mock(),
            "new_graph_page": Mock(),
        },
    }
    for symbol in (
        "QAction",
        "QCheckBox",
        "QColor",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QMenu",
        "QPushButton",
        "QSplitter",
        "Qt",
        "QVBoxLayout",
        "QWidget",
        "qconnect",
    ):
        dependencies["aqt"][symbol] = object
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    package = __import__("anki_note_linker.runtime", fromlist=["runtime"])
    monkeypatch.setattr(package, "state", state, raising=False)
    runtime_root = Path(__file__).resolve().parents[3] / "src/addon/anki_note_linker/runtime"
    modules = []
    for name in ("global_graph", "reviewer"):
        module_name = f"anki_note_linker.runtime.{name}"
        spec = importlib.util.spec_from_file_location(module_name, runtime_root / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, module_name, module)
        spec.loader.exec_module(module)
        modules.append(module)
    graph = modules[0].GlobalGraph.__new__(modules[0].GlobalGraph)
    graph._closed = False
    graph.needRefreshAgain = False
    graph.noteCache = {}
    graph.searchedIds = {1, 2}
    controller = modules[1].ReviewerMixin()
    for name in (
        "injectReviewerPanelsToMainWindow",
        "ensureReviewerLinksPage",
        "ensureReviewerGraphPage",
        "updateReviewerPanelVisibility",
        "refreshReviewerPanel",
    ):
        setattr(controller, name, Mock())
    return SimpleNamespace(graph=graph, controller=controller, config=config, reviewer=mw.reviewer)


@pytest.mark.parametrize("links,graph", [(False, False), (True, False), (False, True), (True, True)])
def test_review_creates_only_enabled_panels(graph_runtime, links, graph):
    context = graph_runtime
    context.config["showLinksPageInReviewerAutomatically"] = links
    context.config["showGraphPageInReviewerAutomatically"] = graph

    context.controller.onStateChange("review", "overview")

    assert context.controller.ensureReviewerLinksPage.call_count == int(links)
    assert context.controller.ensureReviewerGraphPage.call_count == int(graph)
    assert context.reviewer.showLinksPage == links
    assert context.reviewer.showGraphPage == graph
    context.controller.ensureReviewerLinksPage.reset_mock()
    context.controller.ensureReviewerGraphPage.reset_mock()
    context.controller.onToggleReviewerLinksPanel(False)
    context.controller.onToggleReviewerGraphPanel(False)
    context.controller.ensureReviewerLinksPage.assert_not_called()
    context.controller.ensureReviewerGraphPage.assert_not_called()


def test_repeated_tagged_note_updates_do_not_accumulate_edges(graph_runtime):
    graph = graph_runtime.graph
    note = SimpleNamespace(id=1, fields=["Summary"], tags=["same-tag", "same-tag"])

    for _ in range(20):
        graph.updateNodeCache(note, showTags=True)

    assert graph.noteCache["same-tag"].childIds == [1]
    assert graph.noteCache[1].parentIds == {"same-tag"}
    assert len(graph.noteCache) == 2


def test_tag_changes_remove_old_membership_without_affecting_other_notes(graph_runtime):
    graph = graph_runtime.graph
    first = SimpleNamespace(id=1, fields=["First"], tags=["shared", "orphan"])
    second = SimpleNamespace(id=2, fields=["Second"], tags=["shared"])
    graph.updateNodeCache(first, showTags=True)
    graph.updateNodeCache(second, showTags=True)
    first.tags = ["new-tag"]

    graph.updateNodeCache(first, showTags=True)

    assert "orphan" not in graph.noteCache
    assert graph.noteCache["shared"].childIds == [2]
    assert graph.noteCache["new-tag"].childIds == [1]
    assert graph.noteCache[1].parentIds == {"new-tag"}
    assert graph.noteCache[2].parentIds == {"shared"}


def test_disabling_tags_removes_unused_tag_nodes(graph_runtime):
    graph = graph_runtime.graph
    note = SimpleNamespace(id=1, fields=["Summary"], tags=["old-tag"])
    graph.updateNodeCache(note, showTags=True)

    graph.updateNodeCache(note, showTags=False)

    assert set(graph.noteCache) == {1}
    assert graph.noteCache[1].parentIds == set()
