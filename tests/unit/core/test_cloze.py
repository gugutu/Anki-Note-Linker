"""Regression cases from Anki's rslib/src/cloze.rs, adapted to note summaries."""

import pytest

from anki_note_linker.core.cloze import _parse, render_cloze_summary


@pytest.mark.parametrize(
    ("text", "expanded", "collapsed"),
    [
        ("plain text", "plain text", "plain text"),
        ("{{c1,2::shared}}", "shared", "[...]"),
        ("{{c1,2::answer::hint}}", "answer", "[...]"),
        ("{{c1::first}} and {{c2,3::shared}}", "first and shared", "[...] and [...]"),
        ("foo {{c1::bar {{c2::baz}}}}", "foo bar baz", "foo [...]"),
        ("foo {{c1::bar {{c2::baz}}::qux}}", "foo bar baz", "foo [...]"),
        ("{{c1,2::outer {{c3::inner}}}}", "outer inner", "[...]"),
        ("{{c1::outer {{c2,3::inner}}}}", "outer inner", "[...]"),
        ("{{c1::outer {{c1::inner}}}}", "outer inner", "[...]"),
        ("{{c1::a {{c2,3::b {{c4::c::hint}}::hint}}::hint}}", "a b c", "[...]"),
        ("{{c1::<b>answer</b>\nline::hint}}", "<b>answer</b>\nline", "[...]"),
        ("{{c0,1,2::test}}", "test", "[...]"),
        ("{{c1,,3::test}}", "test", "[...]"),
        ("{{c65536,2::test}}", "test", "[...]"),
        ("{{c65536::test}}", "{{c65536::test}}", "{{c65536::test}}"),
        ("{{c1, 2::test}}", "{{c1, 2::test}}", "{{c1, 2::test}}"),
        ("{{c::test}}", "{{c::test}}", "{{c::test}}"),
        ("before {{c1::unclosed", "before ", "before "),
        ("before }} after", "before }} after", "before }} after"),
        (r"{{c1:: \( \frac{1}{\sqrt{\pi}} \) }}", r" \( \frac{1}{\sqrt{\pi}} \) ", "[...]"),
        (r"{{c1:: \[ \frac{1}{\sqrt{\pi}} \] }}", r" \[ \frac{1}{\sqrt{\pi}} \] ", "[...]"),
        (r"{{c1:: \(\pi\) and \(\sqrt{2}\) }}", r" \(\pi\) and \(\sqrt{2}\) ", "[...]"),
        (r"{{c1::foo \( bar}} baz", r"foo \( bar baz", "[...] baz"),
        (r"{{c1::foo \[ bar}} baz", r"foo \[ bar baz", "[...] baz"),
        (r"{{c1::\( a \]}} b", r"\( a \] b", "[...] b"),
        (r"{{c1::\( a {{c2::b}} \frac{1}{\sqrt{2}} \)}} c", r"\( a b \frac{1}{\sqrt{2}} \) c", "[...] c"),
        (r"\(x = {{c1::a}} + {{c2::\frac{1}{2} }}\)", r"\(x = a + \frac{1}{2} \)", r"\(x = [...] + [...]\)"),
        (
            "{{c1,2::image-occlusion:rect:left=10:top=20:width=30:height=40}}",
            "image-occlusion:rect:left=10:top=20:width=30:height=40",
            "[...]",
        ),
    ],
)
def test_matches_anki_parsing_with_summary_rendering(text: str, expanded: str, collapsed: str) -> None:
    assert render_cloze_summary(text, collapse=False) == expanded
    assert render_cloze_summary(text, collapse=True) == collapsed


def test_deduplicates_and_sorts_ordinals_like_anki() -> None:
    node = _parse("{{c3,1,3,2::answer::hint}}")[0]
    assert not isinstance(node, str)
    assert node.ordinals == (1, 2, 3)
    assert node.hint == "hint"


def test_uses_anki_ten_level_nesting_limit() -> None:
    text = "{{c1::" * 11 + "answer" + "}}" * 11
    assert render_cloze_summary(text, collapse=False) == "answer}}"
    assert render_cloze_summary(text, collapse=True) == "[...]}}"


def test_handles_long_ordinals_without_python_integer_conversion_limit() -> None:
    assert render_cloze_summary("{{c" + "9" * 5000 + ",2::answer}}", collapse=False) == "answer"
    assert render_cloze_summary("{{c" + "0" * 5000 + "1::answer}}", collapse=False) == "answer"
