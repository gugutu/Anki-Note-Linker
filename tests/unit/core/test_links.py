import pytest

from anki_note_linker.core.links import (
    child_link_titles,
    child_note_ids,
    find_new_link_title,
    format_new_link,
    format_note_link,
    iter_note_links,
    replace_note_links_with_titles,
    resolve_new_link,
)


def test_parses_links_and_unescapes_opening_brackets() -> None:
    text = r"Before [one \[nested|nid1234567890123] after"

    links = list(iter_note_links(text))

    assert [(link.title, link.note_id) for link in links] == [("one [nested", 1234567890123)]
    assert text[links[0].start : links[0].end] == r"[one \[nested|nid1234567890123]"


def test_collects_unique_valid_children_in_source_order() -> None:
    text = "[first|nid1234567890123] [self|nid9999999999999] [duplicate|nid1234567890123] [second|nid2345678901234]"

    assert child_note_ids(
        text,
        current_note_id=9999999999999,
        allowed_note_ids={1234567890123, 9999999999999, 2345678901234},
    ) == [1234567890123, 2345678901234]
    assert child_link_titles(text) == {
        1234567890123: "first",
        9999999999999: "self",
        2345678901234: "second",
    }


def test_replaces_links_without_consuming_surrounding_html() -> None:
    assert replace_note_links_with_titles("<b>[Title|nid1234567890123]</b>") == "<b>Title</b>"


def test_formats_links_and_validates_identifier_lengths() -> None:
    assert format_note_link(1234567890123, "A [title") == r"[A \[title|nid1234567890123]"
    assert format_new_link("12345678", "New") == "[New|new12345678]"

    with pytest.raises(ValueError):
        format_note_link(123)
    with pytest.raises(ValueError):
        format_new_link("123")


def test_finds_only_the_requested_new_link_placeholder() -> None:
    text = r"[ignored|new11111111] [A \[title|new22222222]"

    assert find_new_link_title(text, "22222222") == "A [title"
    assert find_new_link_title(text, "33333333") is None
    assert find_new_link_title(text, "invalid") is None


def test_resolves_only_matching_links_without_changing_other_content() -> None:
    text = r"<b>[A \[title|new12345678]</b> [Other|new87654321] new12345678 [Again|new12345678]"
    assert resolve_new_link(text, "12345678", 1234567890123) == (
        r"<b>[A \[title|nid1234567890123]</b> [Other|new87654321] new12345678 [Again|nid1234567890123]"
    )


@pytest.mark.parametrize("placeholder", ["12345678", "invalid"])
def test_does_not_restore_removed_placeholders(placeholder: str) -> None:
    text = "Latest text without a link [Existing|nid1234567890123]"
    assert resolve_new_link(text, placeholder, 2345678901234) == text
