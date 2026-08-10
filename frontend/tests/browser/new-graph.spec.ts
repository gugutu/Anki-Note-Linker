import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const projectRoot = resolve(import.meta.dirname, "../../..");

test("new graph initializes with WebGL and renders supplied nodes", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const webRoot = resolve(projectRoot, "src/addon/web");
  const html = await readFile(resolve(webRoot, "newGraph.html"), "utf8");
  await page.setContent(html);
  await page.addScriptTag({
    content: `
      var ankiContext = "GLOBAL_GRAPH";
      var enableImagePreview = true;
      var enableSmoothGraphZoom = false;
      var graphZoomConfig = {};
      window.commands = [];
      function getTr(message) { return message; }
      function pycmd(command) { window.commands.push(command); }
      function renderMathInElement() {}
    `,
  });
  await page.addScriptTag({ path: resolve(webRoot, "dist/vendor/d3.js") });
  await page.addScriptTag({ path: resolve(webRoot, "dist/vendor/pixi.js") });
  await page.addScriptTag({ path: resolve(webRoot, "dist/new-graph.js") });

  await expect(page.locator("canvas")).toBeVisible();
  await page.evaluate(async () => {
    await window.AnkiNoteLinkerNewGraph.reloadPage(
      [
        { id: 1, mainField: "First", type: "normal" },
        { id: 2, mainField: "Second", type: "highlight" },
      ],
      [{ source: 1, target: 2 }],
      true,
      true,
    );
  });

  await expect(page.locator(".circleText")).toHaveCount(2);
  await expect.poll(async () => page.evaluate(() => {
    const source = document.querySelector("canvas");
    if (source === null) return 0;
    const sample = document.createElement("canvas");
    sample.width = source.width;
    sample.height = source.height;
    const context = sample.getContext("2d");
    if (context === null) return 0;
    context.drawImage(source, 0, 0);
    const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
    let changed = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] !== 16 || pixels[index + 1] !== 16 || pixels[index + 2] !== 32) changed += 1;
    }
    return changed;
  })).toBeGreaterThan(50);
  expect(await page.evaluate(() => window.commands)).not.toContain("AnkiNoteLinker-switchToOldRenderer");
  expect(errors).toEqual([]);
});
