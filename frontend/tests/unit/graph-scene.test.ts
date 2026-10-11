import { Container, Graphics, GraphicsContext, Rectangle, type Application } from "pixi.js";
import renderMath from "katex/contrib/auto-render";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_NODE_COLORS } from "../../src/graph/node-graphics";
import { GraphScene } from "../../src/graph/scene";
import type { GraphNode } from "../../src/graph/types";
import { createPointTransform, ViewportBoundary } from "../../src/graph/viewport";

vi.hoisted(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

function node(id: number, x = 0): GraphNode {
  return { id, mainField: "Note", renderText: "Note", type: "normal", x, y: 0 };
}

function createScene() {
  vi.stubGlobal("PIXI", { Container, Graphics, GraphicsContext, Rectangle });
  vi.stubGlobal("renderMathInElement", vi.fn());
  const stage = new Container();
  stage.position.set(window.innerWidth / 2, window.innerHeight / 2);
  const textContainer = document.createElement("div");
  document.body.append(textContainer);
  const transform = createPointTransform(stage);
  const boundary = new ViewportBoundary(stage, transform);
  boundary.update();
  const app = { stage } as Application;
  const scene = new GraphScene(app, textContainer, boundary, transform);
  const handlers = { pointerDown: vi.fn(), pointerEnter: vi.fn(), pointerLeave: vi.fn() };
  return { scene, stage, textContainer, handlers };
}

function contexts(stage: Container): GraphicsContext[] {
  return [...new Set(stage.children.flatMap((child) => (
    child instanceof Graphics
      ? [child.context]
      : child.children.filter((item): item is Graphics => item instanceof Graphics).map((item) => item.context)
  )))];
}

describe("graph scene memory", () => {
  it("releases every old shared context without destroying the new scene", () => {
    const { scene, stage, handlers } = createScene();
    const first = node(1);
    const second = node(2, 100);
    scene.rebuild([first, second], [{ source: first, target: second }], DEFAULT_NODE_COLORS, handlers);
    const oldContexts = contexts(stage);
    expect(oldContexts).toHaveLength(3);
    const releases = oldContexts.map((context) => vi.spyOn(context, "destroy"));

    scene.rebuild([node(3)], [], DEFAULT_NODE_COLORS, handlers);
    scene.layout(16);

    for (const release of releases) expect(release).toHaveBeenCalledOnce();
    expect(oldContexts.every((context) => context.destroyed)).toBe(true);
    expect(contexts(stage)).toHaveLength(1);
    expect(contexts(stage).every((context) => !context.destroyed)).toBe(true);
    expect(stage.children).toHaveLength(1);
    scene.destroy();
    scene.destroy();
  });

  it("allocates text only for visible nodes and releases it when they leave the viewport", () => {
    const { scene, textContainer, handlers } = createScene();
    const visibleNode = node(1);
    const nodes = [visibleNode, ...Array.from({ length: 1000 }, (_, index) => node(index + 2, 10000 + index * 100))];
    const createElement = vi.spyOn(document, "createElement");
    const divCount = () => createElement.mock.calls.filter(([tag]) => tag === "div").length;

    scene.rebuild(nodes, [], DEFAULT_NODE_COLORS, handlers);
    expect(divCount()).toBe(0);
    scene.layout(16);
    expect(divCount()).toBe(1);
    expect(textContainer.children).toHaveLength(1);
    const originalText = textContainer.firstChild;
    expect(renderMathInElement).toHaveBeenCalledOnce();
    expect(renderMathInElement).toHaveBeenCalledWith(originalText, expect.any(Object));
    scene.layout(16);
    expect(renderMathInElement).toHaveBeenCalledOnce();

    visibleNode.x = 20000;
    scene.layout(16);
    expect(textContainer.children).toHaveLength(0);
    expect(originalText?.isConnected).toBe(false);

    visibleNode.x = 0;
    scene.layout(16);
    expect(divCount()).toBe(2);
    expect(textContainer.children).toHaveLength(1);
    expect(textContainer.firstChild).not.toBe(originalText);
    scene.destroy();
  });

  it("releases labels when zoomed out and recreates them when zoomed back in", () => {
    const { scene, stage, textContainer, handlers } = createScene();
    scene.rebuild([node(1)], [], DEFAULT_NODE_COLORS, handlers);
    scene.layout(16);
    const text = textContainer.firstChild;
    expect(text).not.toBeNull();

    stage.scale.set(0.1);
    scene.layout(16);
    expect(textContainer.children).toHaveLength(0);
    stage.scale.set(1);
    scene.layout(16);
    expect(textContainer.children).toHaveLength(1);
    expect(textContainer.firstChild).not.toBe(text);

    const activeContexts = contexts(stage);
    scene.destroy();
    expect(stage.children).toHaveLength(0);
    expect(textContainer.children).toHaveLength(0);
    expect(activeContexts.every((context) => context.destroyed)).toBe(true);
  });

  it("renders formulas again after a label is released and recreated", () => {
    const { scene, stage, textContainer, handlers } = createScene();
    vi.stubGlobal("renderMathInElement", renderMath);
    const mathNode = node(1);
    mathNode.renderText = "Formula \\(x^2\\)";
    scene.rebuild([mathNode], [], DEFAULT_NODE_COLORS, handlers);
    scene.layout(16);
    expect(textContainer.querySelector(".katex")).not.toBeNull();

    stage.scale.set(0.1);
    scene.layout(16);
    expect(textContainer.children).toHaveLength(0);
    stage.scale.set(1);
    scene.layout(16);
    expect(textContainer.querySelector(".katex")).not.toBeNull();
    expect(textContainer.textContent).toContain("Formula");
    scene.destroy();
  });
});
