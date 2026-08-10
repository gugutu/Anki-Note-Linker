import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const projectRoot = resolve(import.meta.dirname, "../../..");

test("links panel renders summaries and sends typed bridge commands", async ({ page }) => {
  const webRoot = resolve(projectRoot, "src/addon/web");
  const html = await readFile(resolve(webRoot, "links.html"), "utf8");
  await page.setContent(html);
  await page.addScriptTag({
    content: `
      var ankiContext = "BROWSER";
      window.commands = [];
      function getTr(message) { return message; }
      function pycmd(command) { window.commands.push(command); }
      function renderMathInElement() {}
    `,
  });
  await page.addScriptTag({ path: resolve(webRoot, "dist/links.js") });

  await page.evaluate(() => {
    window.reloadPage(
      [{ id: 1234567890123, mainField: "<b>Parent</b>", type: "parent" }],
      [{ id: 2345678901234, linkTitle: "Related", mainField: "Child", type: "child" }],
      false,
      true,
    );
  });

  await expect(page.locator(".backLink-button")).toContainText("Parent");
  await expect(page.locator(".forwardLink-button .link-button-title")).toHaveText("Related");
  await page.locator(".forwardLink-button").click();
  await expect.poll(() => page.evaluate(() => window.commands?.at(-1))).toBe(
    "AnkiNoteLinker-openNoteInBrowser2345678901234",
  );
});
