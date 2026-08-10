import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const projectRoot = resolve(import.meta.dirname, "../../..");

test("config toggles zoom controls symmetrically and submits validated values", async ({ page }) => {
  const webRoot = resolve(projectRoot, "src/addon/web");
  const html = await readFile(resolve(webRoot, "config.html"), "utf8");
  await page.setContent(html);
  await page.addScriptTag({
    content: `
      var isMac = true;
      var ankiLanguage = "en";
      var defaultConfig = {};
      var userConfig = {
        location: "right",
        positionRelativeToReviewer: "right",
        noteFieldsDisplayedInTheNoteSummary: ["Front"],
        "globalGraph-nodeDegreeSizing": "none",
        "globalGraph-nodeColor": [57, 125, 237],
        "globalGraph-highlightedNodeColor": [244, 165, 0],
        "globalGraph-tagNodeColor": [127, 199, 132],
        "globalGraph-backgroundColor": [16, 16, 32],
        splitRatio: "2:1",
        splitRatioBetweenLinksPageAndGraphPage: "1:1",
        splitRatioBetweenReviewerAndPanel: "4:1",
        linkMaxLines: 5
      };
      window.commands = [];
      function getTr(message) { return message; }
      function pycmd(command) { window.commands.push(command); }
    `,
  });
  await page.addScriptTag({ path: resolve(webRoot, "dist/config.js") });

  await page.locator("#advancedGraphZoomSummary").click();
  await expect(page.locator("#graphZoom-normalZoomSpeed")).toBeEnabled();
  await expect(page.locator("#graphZoom-smoothZoomSpeed")).toBeDisabled();

  await page.locator("#enableSmoothGraphZoom").check();
  await expect(page.locator("#graphZoom-normalZoomSpeed")).toBeDisabled();
  await expect(page.locator("#graphZoom-smoothZoomSpeed")).toBeEnabled();

  await page.locator("#button-ok").click();
  const command = await page.evaluate(() => window.commands?.at(-1));
  expect(command).toMatch(/^AnkiNoteLinker-config-ok/);
  expect(JSON.parse(command?.slice("AnkiNoteLinker-config-ok".length) ?? "{}")).toMatchObject({
    enableSmoothGraphZoom: true,
    noteFieldsDisplayedInTheNoteSummary: ["Front"],
  });
});
