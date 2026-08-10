from contextlib import suppress
from typing import Any, Optional

import aqt
from aqt import Qt


def remove_hook_safely(hook: Any, callback: Any) -> None:
    with suppress(ValueError, AttributeError):
        hook.remove(callback)


def enable_immediate_profile_close(window: Any) -> None:
    """Allow Anki's legacy top-level-window cleanup to close this window."""
    window.silentlyClose = True
    attribute_scope = getattr(Qt, "WidgetAttribute", Qt)
    delete_on_close = getattr(attribute_scope, "WA_DeleteOnClose", None)
    if delete_on_close is not None:
        window.setAttribute(delete_on_close)


def cleanup_webview(owner: Any, attribute: str) -> None:
    web = getattr(owner, attribute, None)
    if web is None:
        return

    setattr(owner, attribute, None)
    with suppress(RuntimeError):
        web.cleanup()
    with suppress(RuntimeError):
        web.deleteLater()


def register_managed_dialog(window: Any, kind: str) -> Optional[str]:
    """Make custom editor windows participate in Anki's awaited shutdown flow."""
    dialogs = getattr(aqt, "dialogs", None)
    entries = getattr(dialogs, "_dialogs", None)
    if isinstance(entries, dict):
        key = f"AnkiNoteLinker-{kind}-{id(window)}"
        entries[key] = [type(window), window]
        window._anki_note_linker_dialog_key = key
        return key

    # Very old Anki versions do not expose the dialog registry. They can still
    # close these windows through the legacy top-level-window fallback.
    window.silentlyClose = True
    return None


def mark_managed_dialog_closed(window: Any) -> None:
    key = getattr(window, "_anki_note_linker_dialog_key", None)
    dialogs = getattr(aqt, "dialogs", None)
    entries = getattr(dialogs, "_dialogs", None)
    if key is not None and isinstance(entries, dict) and key in entries:
        entries[key][1] = None
    window._anki_note_linker_dialog_key = None
