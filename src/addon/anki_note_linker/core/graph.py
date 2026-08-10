"""Construct graph snapshots without depending on Anki or rendering code."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple, Union

NodeId = Union[int, str]


@dataclass(frozen=True)
class GraphRecord:
    note_id: int
    child_ids: Tuple[int, ...]
    summary: str
    tags: Tuple[str, ...] = ()


@dataclass
class GraphNode:
    node_id: NodeId
    child_ids: List[NodeId] = field(default_factory=list)
    parent_ids: Set[NodeId] = field(default_factory=set)
    summary: str = ""
    is_tag: bool = False


@dataclass(frozen=True)
class GraphConnection:
    source: NodeId
    target: NodeId


@dataclass
class GraphSnapshot:
    nodes: Dict[NodeId, GraphNode]
    connections: List[GraphConnection]

    def visible_nodes(self, include_single_nodes: bool) -> List[GraphNode]:
        if include_single_nodes:
            return list(self.nodes.values())
        return [node for node in self.nodes.values() if node.child_ids or node.parent_ids]


def build_global_graph_search(search_text: str, show_suspended: bool) -> str:
    """Combine the user's search with the suspended-card visibility setting."""
    search_text = search_text.strip()
    if show_suspended:
        return search_text
    if search_text:
        return f"({search_text}) -is:suspended"
    return "-is:suspended"


def build_global_graph_note_search(note_id: int, search_text: str, show_suspended: bool) -> str:
    """Scope the global graph search to one note for incremental refreshes."""
    graph_search = build_global_graph_search(search_text, show_suspended)
    if graph_search:
        return f"nid:{note_id} ({graph_search})"
    return f"nid:{note_id}"


def build_graph_snapshot(records: Iterable[GraphRecord], show_tags: bool) -> GraphSnapshot:
    record_list = list(records)
    allowed_ids = {record.note_id for record in record_list}
    nodes: Dict[NodeId, GraphNode] = {
        record.note_id: GraphNode(node_id=record.note_id, summary=record.summary) for record in record_list
    }

    for record in record_list:
        node = nodes[record.note_id]
        for child_id in record.child_ids:
            if child_id not in allowed_ids or child_id == record.note_id or child_id in node.child_ids:
                continue
            node.child_ids.append(child_id)
            nodes[child_id].parent_ids.add(record.note_id)

        if show_tags:
            for tag in dict.fromkeys(tag for tag in record.tags if tag):
                tag_node = nodes.setdefault(tag, GraphNode(node_id=tag, summary=tag, is_tag=True))
                if record.note_id not in tag_node.child_ids:
                    tag_node.child_ids.append(record.note_id)
                node.parent_ids.add(tag)

    connections = [
        GraphConnection(source=node.node_id, target=child_id) for node in nodes.values() for child_id in node.child_ids
    ]
    return GraphSnapshot(nodes=nodes, connections=connections)
