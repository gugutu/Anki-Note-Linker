from anki_note_linker.core.graph import (
    GraphRecord,
    build_global_graph_note_search,
    build_global_graph_search,
    build_graph_snapshot,
)


def test_builds_search_for_suspended_note_visibility() -> None:
    assert build_global_graph_search("deck:current", show_suspended=False) == "(deck:current) -is:suspended"
    assert build_global_graph_search("", show_suspended=False) == "-is:suspended"
    assert build_global_graph_search("  tag:keep  ", show_suspended=True) == "tag:keep"
    assert build_global_graph_note_search(123, "tag:keep OR tag:later", False) == (
        "nid:123 ((tag:keep OR tag:later) -is:suspended)"
    )
    assert build_global_graph_note_search(123, "", True) == "nid:123"


def test_builds_unique_note_and_tag_connections() -> None:
    snapshot = build_graph_snapshot(
        [
            GraphRecord(
                note_id=1234567890123,
                child_ids=(2345678901234, 2345678901234, 1234567890123, 9999999999999),
                summary="first",
                tags=("topic", "topic", ""),
            ),
            GraphRecord(note_id=2345678901234, child_ids=(), summary="second", tags=("topic",)),
            GraphRecord(note_id=3456789012345, child_ids=(), summary="single"),
        ],
        show_tags=True,
    )

    assert set(snapshot.nodes) == {1234567890123, 2345678901234, 3456789012345, "topic"}
    assert [(connection.source, connection.target) for connection in snapshot.connections] == [
        (1234567890123, 2345678901234),
        ("topic", 1234567890123),
        ("topic", 2345678901234),
    ]
    assert snapshot.nodes[2345678901234].parent_ids == {1234567890123, "topic"}


def test_filters_unconnected_nodes_without_mutating_snapshot() -> None:
    snapshot = build_graph_snapshot(
        [
            GraphRecord(1234567890123, (2345678901234,), "first"),
            GraphRecord(2345678901234, (), "second"),
            GraphRecord(3456789012345, (), "single"),
        ],
        show_tags=False,
    )

    assert [node.node_id for node in snapshot.visible_nodes(False)] == [1234567890123, 2345678901234]
    assert [node.node_id for node in snapshot.visible_nodes(True)] == [
        1234567890123,
        2345678901234,
        3456789012345,
    ]
