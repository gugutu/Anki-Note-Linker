"""Backward-compatible migrations for historical add-on configuration shapes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping


def migrate_config(raw_config: Mapping[str, Any], defaults: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a migrated copy while preserving unknown user-defined keys."""
    config = deepcopy(dict(raw_config))
    for key, value in defaults.items():
        if key not in config:
            config[key] = deepcopy(value)

    shortcuts = config.pop("shortcuts", None)
    if isinstance(shortcuts, Mapping):
        shortcut_keys = {
            "copyNoteID": "shortcuts-copyNoteID",
            "copyNoteLink": "shortcuts-copyNoteLink",
            "openNoteInNewWindow": "shortcuts-openNoteInNewWindow",
            "insertLinkWithClipboardID": "shortcuts-insertLinkWithClipboardID",
            "insertNewLink": "shortcuts-insertNewLink",
            "insertLinkTemplate": "shortcuts-insertLinkTemplate",
        }
        for old_key, new_key in shortcut_keys.items():
            config[new_key] = shortcuts.get(old_key, defaults[new_key])

    global_graph = config.pop("globalGraph", None)
    if isinstance(global_graph, Mapping):
        graph_keys = {
            "defaultSearchText": "globalGraph-defaultSearchText",
            "defaultHighlightFilter": "globalGraph-defaultHighlightFilter",
            "defaultShowSingleNode": "globalGraph-defaultShowSingleNode",
            "nodeColor": "globalGraph-nodeColor",
            "highlightedNodeColor": "globalGraph-highlightedNodeColor",
            "graphBackgroundColor": "globalGraph-backgroundColor",
        }
        for old_key, new_key in graph_keys.items():
            config[new_key] = global_graph.get(old_key, defaults[new_key])

    legacy_previewer_key = "Use the previewer of hjp-linkmaster if it is installed"
    if legacy_previewer_key in config:
        config["useHjpPreviewer"] = config.pop(legacy_previewer_key)

    return config
