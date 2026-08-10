import type { Application, Container, FederatedPointerEvent, Graphics } from "pixi.js";

import { nodeRadius } from "./degree-sizing";
import { createNodeText, renderGraphMath, type GraphTextElement } from "./labels";
import { NodeGraphicsFactory, type NodeColors } from "./node-graphics";
import type { GraphConnection, GraphNode, ResolvedGraphConnection } from "./types";
import type { PointTransform, ViewportBoundary } from "./viewport";

const FONT_SIZE = 12;
const LINE_CLAMP = 4;
const PARTICLE_COUNT = 3;

export interface NodeInteractionHandlers {
  pointerDown(node: GraphNode, circle: Graphics, event: FederatedPointerEvent): void;
  pointerEnter(node: GraphNode): void;
  pointerLeave(): void;
}

export function isResolvedLink(link: GraphConnection): link is ResolvedGraphConnection {
  return typeof link.source === "object" && typeof link.target === "object";
}

function coordinate(value: number | undefined): number {
  return value ?? 0;
}

export class GraphScene {
  private circles: Graphics[] = [];
  private lineContainers: Container[] = [];
  private links: GraphConnection[] = [];
  private nodes: GraphNode[] = [];
  private particleStep = 0;
  private texts: GraphTextElement[] = [];

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
    this.nodes = nodes;
    this.links = links;
    this.app.stage.removeChildren().forEach((child) => child.destroy({ children: true }));
    this.textContainer.replaceChildren();

    const lineContext = new PIXI.GraphicsContext().rect(0, -0.5, 1, 1).fill(0x40404d);
    const particleContext = new PIXI.GraphicsContext().circle(0, 0, 1).fill("rgb(102, 102, 112)");
    this.lineContainers = links.map(() => {
      const container = new PIXI.Container();
      container.interactiveChildren = false;
      const line = new PIXI.Graphics(lineContext);
      line.eventMode = "none";
      container.addChild(line);
      for (let index = 0; index < PARTICLE_COUNT; index += 1) {
        const particle = new PIXI.Graphics(particleContext);
        particle.eventMode = "none";
        container.addChild(particle);
      }
      return container;
    });

    const graphicsFactory = new NodeGraphicsFactory(colors);
    this.circles = nodes.map((node) => this.createNodeGraphics(node, graphicsFactory, handlers));
    this.texts = nodes.map((node) => createNodeText(node));
    if (this.lineContainers.length > 0) {
      this.app.stage.addChild(...this.lineContainers);
    }
    if (this.circles.length > 0) {
      this.app.stage.addChild(...this.circles);
    }
  }

  layout(deltaMilliseconds: number): void {
    this.layoutNodes();
    this.layoutLinks(deltaMilliseconds);
  }

  private createNodeGraphics(
    node: GraphNode,
    factory: NodeGraphicsFactory,
    handlers: NodeInteractionHandlers,
  ): Graphics {
    const circle = new PIXI.Graphics(factory.context(node));
    circle.on("pointerdown", (event: FederatedPointerEvent) => handlers.pointerDown(node, circle, event));
    circle.on("pointerenter", () => handlers.pointerEnter(node));
    circle.on("pointerleave", () => handlers.pointerLeave());
    circle.eventMode = "static";
    return circle;
  }

  private layoutNodes(): void {
    let addedText = false;
    for (const [index, circle] of this.circles.entries()) {
      const node = this.nodes[index];
      const text = this.texts[index];
      if (node === undefined || text === undefined) {
        continue;
      }
      const x = coordinate(node.x);
      const y = coordinate(node.y);
      circle.position.set(x, y);
      circle.renderable = this.boundary.contains(x, y, nodeRadius(node));

      if (this.app.stage.scale.x < 0.5) {
        this.detachText(text);
        continue;
      }
      const textWidth = Math.max(100, nodeRadius(node) * 5);
      text.layoutWidth = this.transform.toClientLength(textWidth);
      text.fontSize = this.transform.toClientLength(FONT_SIZE);
      text.lineHeight = text.fontSize * 1.1;
      text.layoutLeft = this.transform.toClientX(x - textWidth / 2);
      text.layoutTop = this.transform.toClientY(y + nodeRadius(node) + 2);
      const visible = text.layoutLeft + text.layoutWidth > 0
        && text.layoutTop + text.lineHeight * LINE_CLAMP > 0
        && text.layoutLeft < window.innerWidth
        && text.layoutTop < window.innerHeight;
      if (!visible) {
        this.detachText(text);
        continue;
      }
      text.style.cssText = [
        `left:${String(text.layoutLeft)}px`,
        `top:${String(text.layoutTop)}px`,
        `width:${String(text.layoutWidth)}px`,
        `font-size:${String(text.fontSize)}px`,
        `line-height:${String(text.lineHeight)}px`,
      ].join(";");
      if (!text.inDocument) {
        this.textContainer.appendChild(text);
        text.inDocument = true;
        if (!text.addedBefore) {
          text.addedBefore = true;
          addedText = true;
        }
      }
    }
    if (addedText) {
      renderGraphMath();
    }
  }

  private detachText(text: GraphTextElement): void {
    if (text.inDocument) {
      text.remove();
      text.inDocument = false;
    }
  }

  private layoutLinks(deltaMilliseconds: number): void {
    for (const [index, container] of this.lineContainers.entries()) {
      const link = this.links[index];
      if (link === undefined || !isResolvedLink(link)) {
        container.renderable = false;
        continue;
      }
      const sourceX = coordinate(link.source.x);
      const sourceY = coordinate(link.source.y);
      const targetX = coordinate(link.target.x);
      const targetY = coordinate(link.target.y);
      const radius = Math.max(nodeRadius(link.source), nodeRadius(link.target), 20);
      if (!this.boundary.contains(sourceX, sourceY, radius) && !this.boundary.contains(targetX, targetY, radius)) {
        container.renderable = false;
        container.children.forEach((child) => { child.renderable = false; });
        continue;
      }

      const distance = Math.hypot(targetX - sourceX, targetY - sourceY);
      const screenWidth = this.app.stage.scale.x >= 0.08 ? 3 : Math.max(1, 37.5 * this.app.stage.scale.x);
      container.position.set(sourceX, sourceY);
      container.scale.set(distance, this.transform.toCanvasLength(screenWidth));
      container.rotation = Math.atan2(targetY - sourceY, targetX - sourceX);
      container.renderable = true;
      container.children.forEach((particle, particleIndex) => {
        if (particleIndex === 0) {
          particle.renderable = true;
        } else if (this.app.stage.scale.x < 0.2 || distance === 0) {
          particle.renderable = false;
        } else {
          particle.scale.set(screenWidth / distance, screenWidth / container.scale.y);
          particle.x = (particleIndex / PARTICLE_COUNT + this.particleStep) % 1;
          particle.renderable = true;
        }
      });
    }
    this.particleStep = (this.particleStep + deltaMilliseconds / 1600) % 1;
  }
}
