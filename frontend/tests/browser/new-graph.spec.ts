import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import type { Application, GraphicsContext } from "pixi.js";

declare global {
  interface Window {
    graphTestApp?: Application;
    oldGraphContexts?: GraphicsContext[];
  }
}

const projectRoot = resolve(import.meta.dirname, "../../..");
const testNodeId = 123;

async function initializeNewGraph(page: Page, inspectRenderer = false): Promise<void> {
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
  if (inspectRenderer) {
    await page.evaluate(() => {
      const initialize: Application["init"] = Reflect.get(PIXI.Application.prototype, "init");
      PIXI.Application.prototype.init = async function (this: Application, options) {
        await initialize.call(this, options);
        window.graphTestApp = this;
      };
    });
  }
  await page.addScriptTag({ path: resolve(webRoot, "dist/new-graph.js") });
  await expect(page.locator("canvas")).toBeVisible();
}

async function loadSingleNode(page: Page): Promise<{ x: number; y: number }> {
  await page.evaluate(async (nodeId) => {
    await window.AnkiNoteLinkerNewGraph.reloadPage(
      [{ id: nodeId, mainField: "Node", type: "normal", x: 0, y: 0, vx: 0, vy: 0 }],
      [],
      false,
      false,
    );
  }, testNodeId);
  await expect(page.locator(".circleText")).toHaveCount(1);
  const canvas = await page.locator("canvas").boundingBox();
  if (canvas === null) {
    throw new Error("Graph canvas has no bounding box.");
  }
  return { x: canvas.x + canvas.width / 2, y: canvas.y + canvas.height / 2 };
}

test("new graph initializes with WebGL and renders supplied nodes", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await initializeNewGraph(page);
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
  expect(await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    return canvas === null ? 0 : canvas.width / canvas.clientWidth;
  })).toBe(1.5);
  expect(errors).toEqual([]);
});

test("graph refreshes release old GPU contexts and keep the replacement graph usable", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await initializeNewGraph(page, true);
  for (let index = 0; index < 5; index += 1) {
    await page.evaluate(async () => {
      const app = window.graphTestApp;
      if (app === undefined) throw new Error("Graph application was not captured");
      window.oldGraphContexts = [...new Set(app.stage.children.flatMap((child) => (
        child instanceof PIXI.Graphics
          ? [child.context]
          : child.children.filter((item): item is import("pixi.js").Graphics => item instanceof PIXI.Graphics)
            .map((item) => item.context)
      )))];
      await window.AnkiNoteLinkerNewGraph.reloadPage(
        [
          { id: 1, mainField: "First", type: "normal", fx: 0, fy: 0 },
          { id: 2, mainField: "Second", type: "normal", fx: 100, fy: 0 },
        ],
        [{ source: 1, target: 2 }],
        false,
        false,
      );
    });
    expect(await page.evaluate(() => window.oldGraphContexts?.every((context) => context.destroyed))).toBe(true);
    await expect(page.locator(".circleText")).toHaveCount(2);
  }
  const canvas = await page.locator("canvas").boundingBox();
  if (canvas === null) throw new Error("Graph canvas has no bounding box");
  await page.mouse.click(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await expect.poll(() => page.evaluate(() => window.commands)).toEqual(["AnkiNoteLinker-openNoteInPreviewer1"]);
  expect(errors).toEqual([]);
});

test("large graphs recreate visible labels after zooming out and back in", async ({ page }) => {
  await initializeNewGraph(page, true);
  await page.evaluate(async () => {
    await window.AnkiNoteLinkerNewGraph.reloadPage(
      [
        { id: 1, mainField: "Visible", type: "normal", fx: 0, fy: 0 },
        ...Array.from({ length: 1000 }, (_, index) => ({
          id: index + 2, mainField: "Outside viewport", type: "normal", fx: 10000 + index * 100, fy: 0,
        })),
      ],
      [],
      false,
      false,
    );
  });
  await expect(page.locator(".circleText")).toHaveCount(1);
  await page.evaluate(() => { window.graphTestApp?.stage.scale.set(0.1); });
  await expect(page.locator(".circleText")).toHaveCount(0);
  await page.evaluate(() => { window.graphTestApp?.stage.scale.set(1); });
  await expect(page.locator(".circleText")).toHaveCount(1);
  await expect(page.locator(".circleText")).toHaveText("Visible");
});

test("shared node listeners keep hover labels attached to the correct node", async ({ page }) => {
  await initializeNewGraph(page, true);
  await page.evaluate(async () => {
    await window.AnkiNoteLinkerNewGraph.reloadPage(
      [
        { id: 1, mainField: "First node", type: "normal", fx: -100, fy: 0 },
        { id: 2, mainField: "Second node", type: "normal", fx: 100, fy: 0 },
      ],
      [],
      false,
    );
  });
  await expect(page.locator(".circleText")).toHaveCount(2);
  const points = await page.evaluate(() => window.graphTestApp?.stage.children.map((circle) => {
    const point = circle.toGlobal({ x: 0, y: 0 });
    return { x: point.x, y: point.y };
  }));
  const first = points?.[0];
  const second = points?.[1];
  if (first === undefined || second === undefined) throw new Error("Graph nodes were not captured");
  await page.mouse.move(first.x, first.y);
  await expect(page.locator(".label")).toHaveText("First node");
  await page.mouse.move(second.x, second.y);
  await expect(page.locator(".label")).toHaveText("Second node");
  await page.mouse.move(second.x, second.y + 100);
  await expect(page.locator(".label")).toHaveCount(0);
});

for (const interaction of [
  { button: "left", command: `AnkiNoteLinker-openNoteInPreviewer${String(testNodeId)}` },
  { button: "right", command: `AnkiNoteLinker-openNoteInNewEditor${String(testNodeId)}` },
] as const) {
  test(`${interaction.button} click tolerates small pointer movement`, async ({ page }) => {
    await initializeNewGraph(page);
    const point = await loadSingleNode(page);

    await page.mouse.move(point.x, point.y);
    await page.mouse.down({ button: interaction.button });
    await page.mouse.move(point.x + 3, point.y);
    await page.mouse.up({ button: interaction.button });

    await expect.poll(() => page.evaluate(() => window.commands)).toEqual([interaction.command]);
  });

  test(`${interaction.button} button drags a node without opening it`, async ({ page }) => {
    await initializeNewGraph(page);
    const point = await loadSingleNode(page);
    const nodeText = page.locator(".circleText");
    const initialLeft = Number.parseFloat(await nodeText.evaluate((element) => element.style.left));

    await page.mouse.move(point.x, point.y);
    await page.mouse.down({ button: interaction.button });
    await page.mouse.move(point.x + 20, point.y);
    await expect.poll(async () => (
      Number.parseFloat(await nodeText.evaluate((element) => element.style.left))
    )).toBeGreaterThan(initialLeft + 10);
    await page.mouse.up({ button: interaction.button });

    expect(await page.evaluate(() => window.commands)).toEqual([]);
  });
}
