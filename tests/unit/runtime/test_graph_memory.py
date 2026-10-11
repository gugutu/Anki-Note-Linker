"""Exercise panel allocation and graph cache updates without Qt or Anki."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from anki_note_linker.config.schema import default_config


@pytest.fixture
def graph_runtime(monkeypatch):
    mw = SimpleNamespace(
        reviewer=SimpleNamespace(card=None, state="answer"), addonManager=SimpleNamespace(setWebExports=Mock())
    )
    state = SimpleNamespace(
        addon=SimpleNamespace(
            findChildIds=lambda note_id, fields, rangeIdSet: [],
            getMainField=lambda note: note.fields[0],
        ),
    )
    config = default_config(False)
    dependencies: dict[str, dict[str, object]] = {
        "anki": {"collection": SimpleNamespace(OpChanges=object)},
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
        "aqt.browser.previewer": {"BrowserPreviewer": object},
        "anki_note_linker.runtime.configuration": {"config": config, "ConfigView": object},
        "anki_note_linker.runtime.i18n": {"getTr": lambda text: text},
        "anki_note_linker.runtime.lifecycle": {
            "cleanup_webview": Mock(),
            "enable_immediate_profile_close": Mock(),
            "remove_hook_safely": Mock(),
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
    for name in ("state", "global_graph", "reviewer"):
        module_name = f"anki_note_linker.runtime.{name}"
        spec = importlib.util.spec_from_file_location(module_name, runtime_root / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, module_name, module)
        spec.loader.exec_module(module)
        if name == "state":
            monkeypatch.setattr(module, "addon", state.addon)
            monkeypatch.setattr(package, "state", module)
        modules.append(module)
    graph = modules[1].GlobalGraph.__new__(modules[1].GlobalGraph)
    graph._closed = False
    graph.needRefreshAgain = False
    graph.noteCache = {}
    graph.searchedIds = {1, 2}
    controller = modules[2].ReviewerMixin()
    for name in (
        "injectReviewerPanelsToMainWindow",
        "ensureReviewerLinksPage",
        "ensureReviewerGraphPage",
        "updateReviewerPanelVisibility",
        "refreshReviewerPanel",
    ):
        setattr(controller, name, Mock())
    return SimpleNamespace(
        graph=graph, controller=controller, config=config, reviewer=mw.reviewer, values=modules[0], module=modules[1]
    )


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


def test_compact_graph_objects_preserve_serialized_fields(graph_runtime):
    values = graph_runtime.values
    note = values.NoteNode(1, [2], {3}, "<b>Summary</b>")
    child = note.toJsNoteNode("child")
    child.linkTitle = "Custom title"
    child.type = "parent child"
    connection = values.Connection(1, "tag")

    assert all(not hasattr(value, "__dict__") for value in (note, child, connection))
    assert json.loads(json.dumps([child, connection], default=lambda value: value.to_dict())) == [
        {"id": 1, "mainField": "<b>Summary</b>", "type": "parent child", "linkTitle": "Custom title"},
        {"source": 1, "target": "tag"},
    ]
    tag = values.NoteNode("tag", [1], set(), "tag", isTag=True)
    assert tag.toJsNoteNode("highlight").to_dict() == {
        "id": "tag",
        "mainField": "tag",
        "type": "tag",
        "linkTitle": None,
    }


@pytest.mark.parametrize("show_single", [False, True])
def test_global_graph_refresh_does_not_retain_transport_lists(graph_runtime, monkeypatch, show_single):
    graph = graph_runtime.graph
    values = graph_runtime.values
    graph.noteCache = {
        1: values.NoteNode(1, [2], set(), "First"),
        2: values.NoteNode(2, [], {1}, "Second"),
        3: values.NoteNode(3, [], set(), "Single"),
    }
    graph.inRefreshProcess = False
    graph.lastSearchState = None
    graph.hlIds = {2}
    graph.lineEdit = SimpleNamespace(text=lambda: "")
    graph.lineEdit2 = SimpleNamespace(text=lambda: "")
    graph.showSingleNodesCheckBox = SimpleNamespace(isChecked=lambda: show_single)
    graph.showTagNodesCheckBox = SimpleNamespace(isChecked=lambda: False)
    graph.showSuspendedNotesCheckBox = SimpleNamespace(isChecked=lambda: False)
    graph.rebuildCache = Mock()
    graph.web = SimpleNamespace(eval=Mock())
    graph.qColorToString = lambda color: "rgb(0,0,0)"
    monkeypatch.setattr(graph_runtime.module, "QColor", SimpleNamespace(fromRgb=lambda *args: args))

    class Query:
        def __init__(self, parent, op, success):
            self.op = op
            self.success = success

        def failure(self, callback):
            return self

        def run_in_background(self):
            self.success(self.op(object()))

    monkeypatch.setattr(graph_runtime.module, "QueryOp", Query)
    graph.refreshGlobalGraph()

    script = graph.web.eval.call_args.args[0]
    decoder = json.JSONDecoder()
    nodes, offset = decoder.raw_decode(script.split("reloadPage(", 1)[1].lstrip())
    arguments = script.split("reloadPage(", 1)[1].lstrip()
    connections, _ = decoder.raw_decode(arguments[offset:].lstrip().removeprefix(",").lstrip())
    assert [node["id"] for node in nodes] == ([1, 2, 3] if show_single else [1, 2])
    assert nodes[1]["type"] == "highlight"
    assert connections == [{"source": 1, "target": 2}]
    assert not hasattr(graph, "noteCacheList")
    assert not hasattr(graph, "linkCache")
    assert graph.inRefreshProcess is False
    assert len(graph.noteCache) == 3
