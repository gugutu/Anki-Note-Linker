import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const editorScript = resolve(import.meta.dirname, "../../../src/addon/web/dist/editor.js");

async function loadEditor(page: Page, addMode = false): Promise<void> {
  await page.setContent('<div class="note-editor"><div id="field-host"></div></div>');
  await page.addScriptTag({ content: `
    const root = document.querySelector('.note-editor');
    const shadow = document.getElementById('field-host').attachShadow({ mode: 'open' });
    const field = document.createElement('div');
    field.id = 'field';
    field.contentEditable = 'true';
    field.textContent = '中文标题';
    shadow.appendChild(field);
    window.commands = [];
    window.pycmd = command => window.commands.push(command);
    window.getNoteId = () => document.body.dataset.noteId || '1234567890123';
    const input = { element: Promise.resolve(field), focus: async () => { await Promise.resolve(); field.focus(); } };
    window.require = () => ({ instances: [{ focusedInput: { subscribe: callback => { callback(input); return () => {}; } } }] });
    window.pasteHTML = html => document.execCommand('insertHTML', false, html);
    root.addEventListener('contextmenu', event => {
      event.preventDefault();
      setTimeout(() => {
        root.querySelector('[role="menu"]')?.remove();
        const menu = document.createElement('div');
        menu.setAttribute('role', 'menu');
        Object.assign(menu.style, { position: 'fixed', left: event.clientX + 'px', top: event.clientY + 'px' });
        for (const label of ['Paste', 'Copy image']) {
          const item = document.createElement('div');
          item.setAttribute('role', 'menuitem');
          item.className = 'native-menu-item';
          item.textContent = label;
          item.addEventListener('click', () => window.commands.push('native:' + label));
          menu.appendChild(item);
        }
        menu.addEventListener('click', () => menu.remove());
        root.appendChild(menu);
      }, 20);
    });
  ` });
  await page.addScriptTag({ path: editorScript });
  await page.evaluate((adding) => {
    window.AnkiNoteLinkerEditor?.initialize({
      addMode: adding,
      menuItems: [
        { action: "insertLinkTemplate", label: "插入链接模板", shortcut: "Ctrl+Alt+T", requiresField: true },
        { action: "copyNoteID", label: "复制当前笔记ID", shortcut: "Ctrl+Alt+C", requiresField: false },
      ],
    });
  }, addMode);
}

async function selectText(page: Page, text = "中文标题"): Promise<void> {
  await page.evaluate((selected) => {
    const field = document.getElementById("field-host")?.shadowRoot?.querySelector<HTMLElement>("#field");
    if (field === null || field === undefined) throw new Error("Test editor field is missing");
    field.textContent = selected;
    field.focus();
    const range = document.createRange();
    range.selectNodeContents(field);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, text);
}

async function openMenu(page: Page): Promise<void> {
  await page.locator("#field").dispatchEvent("contextmenu", { bubbles: true, composed: true, clientX: 15, clientY: 15 });
  await expect(page.locator('[data-note-linker="insertLinkTemplate"]')).toBeVisible();
}

test("new editor menu preserves native actions and inserts at the captured selection", async ({ page }) => {
  await loadEditor(page);
  await selectText(page);
  await openMenu(page);
  await expect(page.getByRole("menuitem", { name: "Copy image", exact: true })).toBeVisible();
  await expect(page.locator('[data-note-linker="insertLinkTemplate"]')).toHaveClass("native-menu-item");
  await page.locator('[data-note-linker="insertLinkTemplate"]').click();
  await expect.poll(() => page.evaluate(() => window.commands?.at(-1))).toBe(
    `AnkiNoteLinker-editorAction${JSON.stringify({ action: "insertLinkTemplate", selectedText: "中文标题" })}`,
  );
  await page.evaluate(async () => {
    await window.AnkiNoteLinkerEditor?.pasteHtml("[中文标题|nid]", true);
  });
  await expect(page.locator("#field")).toHaveText("[中文标题|nid]");
  await openMenu(page);
  await page.getByRole("menuitem", { name: "Copy image", exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.commands?.at(-1))).toBe("native:Copy image");
});

test("add-note editor omits actions that require a saved note", async ({ page }) => {
  await loadEditor(page, true);
  await openMenu(page);
  await expect(page.locator('[data-note-linker="copyNoteID"]')).toHaveCount(0);
});

test("double-click listener supports shadow-root selections and installs once", async ({ page }) => {
  await loadEditor(page);
  await page.addScriptTag({ path: editorScript });
  await selectText(page, "nid2345678901234");
  await page.locator("#field").dispatchEvent("dblclick", { bubbles: true, composed: true });
  await expect.poll(() => page.evaluate(() => window.commands)).toEqual(["AnkiNoteLinker-openNoteInNewEditor2345678901234"]);

  await selectText(page, "new12345678");
  await page.locator("#field").dispatchEvent("dblclick", { bubbles: true, composed: true });
  await expect.poll(() => page.evaluate(() => window.commands?.at(-1))).toBe("AnkiNoteLinker-openAddNoteWindow12345678");
});

test("legacy editor double-click works without new editor APIs", async ({ page }) => {
  await page.setContent('<div id="legacy-field" contenteditable="true">nid2345678901234</div>');
  await page.addScriptTag({ content: "window.commands = []; window.pycmd = command => window.commands.push(command);" });
  await page.addScriptTag({ path: editorScript });
  await page.evaluate(() => {
    const field = document.getElementById("legacy-field");
    if (field === null) throw new Error("Test editor field is missing");
    const range = document.createRange();
    range.selectNodeContents(field);
    window.getSelection()?.addRange(range);
  });
  await page.locator("#legacy-field").dispatchEvent("dblclick", { bubbles: true });
  await expect.poll(() => page.evaluate(() => window.commands)).toEqual(["AnkiNoteLinker-openNoteInNewEditor2345678901234"]);
});

test("editor actions stay idle during IME composition", async ({ page }) => {
  await loadEditor(page);
  await selectText(page, "nid2345678901234");
  await page.locator("#field").dispatchEvent("compositionstart", { bubbles: true, composed: true });
  await page.locator("#field").dispatchEvent("dblclick", { bubbles: true, composed: true });
  await page.evaluate(async () => { await window.AnkiNoteLinkerEditor?.runAction("insertLinkTemplate"); });
  expect(await page.evaluate(() => window.commands)).toEqual([]);
  await page.locator("#field").dispatchEvent("compositionend", { bubbles: true, composed: true });
  await page.locator("#field").dispatchEvent("dblclick", { bubbles: true, composed: true });
  await expect.poll(() => page.evaluate(() => window.commands?.length)).toBe(1);
});

test("stale menu actions do not insert into a different note", async ({ page }) => {
  await loadEditor(page);
  await selectText(page);
  await openMenu(page);
  await page.evaluate(() => { document.body.dataset.noteId = "2345678901234"; });
  await page.locator('[data-note-linker="insertLinkTemplate"]').click();
  expect(await page.evaluate(() => window.commands)).toEqual([]);
});

test("new editor actions use CodeMirror selection and insertion in HTML mode", async ({ page }) => {
  await loadEditor(page);
  await page.addScriptTag({ content: `
    (() => {
    const code = { getSelection: () => '<b>标题</b>', replaceSelection: text => { document.body.dataset.insertedHtml = text; } };
    const input = { codeMirror: { editor: Promise.resolve(code) }, focus: async () => {} };
    window.require = () => ({ instances: [{ focusedInput: { subscribe: callback => { callback(input); return () => {}; } } }] });
    })();
  ` });
  await page.evaluate(async () => {
    await window.AnkiNoteLinkerEditor?.runAction("insertLinkTemplate");
    await window.AnkiNoteLinkerEditor?.pasteHtml("[标题|nid]", true);
  });
  expect(await page.evaluate(() => window.commands?.at(-1))).toBe(
    `AnkiNoteLinker-editorAction${JSON.stringify({ action: "insertLinkTemplate", selectedText: "<b>标题</b>" })}`,
  );
  expect(await page.evaluate(() => document.body.dataset.insertedHtml)).toBe("[标题|nid]");
});
