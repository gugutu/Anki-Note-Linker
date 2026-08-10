"""Parse and transform the add-on's note-link syntax."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import AbstractSet, Dict, Iterator, List, Optional

NOTE_LINK_PATTERN = re.compile(r"\[((?:[^\[]|\\\[)*?)\|nid(\d{13})\]")
NEW_LINK_PATTERN_TEMPLATE = r"\[((?:[^\[]|\\\[)*?)\|new{placeholder}\]"


@dataclass(frozen=True)
class NoteLink:
    """A parsed note link and its location in the source text."""

    title: str
    note_id: int
    start: int
    end: int


def unescape_title(title: str) -> str:
    return title.replace(r"\[", "[")


def escape_title(title: str) -> str:
    return title.replace("[", r"\[")


def iter_note_links(text: str) -> Iterator[NoteLink]:
    for match in NOTE_LINK_PATTERN.finditer(text):
        yield NoteLink(
            title=unescape_title(match.group(1)),
            note_id=int(match.group(2)),
            start=match.start(),
            end=match.end(),
        )


def child_note_ids(
    text: str,
    current_note_id: Optional[int] = None,
    allowed_note_ids: Optional[AbstractSet[int]] = None,
) -> List[int]:
    """Return unique linked note IDs while preserving source order."""
    result = []
    seen = set()
    for link in iter_note_links(text):
        if link.note_id == current_note_id or link.note_id in seen:
            continue
        if allowed_note_ids is not None and link.note_id not in allowed_note_ids:
            continue
        seen.add(link.note_id)
        result.append(link.note_id)
    return result


def child_link_titles(
    text: str,
    current_note_id: Optional[int] = None,
    allowed_note_ids: Optional[AbstractSet[int]] = None,
) -> Dict[int, str]:
    """Return the first title used for each linked note ID."""
    result = {}
    for link in iter_note_links(text):
        if link.note_id == current_note_id or link.note_id in result:
            continue
        if allowed_note_ids is not None and link.note_id not in allowed_note_ids:
            continue
        result[link.note_id] = link.title
    return result


def replace_note_links_with_titles(text: str) -> str:
    return NOTE_LINK_PATTERN.sub(lambda match: unescape_title(match.group(1)), text)


def find_new_link_title(text: str, placeholder: str) -> Optional[str]:
    if not re.fullmatch(r"\d{8}", placeholder):
        return None
    pattern = re.compile(NEW_LINK_PATTERN_TEMPLATE.format(placeholder=re.escape(placeholder)))
    match = pattern.search(text)
    return unescape_title(match.group(1)) if match else None


def format_note_link(note_id: int, title: str = "") -> str:
    if not re.fullmatch(r"\d{13}", str(note_id)):
        raise ValueError("Anki note IDs must contain exactly 13 digits")
    return f"[{escape_title(title)}|nid{note_id}]"


def format_new_link(placeholder: str, title: str = "") -> str:
    if not re.fullmatch(r"\d{8}", placeholder):
        raise ValueError("New-link placeholders must contain exactly 8 digits")
    return f"[{escape_title(title)}|new{placeholder}]"
