"""Load Anki Note Linker when imported as an Anki add-on package."""

if __package__:
    from .anki_note_linker.runtime.controller import initialize

    initialize()
    __all__ = ["initialize"]
else:
    __all__ = []
