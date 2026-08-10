"""Canonical configuration defaults and validation rules."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class NumberSetting:
    runtime_key: str
    default: float
    minimum: float
    maximum: float


GRAPH_ZOOM_SETTINGS = {
    "graphZoom-zoomOutLimit": NumberSetting("minScale", 0.01, 0.001, 1.0),
    "graphZoom-zoomInLimit": NumberSetting("maxScale", 100.0, 1.0, 100.0),
    "graphZoom-normalZoomSpeed": NumberSetting("normalZoomSpeed", 1.0, 0.1, 5.0),
    "graphZoom-smoothZoomSpeed": NumberSetting("smoothZoomSpeed", 1.0, 0.1, 5.0),
    "graphZoom-smoothStepLimit": NumberSetting("smoothStepLimit", 0.15, 0.01, 1.0),
    "graphZoom-smoothResponseRange": NumberSetting("smoothResponseRange", 0.4, 0.05, 2.0),
    "graphZoom-smoothDurationMs": NumberSetting("smoothDurationMs", 250.0, 0.0, 1000.0),
    "graphZoom-autoFitZoomInLimit": NumberSetting("autoFitMaxScale", 1.4, 0.1, 10.0),
}


def default_config(is_mac: bool) -> Dict[str, Any]:
    modifier_shortcuts = {
        "shortcuts-copyNoteID": "Ctrl+Alt+C" if is_mac else "Alt+Shift+C",
        "shortcuts-copyNoteLink": "Ctrl+Alt+L" if is_mac else "Alt+Shift+L",
        "shortcuts-openNoteInNewWindow": "Ctrl+Alt+W" if is_mac else "Alt+Shift+W",
        "shortcuts-insertLinkWithClipboardID": "Ctrl+Alt+V" if is_mac else "Alt+Shift+V",
        "shortcuts-insertNewLink": "Ctrl+Alt+N" if is_mac else "Alt+Shift+N",
        "shortcuts-insertLinkTemplate": "Ctrl+Alt+T" if is_mac else "Alt+Shift+T",
    }
    defaults: Dict[str, Any] = {
        "showLinksPageAutomatically": True,
        "showGraphPageAutomatically": True,
        "showLinksPageInReviewerAutomatically": True,
        "showGraphPageInReviewerAutomatically": False,
        "splitRatio": "2:1",
        "splitRatioBetweenReviewerAndPanel": "4:1",
        "splitRatioBetweenLinksPageAndGraphPage": "1:1",
        "location": "right",
        "positionRelativeToReviewer": "right",
        "linkMaxLines": 5,
        "collapseClozeInLinksPage": True,
        "showForwardLinkTitleInLinksPage": False,
        "useHjpPreviewer": True,
        "enableImagePreview": True,
        "enableSmoothGraphZoom": False,
        "noteFieldsDisplayedInTheNoteSummary": [],
        "globalGraph-defaultSearchText": "deck:current",
        "globalGraph-defaultHighlightFilter": "is:due",
        "globalGraph-defaultShowSingleNode": False,
        "globalGraph-defaultShowTags": False,
        "globalGraph-nodeDegreeSizing": "none",
        "globalGraph-nodeColor": [57, 125, 237],
        "globalGraph-highlightedNodeColor": [244, 165, 0],
        "globalGraph-tagNodeColor": [127, 199, 132],
        "globalGraph-backgroundColor": [16, 16, 32],
    }
    defaults.update({key: setting.default for key, setting in GRAPH_ZOOM_SETTINGS.items()})
    defaults.update(modifier_shortcuts)
    return defaults


def clamp_number(value: Any, fallback: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return min(maximum, max(minimum, number))


def graph_zoom_config(config: Mapping[str, Any]) -> Dict[str, float]:
    result = {
        setting.runtime_key: clamp_number(
            config.get(config_key, setting.default),
            setting.default,
            setting.minimum,
            setting.maximum,
        )
        for config_key, setting in GRAPH_ZOOM_SETTINGS.items()
    }
    if result["minScale"] >= result["maxScale"]:
        result["minScale"] = GRAPH_ZOOM_SETTINGS["graphZoom-zoomOutLimit"].default
        result["maxScale"] = GRAPH_ZOOM_SETTINGS["graphZoom-zoomInLimit"].default
    return result


def copy_defaults(is_mac: bool) -> Dict[str, Any]:
    return deepcopy(default_config(is_mac))
