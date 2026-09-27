export interface EditorMenuItem {
  action: string;
  label: string;
  requiresField: boolean;
  shortcut: string;
}

export interface EditorSettings {
  addMode: boolean;
  menuItems: EditorMenuItem[];
}

interface CodeEditor {
  getSelection: () => string;
  replaceSelection: (text: string) => void;
}

interface EditingInput {
  codeMirror?: { editor: Promise<CodeEditor> };
  element?: Promise<HTMLElement>;
  focus: () => void | Promise<void>;
}

export interface NoteEditorModule {
  instances: {
    focusedInput: { subscribe: (callback: (input: EditingInput | null) => void) => () => void };
  }[];
}

interface SelectionSnapshot {
  input: EditingInput | null;
  noteId: string | undefined;
  range: Range | null;
  selection: Selection | null;
  text: string;
}

function focusedInput(): EditingInput | null {
  const loadModule = (window as { require?: (name: string) => NoteEditorModule }).require;
  if (loadModule === undefined) return null;
  try {
    const editor = loadModule("anki/NoteEditor").instances[0];
    let input: EditingInput | null = null;
    const unsubscribe = editor?.focusedInput.subscribe((value) => { input = value; });
    unsubscribe?.();
    return input;
  } catch {
    return null;
  }
}

function currentNoteId(): string | undefined {
  return window.getNoteId === undefined ? undefined : String(window.getNoteId());
}

async function captureSelection(event?: MouseEvent): Promise<SelectionSnapshot> {
  const input = focusedInput();
  const noteId = currentNoteId();
  if (input?.codeMirror !== undefined) {
    return { input, noteId, range: null, selection: null, text: (await input.codeMirror.editor).getSelection() };
  }
  const element = input?.element === undefined
    ? event?.composedPath().find((target): target is Element => target instanceof Element)
    : await input.element;
  const root = element?.getRootNode();
  const selection = root instanceof ShadowRoot
    ? (root as ShadowRoot & { getSelection?: () => Selection | null }).getSelection?.() ?? window.getSelection()
    : window.getSelection();
  return {
    input,
    noteId,
    range: selection !== null && selection.rangeCount > 0 ? selection.getRangeAt(0).cloneRange() : null,
    selection,
    text: selection?.toString() ?? "",
  };
}

async function restoreSelection(snapshot: SelectionSnapshot): Promise<void> {
  await snapshot.input?.focus();
  if (snapshot.range?.startContainer.isConnected === true && snapshot.selection !== null) {
    snapshot.selection.removeAllRanges();
    snapshot.selection.addRange(snapshot.range);
  }
}

export function createEditorApi() {
  let settings: EditorSettings = { addMode: false, menuItems: [] };
  let composing = false;
  let insertion: SelectionSnapshot | null = null;
  let cancelMenuObserver: (() => void) | null = null;
  let menuVersion = 0;

  function isComposing(): boolean { return composing; }

  async function runAction(action: string, selection?: SelectionSnapshot): Promise<void> {
    if (isComposing() || !settings.menuItems.some((item) => item.action === action)) return;
    const snapshot = selection ?? await captureSelection();
    if (isComposing() || snapshot.noteId !== currentNoteId()) return;
    if (action.startsWith("insert")) {
      if (snapshot.input === null) return;
      insertion = snapshot;
    }
    if (snapshot.input !== null) {
      await restoreSelection(snapshot);
      if (isComposing() || snapshot.noteId !== currentNoteId()) return;
    }
    pycmd(`AnkiNoteLinker-editorAction${JSON.stringify({ action, selectedText: snapshot.text })}`);
  }

  async function pasteHtml(html: string, internal: boolean): Promise<void> {
    const snapshot = insertion ?? await captureSelection();
    insertion = null;
    if (isComposing() || snapshot.noteId !== currentNoteId()) return;
    await restoreSelection(snapshot);
    if (isComposing() || snapshot.noteId !== currentNoteId()) return;
    if (snapshot.input?.codeMirror !== undefined) {
      (await snapshot.input.codeMirror.editor).replaceSelection(html);
    } else {
      window.pasteHTML?.(html, internal, false);
    }
  }

  async function onDoubleClick(event: MouseEvent): Promise<void> {
    if (isComposing()) return;
    const snapshot = await captureSelection(event);
    if (isComposing() || snapshot.noteId !== currentNoteId()) return;
    if (/^nid\d{13}$/.test(snapshot.text)) {
      pycmd(`AnkiNoteLinker-openNoteInNewEditor${snapshot.text.slice(3)}`);
    } else if (/^new\d{8}$/.test(snapshot.text)) {
      pycmd(`AnkiNoteLinker-openAddNoteWindow${snapshot.text.slice(3)}`);
    }
  }

  function extendMenu(root: Element, snapshot: SelectionSnapshot): void {
    let timeout = 0;
    const observer = new MutationObserver(appendItems);
    function stop(): void {
      observer.disconnect();
      window.clearTimeout(timeout);
    }
    function appendItems(): void {
      const menu = root.querySelector<HTMLElement>('[role="menu"]');
      const nativeItem = menu?.querySelector<HTMLElement>('[role="menuitem"]');
      if (menu === null || nativeItem === null || nativeItem === undefined) return;
      stop();
      menu.querySelectorAll("[data-note-linker]").forEach((item) => item.remove());
      const items = settings.menuItems.filter((item) => item.requiresField ? snapshot.input !== null : !settings.addMode);
      if (items.length === 0) return;
      const separator = document.createElement("div");
      separator.dataset.noteLinker = "separator";
      separator.setAttribute("role", "separator");
      separator.style.borderTop = "1px solid var(--border)";
      separator.style.margin = "4px 0";
      menu.append(separator);
      for (const item of items) {
        const button = nativeItem.cloneNode(false) as HTMLElement;
        button.dataset.noteLinker = item.action;
        button.tabIndex = 0;
        button.style.display = "flex";
        button.style.justifyContent = "space-between";
        button.style.gap = "24px";
        button.style.whiteSpace = "normal";
        const label = document.createElement("span");
        label.textContent = item.label;
        const shortcut = document.createElement("span");
        shortcut.textContent = item.shortcut;
        shortcut.style.opacity = "0.7";
        shortcut.style.flexShrink = "0";
        button.append(label, shortcut);
        button.addEventListener("click", () => { void runAction(item.action, snapshot); });
        button.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            void runAction(item.action, snapshot);
          }
        });
        menu.append(button);
      }
      requestAnimationFrame(() => {
        if (!menu.isConnected) return;
        menu.style.maxWidth = `${String(window.innerWidth)}px`;
        const rect = menu.getBoundingClientRect();
        menu.style.left = `${String(Math.max(0, Math.min(rect.left, window.innerWidth - rect.width)))}px`;
        menu.style.top = `${String(Math.max(0, Math.min(rect.top, window.innerHeight - rect.height)))}px`;
        menu.style.maxHeight = `${String(window.innerHeight)}px`;
        menu.style.overflowY = "auto";
      });
    }
    cancelMenuObserver = stop;
    observer.observe(root, { childList: true, subtree: true });
    timeout = window.setTimeout(stop, 500);
    appendItems();
  }

  async function onContextMenu(event: MouseEvent): Promise<void> {
    cancelMenuObserver?.();
    const version = ++menuVersion;
    if (isComposing() || settings.menuItems.length === 0) return;
    const root = event.composedPath().find((target): target is Element => target instanceof Element && target.matches(".note-editor"));
    if (root === undefined) return;
    const snapshot = await captureSelection(event);
    if (isComposing() || version !== menuVersion || snapshot.noteId !== currentNoteId()) return;
    // The native Svelte menu renders asynchronously. Preserve its built-in actions.
    extendMenu(root, snapshot);
  }

  window.addEventListener("dblclick", (event) => { void onDoubleClick(event); });
  window.addEventListener("contextmenu", (event) => { void onContextMenu(event); }, true);
  window.addEventListener("compositionstart", () => { composing = true; }, true);
  window.addEventListener("compositionend", () => { composing = false; }, true);
  window.addEventListener("pagehide", () => { cancelMenuObserver?.(); });

  return { initialize: (options: EditorSettings) => { settings = options; }, pasteHtml, runAction };
}

export type EditorBrowserApi = ReturnType<typeof createEditorApi>;

window.AnkiNoteLinkerEditor ??= createEditorApi();
