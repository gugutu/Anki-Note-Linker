import json
from pathlib import Path

from anki_note_linker.config.schema import clamp_number, default_config, graph_zoom_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_platform_defaults_only_change_shortcuts() -> None:
    mac = default_config(is_mac=True)
    other = default_config(is_mac=False)

    assert mac["shortcuts-copyNoteID"] == "Ctrl+Alt+C"
    assert other["shortcuts-copyNoteID"] == "Alt+Shift+C"
    assert {key: value for key, value in mac.items() if not key.startswith("shortcuts-")} == {
        key: value for key, value in other.items() if not key.startswith("shortcuts-")
    }


def test_clamps_invalid_and_out_of_range_numbers() -> None:
    assert clamp_number("bad", 1.0, 0.1, 5.0) == 1.0
    assert clamp_number(-1, 1.0, 0.1, 5.0) == 0.1
    assert clamp_number(99, 1.0, 0.1, 5.0) == 5.0


def test_graph_zoom_config_uses_runtime_names_and_repairs_reversed_limits() -> None:
    zoom = graph_zoom_config(
        {
            "graphZoom-zoomOutLimit": 1,
            "graphZoom-zoomInLimit": 1,
            "graphZoom-smoothDurationMs": 5000,
        }
    )

    assert zoom["minScale"] == 0.01
    assert zoom["maxScale"] == 100.0
    assert zoom["smoothDurationMs"] == 1000.0


def test_config_json_matches_non_platform_defaults() -> None:
    packaged_defaults = json.loads((PROJECT_ROOT / "src" / "addon" / "config.json").read_text(encoding="utf-8"))
    canonical_defaults = {
        key: value for key, value in default_config(is_mac=False).items() if not key.startswith("shortcuts-")
    }

    assert packaged_defaults == canonical_defaults
