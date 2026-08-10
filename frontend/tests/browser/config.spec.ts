import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const projectRoot = resolve(import.meta.dirname, "../../..");
const webRoot = resolve(projectRoot, "src/addon/web");

async function loadConfigPage(page: Page, language: string, useTranslations = false): Promise<void> {
  const html = await readFile(resolve(webRoot, "config.html"), "utf8");
  await page.setContent(html);
  await page.addScriptTag({
    content: `
      var isMac = true;
      var ankiLanguage = ${JSON.stringify(language)};
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
      function pycmd(command) { window.commands.push(command); }
      ${useTranslations ? "" : "function getTr(message) { return message; }"}
    `,
  });
  if (useTranslations) {
    await page.addScriptTag({ path: resolve(webRoot, "js/translation.js") });
  }
  await page.addScriptTag({ path: resolve(webRoot, "dist/config.js") });
}

test("config toggles zoom controls symmetrically and submits validated values", async ({ page }) => {
  await loadConfigPage(page, "en");

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
    "globalGraph-defaultShowSuspended": false,
    noteFieldsDisplayedInTheNoteSummary: ["Front"],
  });
});

test("config translates advanced graph settings and dynamic controls into Chinese", async ({ page }) => {
  await loadConfigPage(page, "zh-CN", true);

  await expect(page.locator("#advancedGraphZoomSummary")).toHaveText("高级关系图缩放设置");
  await expect(page.locator("label.graphZoom-zoomInLimit")).toHaveText("放大限制:");
  await expect(page.locator("label.graphZoom-normalZoomSpeed")).toHaveText("普通缩放速度:");
  await expect(page.locator("#noteFieldsDisplayedInTheNoteSummary button")).toHaveAttribute("title", "移除字段");
  await page.locator("#advancedGraphZoomSummary").click();

  const helpMessages: string[] = [];
  page.on("dialog", async (dialog) => {
    helpMessages.push(dialog.message());
    await dialog.dismiss();
  });

  await page.locator("#graphZoom-zoomInLimit-help").click();
  await page.locator("#graphZoom-normalZoomSpeed-help").click();
  await page.locator("#enableSmoothGraphZoom").check();
  await page.locator("#graphZoom-smoothZoomSpeed-help").click();
  await page.locator("#graphZoom-smoothStepLimit-help").click();

  await expect.poll(() => helpMessages).toHaveLength(4);
  expect(helpMessages).toEqual([
    "控制关系图最多能放大到什么程度。数值越大，越适合近距离查看节点；数值越小，越早停止放大。范围：1-100。默认值：100。",
    "控制未启用平滑缩放时，每次滚动滚轮对视图缩放的影响。数值越大，缩放越快；数值越小，缩放越慢、越稳。范围：0.1-5。默认值：1。",
    "控制启用平滑缩放时，每次滚动滚轮对目标缩放的影响。数值越大，目标变化越快；数值越小，移动越柔和。范围：0.1-5。默认值：1。",
    "限制平滑模式下单次滚轮动作最多能改变多少目标缩放。数值越小，越不容易突然跳变；数值越大，快速滚动时缩放力度更强。范围：0.01-1。默认值：0.15。",
  ]);
});
