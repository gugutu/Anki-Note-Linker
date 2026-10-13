"""Build stable graph and links-panel summaries from note fields."""

from __future__ import annotations

from typing import List, Mapping, Sequence

from .cloze import render_cloze_summary
from .links import replace_note_links_with_titles


def replace_cloze_markup(text: str, collapse: bool) -> str:
    """Render cloze summaries using Anki's tokenizer and nested-parser algorithm."""
    return render_cloze_summary(text, collapse)


def clean_summary(text: str, collapse_cloze: bool) -> str:
    without_links = replace_note_links_with_titles(text)
    return replace_cloze_markup(without_links, collapse_cloze)


def select_summary_text(
    fields: Sequence[str],
    field_indexes: Mapping[str, int],
    configured_field_names: Sequence[str],
    enable_image_preview: bool,
) -> str:
    """Select summary fields while preserving the historical fallback behavior."""
    if not fields:
        return ""

    selected: List[str] = []
    image_index = field_indexes.get("Image")
    if enable_image_preview and image_index is not None and image_index < len(fields):
        selected.append(fields[image_index])

    for field_name in configured_field_names:
        if field_name == "Image":
            continue
        index = field_indexes.get(field_name)
        if index is not None and index < len(fields):
            selected.append(fields[index])

    return " ".join(selected) if selected else fields[0]


def build_summary(
    fields: Sequence[str],
    field_indexes: Mapping[str, int],
    configured_field_names: Sequence[str],
    enable_image_preview: bool,
    collapse_cloze: bool,
) -> str:
    selected = select_summary_text(fields, field_indexes, configured_field_names, enable_image_preview)
    return clean_summary(selected, collapse_cloze)
