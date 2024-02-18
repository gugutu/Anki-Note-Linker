class Connection:
    def __init__(self, source_id, target_id):
        self.source = source_id
        self.target = target_id


class NoteNode:
    def __init__(self, nid: int, childIds: list[int], parentIds: list[int], mainField: str):
        self.id = nid
        self.childIds: list[int] = childIds
        self.parentIds: list[int] = parentIds
        self.mainField: str = mainField

    def toJsNoteNode(self, type):
        return JsNoteNode(self.id, self.mainField, type)


class JsNoteNode:
    def __init__(self, nid: int, mainField: str, type: str):
        self.id = nid
        self.mainField = mainField
        self.type = type
