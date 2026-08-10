"""Note parsing, summary construction, and editor refresh decisions."""

import operator

from anki.errors import NotFoundError
from anki.notes import Note, NoteId
from aqt import mw
from aqt.editor import Editor

from ..core.links import child_link_titles, child_note_ids
from ..core.summaries import build_summary
from . import state
from .configuration import config
from .state import NoteNode


class NoteServiceMixin:
    def onLoadNote(self, editor: Editor):
        if editor.addMode:
            return
        self.editors.add(editor)
        self.refreshPage(editor, resetCenter=True, reason="loaded note")

    def onEditNote(self, note: Note):
        if note.id == 0:
            return
        showForwardLinkTitle = config["showForwardLinkTitleInLinksPage"]
        childLinkTitles = self.findChildLinkTitles(note.id, " ".join(note.fields)) if showForwardLinkTitle else None
        for editor in self.editors:
            if editor.note and (editor.note.id == note.id):
                if (
                    hasattr(editor, "noteNode")
                    and editor.noteNode.mainField == self.getMainField(note)
                    and operator.eq(editor.noteNode.childIds, self.findChildIds(note.id, " ".join(note.fields)))
                    and (
                        not showForwardLinkTitle or operator.eq(getattr(editor, "childLinkTitles", {}), childLinkTitles)
                    )
                ):
                    return
                else:
                    self.refreshPage(editor, adaptScale=False, reason="mainField or links of note changed")

        if state.globalGraph is not None and note.id in state.globalGraph.searchedIds:
            state.globalGraph.refreshGlobalGraph(note, "mainField or links of note changed")

    def idToNoteNode(self, nid: NoteId):
        try:
            note = mw.col.get_note(nid)
        except NotFoundError:
            return NoteNode(nid, [], set(), None)
        return self.noteToNoteNode(note)

    def noteToNoteNode(self, note: Note):
        return NoteNode(
            note.id,
            self.findChildIds(note.id, " ".join(note.fields)),
            self.findParentIds(note.id),
            self.getMainField(note),
        )

    def findChildIds(self, myId: NoteId, joinedFields: str, rangeIdSet=None):
        return [NoteId(note_id) for note_id in child_note_ids(joinedFields, int(myId), rangeIdSet)]

    def findChildLinkTitles(self, myId: NoteId, joinedFields: str, rangeIdSet=None):
        return {
            NoteId(note_id): title for note_id, title in child_link_titles(joinedFields, int(myId), rangeIdSet).items()
        }

    def findParentIds(self, myId):
        parentIds = set(mw.col.find_notes("[*|nid" + str(myId) + "]"))
        parentIds.discard(myId)
        return parentIds

    def getMainField(self, note: Note) -> str:
        fmap = mw.col.models.field_map(note.note_type())
        field_indexes = {field_name: details[0] for field_name, details in fmap.items()}
        return build_summary(
            note.fields,
            field_indexes,
            config["noteFieldsDisplayedInTheNoteSummary"],
            config.get("enableImagePreview", True),
            config["collapseClozeInLinksPage"],
        )
