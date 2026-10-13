"""Python port of Anki's Cloze tokenizer and nested parser for note summaries.

Adapted from Ankitects Pty Ltd and contributors, GNU AGPL v3 or later:
https://github.com/ankitects/anki/blob/42ddc889b6b136c34efe93ee6a3a72d26991e9e1/rslib/src/cloze.rs
The summary renderer hides all top-level clozes, rather than selecting a card ordinal.
"""

from __future__ import annotations

import re
from typing import Iterator, List, Optional, Tuple, Union

_OPEN_CLOZE = re.compile(r"\{\{c([0-9,]*)::")
_MAX_DEPTH = 10
_Token = Union[str, Tuple[int, ...], None]
_Node = Union[str, "_Cloze"]


def _open_cloze(text: str, offset: int) -> Optional[Tuple[int, Tuple[int, ...]]]:
    match = _OPEN_CLOZE.match(text, offset)
    if match is None:
        return None
    ordinals = set()
    for number in match[1].split(","):
        if not number:
            continue
        normalized = number.lstrip("0") or "0"
        if len(normalized) <= 5 and int(normalized) <= 65535:
            ordinals.add(int(normalized))
    return (match.end(), tuple(sorted(ordinals))) if ordinals else None


def _tokenize(text: str) -> Iterator[_Token]:
    offset = 0
    current: Optional[Tuple[str, int]] = None
    next_id = 0
    regions: List[Optional[int]] = []
    while offset < len(text):
        opening = _open_cloze(text, offset)
        region = current[1] if current is not None else None
        can_close = region is None or bool(regions and regions[-1] == region)
        if opening is not None:
            regions.append(region)
            offset, ordinals = opening
            yield ordinals
        elif can_close and text.startswith("}}", offset):
            if regions:
                regions.pop()
            offset += 2
            yield None
        else:
            start = offset
            while offset < len(text):
                region = current[1] if current is not None else None
                can_close = region is None or bool(regions and regions[-1] == region)
                if _open_cloze(text, offset) is not None or (can_close and text.startswith("}}", offset)):
                    break
                if current is None:
                    for opening_delimiter, closing_delimiter in ((r"\(", r"\)"), (r"\[", r"\]")):
                        if text.startswith(opening_delimiter, offset) and closing_delimiter in text[offset + 2 :]:
                            current = (closing_delimiter, next_id)
                            next_id += 1
                            offset += 2
                            break
                    else:
                        offset += 1
                elif text.startswith(current[0], offset):
                    current = None
                    offset += 2
                else:
                    offset += 1
            yield text[start:offset]


class _Cloze:
    __slots__ = ("ordinals", "nodes", "hint")

    def __init__(self, ordinals: Tuple[int, ...]) -> None:
        self.ordinals = ordinals
        self.nodes: List[_Node] = []
        self.hint: Optional[str] = None


def _parse(text: str) -> List[_Node]:
    stack: List[_Cloze] = []
    output: List[_Node] = []
    for token in _tokenize(text):
        if isinstance(token, tuple):
            if len(stack) < _MAX_DEPTH:
                stack.append(_Cloze(token))
        elif isinstance(token, str):
            if stack:
                cloze = stack[-1]
                if not token.startswith("image-occlusion:") and "::" in token:
                    token, cloze.hint = token.split("::", 1)
                cloze.nodes.append(token)
            else:
                output.append(token)
        elif stack:
            cloze = stack.pop()
            (stack[-1].nodes if stack else output).append(cloze)
        else:
            output.append("}}")
    return output


def render_cloze_summary(text: str, collapse: bool) -> str:
    """Render Anki-parsed clozes without card-specific spans or hint text."""
    if "{{c" not in text:
        return text

    def render(nodes: List[_Node]) -> str:
        return "".join(node if isinstance(node, str) else "[...]" if collapse else render(node.nodes) for node in nodes)

    return render(_parse(text))
