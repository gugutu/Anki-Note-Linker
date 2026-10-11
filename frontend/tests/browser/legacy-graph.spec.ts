import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const webRoot = resolve(import.meta.dirname, "../../../src/addon/web");

test("legacy graph still initializes and refreshes with the compact D3 bundle", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addScriptTag({
    content: `
      var ankiContext = "GLOBAL_GRAPH";
      var enableImagePreview = true;
      var graphZoomConfig = {};
      function getTr(message) { return message; }
      function pycmd() {}
      function renderMathInElement() {}
    `,
  });
  for (const path of ["dist/vendor/d3.js", "dist/vendor/force-graph.js", "dist/graph-core.js"]) {
    await page.addScriptTag({ path: resolve(webRoot, path) });
  }
  const html = await readFile(resolve(webRoot, "graph.html"), "utf8");
  await page.setContent(html);
  await expect(page.locator("#graph canvas")).toBeVisible();
  await page.evaluate(async () => {
    const reload = Reflect.get(window, "reloadPage") as unknown as typeof window.AnkiNoteLinkerNewGraph.reloadPage;
    await reload(
      [{ id: 1, mainField: "First", type: "normal" }, { id: 2, mainField: "Second", type: "normal" }],
      [{ source: 1, target: 2 }],
      true,
    );
  });
  expect(await page.evaluate(() => Object.keys(d3).sort())).toEqual([
    "forceCollide", "forceLink", "forceManyBody", "forceSimulation", "forceX", "forceY",
  ]);
  expect(errors).toEqual([]);
});
