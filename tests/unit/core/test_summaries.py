from anki_note_linker.core.summaries import build_summary, clean_summary, replace_cloze_markup, select_summary_text


def test_replaces_nested_cloze_markup_until_stable() -> None:
    text = "{{c1::outer {{c2::inner}} text}}"

    assert replace_cloze_markup(text, collapse=False) == "outer inner text"
    assert replace_cloze_markup(text, collapse=True) == "[...]"


def test_preserves_cloze_hint_as_part_of_visible_text() -> None:
    assert replace_cloze_markup("{{c1::answer::hint}}", collapse=False) == "answer::hint"


def test_cleans_links_before_collapsing_cloze_markup() -> None:
    text = "{{c1::[Linked|nid1234567890123]}}"

    assert clean_summary(text, collapse_cloze=False) == "Linked"
    assert clean_summary(text, collapse_cloze=True) == "[...]"


def test_selects_image_and_configured_fields_in_historical_order() -> None:
    fields = ["front", "back", "image"]
    indexes = {"Front": 0, "Back": 1, "Image": 2}

    assert select_summary_text(fields, indexes, ["Back"], enable_image_preview=True) == "image back"
    assert select_summary_text(fields, indexes, ["Back", "Image"], enable_image_preview=False) == "back"


def test_falls_back_to_first_field_when_no_configured_field_exists() -> None:
    assert select_summary_text(["front", "back"], {"Front": 0}, ["Missing"], True) == "front"
    assert select_summary_text([], {}, [], True) == ""


def test_build_summary_combines_selection_and_cleanup() -> None:
    assert (
        build_summary(
            ["{{c1::[Linked|nid1234567890123]}}"],
            {"Front": 0},
            ["Front"],
            enable_image_preview=False,
            collapse_cloze=True,
        )
        == "[...]"
    )
