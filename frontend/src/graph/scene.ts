import type { Application, Container, FederatedPointerEvent, Graphics, GraphicsContext } from "pixi.js";

import { nodeRadius } from "./degree-sizing";
import { createNodeText, renderGraphMath, type GraphTextElement } from "./labels";
import { NodeGraphicsFactory, type NodeColors } from "./node-graphics";
import { ParticlePool } from "./particle-pool";
import type { GraphConnection, GraphNode, ResolvedGraphConnection } from "./types";
import type { PointTransform, ViewportBoundary } from "./viewport";

const FONT_SIZE = 12;
const LINE_CLAMP = 4;
const PARTICLE_COUNT = 3;
const PARTICLE_RETENTION_MS = 1000;
const MAX_RECLAIMED_LINKS_PER_FRAME = 16;
const RECLAIM_BUDGET_MS = 1;

export interface NodeInteractionHandlers {
  pointerDown(node: GraphNode, circle: Graphics, event: FederatedPointerEvent): void;
  pointerEnter(node: GraphNode): void;
  pointerLeave(): void;
}

interface NodeGraphics extends Graphics {
  graphNode: GraphNode | null;
  graphHandlers: NodeInteractionHandlers | null;
}

function onNodePointerDown(this: NodeGraphics, event: FederatedPointerEvent): void {
  if (this.graphNode !== null) {
    this.graphHandlers?.pointerDown(this.graphNode, this, event);
  }
}

function onNodePointerEnter(this: NodeGraphics): void {
  if (this.graphNode !== null) {
    this.graphHandlers?.pointerEnter(this.graphNode);
  }
}

function onNodePointerLeave(this: NodeGraphics): void {
  this.graphHandlers?.pointerLeave();
}

export function isResolvedLink(link: GraphConnection): link is ResolvedGraphConnection {
  return typeof link.source === "object" && typeof link.target === "object";
}

function coordinate(value: number | undefined): number {
  return value ?? 0;
}

export class GraphScene {
  private circles: NodeGraphics[] = [];
  private graphicsFactory: NodeGraphicsFactory | null = null;
  private lineContext: GraphicsContext | null = null;
  private lineContainers: Container[] = [];
  private particlesHiddenAt = new Float64Array();
  private links: GraphConnection[] = [];
  private nodes: GraphNode[] = [];
  private particleStep = 0;
  private particlePool: ParticlePool | null = null;
  private elapsedMilliseconds = 0;
  private reclaimedLinks = 0;
  private reclaimMilliseconds = 0;
  private readonly texts = new Map<number, GraphTextElement>();

  constructor(
    private readonly app: Application,
    private readonly textContainer: HTMLElement,
    private readonly boundary: ViewportBoundary,
    private readonly transform: PointTransform,
  ) {}

  rebuild(
    nodes: GraphNode[],
    links: GraphConnection[],
    colors: NodeColors,
    handlers: NodeInteractionHandlers,
  ): void {
    this.destroy();
    this.nodes = nodes;
    this.links = links;
    this.particlesHiddenAt = new Float64Array(links.length).fill(-1);

    if (links.length > 0) {
      const lineContext = this.lineContext = new PIXI.GraphicsContext().rect(0, -0.5, 1, 1).fill(0x40404d);
      this.particlePool = new ParticlePool();
      this.lineContainers = links.map(() => {
        const container = new PIXI.Container();
        container.interactiveChildren = false;
        const line = new PIXI.Graphics(lineContext);
        line.eventMode = "none";
        container.addChild(line);
        return container;
      });
    }

    const graphicsFactory = this.graphicsFactory = new NodeGraphicsFactory(colors);
    this.circles = nodes.map((node) => this.createNodeGraphics(node, graphicsFactory, handlers));
    for (const container of this.lineContainers) {
      this.app.stage.addChild(container);
    }
    for (const circle of this.circles) {
      this.app.stage.addChild(circle);
    }
  }

  layout(deltaMilliseconds: number): void {
    this.elapsedMilliseconds += Math.max(0, deltaMilliseconds);
    this.reclaimedLinks = 0;
    this.reclaimMilliseconds = 0;
    this.layoutNodes();
    this.layoutLinks(deltaMilliseconds);
  }

  destroy(): void {
    this.clearDisplayObjects();
    this.nodes = [];
    this.links = [];
  }

  private clearDisplayObjects(): void {
    for (const circle of this.circles) {
      circle.graphNode = null;
      circle.graphHandlers = null;
    }
    this.app.stage.removeChildren().forEach((child) => child.destroy({ children: true }));
    this.circles = [];
    this.lineContainers = [];
    this.particlesHiddenAt = new Float64Array();
    // Shared contexts outlive individual Graphics objects; release them once per scene.
    this.graphicsFactory?.destroy();
    this.graphicsFactory = null;
    this.lineContext?.destroy();
    this.lineContext = null;
    this.particlePool?.destroy();
    this.particlePool = null;
    this.elapsedMilliseconds = 0;
    this.textContainer.replaceChildren();
    this.texts.clear();
  }

  private createNodeGraphics(
    node: GraphNode,
    factory: NodeGraphicsFactory,
    handlers: NodeInteractionHandlers,
  ): NodeGraphics {
    const circle = new PIXI.Graphics(factory.context(node)) as NodeGraphics;
    circle.graphNode = node;
    circle.graphHandlers = handlers;
    // Pixi supplies the listener context, so every node can share these functions.
    circle.on("pointerdown", onNodePointerDown, circle);
    circle.on("pointerenter", onNodePointerEnter, circle);
    circle.on("pointerleave", onNodePointerLeave, circle);
    circle.eventMode = "static";
    return circle;
  }

  private layoutNodes(): void {
    for (let index = 0; index < this.circles.length; index += 1) {
      const circle = this.circles[index];
      const node = this.nodes[index];
      if (node === undefined || circle === undefined) {
        continue;
      }
      const x = coordinate(node.x);
      const y = coordinate(node.y);
      circle.position.set(x, y);
      circle.renderable = this.boundary.contains(x, y, nodeRadius(node));

      if (this.app.stage.scale.x < 0.5) {
        this.detachText(index);
        continue;
      }
      const textWidth = Math.max(100, nodeRadius(node) * 5);
      const layoutWidth = this.transform.toClientLength(textWidth);
      const fontSize = this.transform.toClientLength(FONT_SIZE);
      const lineHeight = fontSize * 1.1;
      const layoutLeft = this.transform.toClientX(x - textWidth / 2);
      const layoutTop = this.transform.toClientY(y + nodeRadius(node) + 2);
      const visible = layoutLeft + layoutWidth > 0
        && layoutTop + lineHeight * LINE_CLAMP > 0
        && layoutLeft < window.innerWidth
        && layoutTop < window.innerHeight;
      if (!visible) {
        this.detachText(index);
        continue;
      }
      let text = this.texts.get(index);
      if (text === undefined) {
        text = createNodeText(node);
        this.texts.set(index, text);
      }
      if (
        text.layoutWidth !== layoutWidth
        || text.fontSize !== fontSize
        || text.lineHeight !== lineHeight
        || text.layoutLeft !== layoutLeft
        || text.layoutTop !== layoutTop
      ) {
        text.layoutWidth = layoutWidth;
        text.fontSize = fontSize;
        text.lineHeight = lineHeight;
        text.layoutLeft = layoutLeft;
        text.layoutTop = layoutTop;
        text.style.cssText = `left:${String(layoutLeft)}px;top:${String(layoutTop)}px;`
          + `width:${String(layoutWidth)}px;font-size:${String(fontSize)}px;`
          + `line-height:${String(lineHeight)}px`;
      }
      if (!text.inDocument) {
        this.textContainer.appendChild(text);
        text.inDocument = true;
        if (!text.addedBefore) {
          text.addedBefore = true;
          renderGraphMath(text);
        }
      }
    }
  }

  private detachText(index: number): void {
    this.texts.get(index)?.remove();
    this.texts.delete(index);
  }

  private hideParticles(container: Container, index: number): void {
    if (container.children.length <= 1) return;
    for (let index = 1; index < container.children.length; index += 1) {
      const particle = container.children[index];
      if (particle !== undefined) particle.renderable = false;
    }
    let hiddenAt = this.particlesHiddenAt[index] ?? -1;
    if (hiddenAt < 0) {
      hiddenAt = this.particlesHiddenAt[index] = this.elapsedMilliseconds;
    }
    if (
      this.elapsedMilliseconds - hiddenAt < PARTICLE_RETENTION_MS
      || this.reclaimedLinks >= MAX_RECLAIMED_LINKS_PER_FRAME
      || this.reclaimMilliseconds >= RECLAIM_BUDGET_MS
    ) return;
    const started = performance.now();
    for (const particle of container.removeChildren(1)) {
      this.particlePool?.release(particle as Graphics);
    }
    this.particlesHiddenAt[index] = -1;
    this.reclaimedLinks += 1;
    this.reclaimMilliseconds += performance.now() - started;
  }

  private layoutParticles(container: Container, distance: number, screenWidth: number, index: number): void {
    if (this.app.stage.scale.x < 0.2 || distance === 0) {
      this.hideParticles(container, index);
      return;
    }
    this.particlesHiddenAt[index] = -1;
    if (container.children.length === 1 && this.particlePool !== null) {
      for (let index = 0; index < PARTICLE_COUNT; index += 1) {
        const particle = this.particlePool.acquire();
        container.addChild(particle);
      }
    }
    for (let index = 1; index < container.children.length; index += 1) {
      const particle = container.children[index];
      if (particle === undefined) {
        continue;
      }
      particle.scale.set(screenWidth / distance, screenWidth / container.scale.y);
      particle.x = (index / PARTICLE_COUNT + this.particleStep) % 1;
      particle.renderable = true;
    }
  }

  private layoutLinks(deltaMilliseconds: number): void {
    for (let index = 0; index < this.lineContainers.length; index += 1) {
      const container = this.lineContainers[index];
      if (container === undefined) {
        continue;
      }
      const link = this.links[index];
      if (link === undefined || !isResolvedLink(link)) {
        container.renderable = false;
        this.hideParticles(container, index);
        continue;
      }
      const sourceX = coordinate(link.source.x);
      const sourceY = coordinate(link.source.y);
      const targetX = coordinate(link.target.x);
      const targetY = coordinate(link.target.y);
      const radius = Math.max(nodeRadius(link.source), nodeRadius(link.target), 20);
      if (!this.boundary.contains(sourceX, sourceY, radius) && !this.boundary.contains(targetX, targetY, radius)) {
        container.renderable = false;
        for (const child of container.children) {
          child.renderable = false;
        }
        this.hideParticles(container, index);
        continue;
      }

      const distance = Math.hypot(targetX - sourceX, targetY - sourceY);
      const screenWidth = this.app.stage.scale.x >= 0.08 ? 3 : Math.max(1, 37.5 * this.app.stage.scale.x);
      container.position.set(sourceX, sourceY);
      container.scale.set(distance, this.transform.toCanvasLength(screenWidth));
      container.rotation = Math.atan2(targetY - sourceY, targetX - sourceX);
      container.renderable = true;
      const line = container.children[0];
      if (line !== undefined) {
        line.renderable = true;
      }
      this.layoutParticles(container, distance, screenWidth, index);
    }
    this.particleStep = (this.particleStep + deltaMilliseconds / 1600) % 1;
  }
}
