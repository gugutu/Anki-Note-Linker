import type {
  FederatedPointerEvent,
  FederatedWheelEvent,
  Graphics,
  Ticker,
} from "pixi.js";
import type { Simulation, SimulationLinkDatum } from "d3-force";

import { CenterAnimation, ZoomAnimation } from "./animations";
import { applyGraphBackground, DEFAULT_BACKGROUND, normalizeRgbColor } from "./appearance";
import {
  linkDistance,
  nodeChargeStrength,
  nodeCollisionRadius,
  nodeRadius,
  normalizeDegreeSizingMode,
  updateNodeDegreeSizing,
} from "./degree-sizing";
import { createNodeLabel, positionLabel, renderGraphMath } from "./labels";
import { prepareNodeContent } from "./node-content";
import { DEFAULT_NODE_COLORS, type NodeColors } from "./node-graphics";
import { GraphScene, isResolvedLink, type NodeInteractionHandlers } from "./scene";
import type {
  GraphConnection,
  GraphNode,
  NodeDegreeSizingMode,
  NodeId,
} from "./types";
import { normalizeZoomConfig } from "./zoom";
import { createPointTransform, ViewportBoundary } from "./viewport";

type D3Link = GraphConnection & SimulationLinkDatum<GraphNode>;

const NODE_DRAG_THRESHOLD = 4;

interface NodePointerGesture {
  button: 0 | 2;
  dragGapX: number;
  dragGapY: number;
  dragging: boolean;
  node: GraphNode;
  pointerId: number;
  startX: number;
  startY: number;
}

export interface NewGraphBrowserApi {
  focusNode(nodeId: NodeId): void;
  reloadPage(
    nodes: GraphNode[],
    connections: GraphConnection[],
    resetCenter: boolean,
    adaptScale?: boolean,
    normalColor?: string | null,
    highlightColor?: string | null,
    tagColor?: string | null,
    backgroundColor?: number[] | null,
    degreeSizing?: string,
  ): Promise<void>;
}

function coordinate(value: number | undefined): number {
  return value ?? 0;
}

class PixiGraphRenderer implements NewGraphBrowserApi {
  private readonly app = new PIXI.Application();
  private readonly centerAnimation = new CenterAnimation((x, y) => {
    this.app.stage.x = x;
    this.app.stage.y = y;
    this.boundary.update();
  });
  private readonly initialization: Promise<boolean>;
  private readonly scene: GraphScene;
  private readonly simulation: Simulation<GraphNode, D3Link>;
  private readonly transform = createPointTransform(this.app.stage);
  private readonly boundary = new ViewportBoundary(this.app.stage, this.transform);
  private readonly zoomConfig = normalizeZoomConfig(graphZoomConfig);
  private readonly zoomAnimation = new ZoomAnimation(
    {
      apply: (scale, eventX, eventY) => this.applyZoomAt(scale, eventX, eventY),
      currentScale: () => this.app.stage.scale.x,
      draggingCanvas: () => this.draggingCanvas || this.nodeGesture?.dragging === true,
    },
    this.zoomConfig,
    enableSmoothGraphZoom,
  );

  private degreeSizing: NodeDegreeSizingMode = "none";
  private draggingCanvas = false;
  private fallbackRequested = false;
  private label: HTMLDivElement | null = null;
  private lastWindowHeight: number | null = null;
  private lastWindowWidth: number | null = null;
  private links: GraphConnection[] = [];
  private needAdaptScale = true;
  private nodeColors: NodeColors = { ...DEFAULT_NODE_COLORS };
  private nodeGesture: NodePointerGesture | null = null;
  private nodes: GraphNode[] = [];
  private stageDragGapX = 0;
  private stageDragGapY = 0;

  constructor() {
    const textContainer = document.querySelector<HTMLElement>("#texts");
    if (textContainer === null) {
      throw new Error("The graph text container is missing.");
    }
    this.scene = new GraphScene(this.app, textContainer, this.boundary, this.transform);
    this.simulation = d3.forceSimulation<GraphNode>(this.nodes)
      .force("x", d3.forceX<GraphNode>(0).strength(0.06))
      .force("y", d3.forceY<GraphNode>(0).strength(0.06))
      .force("center", null)
      .velocityDecay(0.3);
    this.applySimulationForces();
    this.initialization = this.app.init({
      antialias: true,
      autoDensity: true,
      background: "rgb(16, 16, 32)",
      height: window.innerHeight,
      preference: "webgl",
      resolution: 1.5,
      width: window.innerWidth,
    }).then(() => {
      this.initializePixi();
      return true;
    }).catch((error: unknown) => {
      this.requestLegacyRenderer(error);
      return false;
    });
  }

  async reloadPage(
    newNodes: GraphNode[],
    connections: GraphConnection[],
    resetCenter: boolean,
    adaptScale = false,
    normalColor: string | null = null,
    highlightColor: string | null = null,
    tagColor: string | null = null,
    backgroundColor: number[] | null = DEFAULT_BACKGROUND,
    degreeSizing = "none",
  ): Promise<void> {
    if (!await this.initialization) {
      return;
    }
    while (window.innerHeight === 0 || window.innerWidth === 0) {
      await new Promise<void>((resolve) => window.setTimeout(resolve, 20));
    }

    applyGraphBackground(this.app, normalizeRgbColor(backgroundColor));
    this.nodeColors = {
      highlight: highlightColor ?? DEFAULT_NODE_COLORS.highlight,
      normal: normalColor ?? DEFAULT_NODE_COLORS.normal,
      tag: tagColor ?? DEFAULT_NODE_COLORS.tag,
    };
    this.degreeSizing = normalizeDegreeSizingMode(degreeSizing);

    const previousNodes = new Map(this.nodes.map((node) => [node.id, node]));
    for (const node of newNodes) {
      const previous = previousNodes.get(node.id);
      if (previous !== undefined) {
        for (const key of ["x", "y", "vx", "vy", "fx", "fy", "index"] as const) {
          const value = previous[key];
          if (value !== undefined) {
            Object.assign(node, { [key]: value });
          }
        }
      }
      prepareNodeContent(node, enableImagePreview, `${window.location.origin}/`, getTr("Invalid note"));
    }

    this.nodes = newNodes;
    this.links = connections;
    updateNodeDegreeSizing(this.nodes, this.links, this.degreeSizing);
    this.simulation.nodes(this.nodes);
    this.applySimulationForces();
    this.simulation.alpha(1).alphaTarget(0).restart();
    this.rebuildDisplayObjects();
    this.needAdaptScale = adaptScale;
    this.simulation.tick(5);
    if (resetCenter) {
      this.centerOn(0, 0);
    }
  }

  focusNode(nodeId: NodeId): void {
    let attempts = 0;
    const focusWhenReady = (): void => {
      const node = this.nodes.find((candidate) => candidate.id === nodeId);
      if (node?.x !== undefined && node.y !== undefined) {
        this.centerOn(node.x, node.y);
        return;
      }
      attempts += 1;
      if (attempts < 20) {
        window.setTimeout(focusWhenReady, 100);
      }
    };
    focusWhenReady();
  }

  private requestLegacyRenderer(error: unknown): void {
    if (this.fallbackRequested) {
      return;
    }
    this.fallbackRequested = true;
    console.error("Failed to initialize the Pixi graph renderer; switching to the legacy renderer.", error);
    pycmd("AnkiNoteLinker-switchToOldRenderer");
  }

  private applySimulationForces(): void {
    const links = this.links as D3Link[];
    this.simulation
      .force(
        "link",
        d3.forceLink<GraphNode, D3Link>(links)
          .id((node) => node.id)
          .distance((link) => isResolvedLink(link) ? linkDistance(link, this.degreeSizing) : 100),
      )
      .force("charge", d3.forceManyBody<GraphNode>().strength((node) => nodeChargeStrength(node, this.degreeSizing)))
      .force(
        "collide",
        this.degreeSizing === "none"
          ? null
          : d3.forceCollide<GraphNode>()
            .radius((node) => nodeCollisionRadius(node))
            .iterations(2)
            .strength(0.9),
      );
  }

  private initializePixi(): void {
    document.body.appendChild(this.app.canvas);
    this.app.canvas.addEventListener("contextmenu", (event) => event.preventDefault());
    this.app.stage.x = window.innerWidth / 2;
    this.app.stage.y = window.innerHeight / 2;
    this.boundary.update();
    this.app.stage.eventMode = "static";
    this.rebuildDisplayObjects();

    window.addEventListener("resize", () => this.resize());
    this.app.stage.on("pointerdown", (event: FederatedPointerEvent) => {
      if (event.target !== this.app.stage) {
        return;
      }
      this.stageDragGapX = this.app.stage.x - event.x;
      this.stageDragGapY = this.app.stage.y - event.y;
      this.draggingCanvas = true;
    });
    this.app.stage.on("pointerup", (event: FederatedPointerEvent) => this.finishPointerInteraction(event, true));
    this.app.stage.on("pointerupoutside", (event: FederatedPointerEvent) => {
      this.finishPointerInteraction(event, false);
    });
    this.app.stage.on("pointercancel", (event: FederatedPointerEvent) => {
      this.finishPointerInteraction(event, false);
    });
    this.app.stage.on("globalpointermove", (event: FederatedPointerEvent) => this.movePointer(event));
    this.app.stage.on("wheel", (event: FederatedWheelEvent) => this.zoomAnimation.start(event));
    this.app.ticker.add((ticker: Ticker) => this.tick(ticker));
  }

  private resize(): void {
    this.app.renderer.resize(window.innerWidth, window.innerHeight);
    if (
      this.lastWindowWidth !== null
      && this.lastWindowWidth !== 0
      && this.lastWindowHeight !== null
      && this.lastWindowHeight !== 0
    ) {
      this.app.stage.x *= window.innerWidth / this.lastWindowWidth;
      this.app.stage.y *= window.innerHeight / this.lastWindowHeight;
    }
    this.lastWindowWidth = window.innerWidth;
    this.lastWindowHeight = window.innerHeight;
    this.boundary.update();
  }

  private rebuildDisplayObjects(): void {
    document.body.style.cursor = "default";
    this.removeLabel();
    const handlers: NodeInteractionHandlers = {
      pointerDown: (node, circle, event) => this.startNodeGesture(node, circle, event),
      pointerEnter: (node) => this.showNodeLabel(node),
      pointerLeave: () => this.hideNodeLabel(),
    };
    this.scene.rebuild(this.nodes, this.links, this.nodeColors, handlers);
  }

  private startNodeGesture(node: GraphNode, circle: Graphics, event: FederatedPointerEvent): void {
    if ((event.button !== 0 && event.button !== 2) || this.nodeGesture !== null) {
      return;
    }
    this.draggingCanvas = false;
    node.fx = circle.x;
    node.fy = circle.y;
    this.nodeGesture = {
      button: event.button,
      dragGapX: circle.x - this.transform.toCanvasX(event.x),
      dragGapY: circle.y - this.transform.toCanvasY(event.y),
      dragging: false,
      node,
      pointerId: event.pointerId,
      startX: event.x,
      startY: event.y,
    };
  }

  private showNodeLabel(node: GraphNode): void {
    document.body.style.cursor = "pointer";
    this.removeLabel();
    this.label = createNodeLabel(node);
    document.body.appendChild(this.label);
    renderGraphMath();
  }

  private hideNodeLabel(): void {
    document.body.style.cursor = "default";
    this.removeLabel();
  }

  private openNodeContextAction(node: GraphNode): void {
    if (node.type === "tag") {
      pycmd(`AnkiNoteLinker-tagSearch${String(node.id)}`);
    } else {
      pycmd(`AnkiNoteLinker-openNoteInNewEditor${String(node.id)}`);
    }
  }

  private openNode(node: GraphNode): void {
    if (node.type === "tag") {
      pycmd(`AnkiNoteLinker-tagSearch${String(node.id)}`);
      return;
    }
    if (node.type === "me") {
      return;
    }
    const command = ankiContext === "BROWSER"
      ? "AnkiNoteLinker-openNoteInBrowser"
      : ankiContext === "EDIT_CURRENT"
        ? "AnkiNoteLinker-setNoteToEditor"
        : "AnkiNoteLinker-openNoteInPreviewer";
    pycmd(`${command}${String(node.id)}`);
  }

  private finishPointerInteraction(event: FederatedPointerEvent, activateNode: boolean): void {
    if (this.draggingCanvas) {
      this.draggingCanvas = false;
      this.boundary.update();
    }
    this.app.stage.interactiveChildren = true;
    const gesture = this.nodeGesture;
    if (gesture !== null && gesture.pointerId === event.pointerId) {
      this.nodeGesture = null;
      gesture.node.fx = null;
      gesture.node.fy = null;
      document.body.style.cursor = "default";
      this.simulation.alphaTarget(0).restart();
      if (activateNode && !gesture.dragging) {
        if (gesture.button === 2) {
          this.openNodeContextAction(gesture.node);
        } else {
          this.openNode(gesture.node);
        }
      }
    }
  }

  private movePointer(event: FederatedPointerEvent): void {
    const gesture = this.nodeGesture;
    if (gesture !== null && gesture.pointerId === event.pointerId) {
      if (!gesture.dragging) {
        const distance = Math.hypot(event.x - gesture.startX, event.y - gesture.startY);
        if (distance < NODE_DRAG_THRESHOLD) {
          if (this.label !== null) {
            positionLabel(this.label, event.x, event.y);
          }
          return;
        }
        gesture.dragging = true;
        document.body.style.cursor = "grabbing";
        this.removeLabel();
      }
      gesture.node.fx = this.transform.toCanvasX(event.x) + gesture.dragGapX;
      gesture.node.fy = this.transform.toCanvasY(event.y) + gesture.dragGapY;
      if (this.simulation.alphaTarget() < 0.5) {
        this.simulation.alphaTarget(0.5).restart();
      }
      this.draggingCanvas = false;
    } else if (this.draggingCanvas) {
      this.app.stage.interactiveChildren = false;
      this.app.stage.x = event.x + this.stageDragGapX;
      this.app.stage.y = event.y + this.stageDragGapY;
      this.boundary.update(false);
    }
    if (this.label !== null) {
      positionLabel(this.label, event.x, event.y);
    }
  }

  private applyZoomAt(scale: number, eventX: number, eventY: number): void {
    const beforeX = this.transform.toCanvasX(eventX);
    const beforeY = this.transform.toCanvasY(eventY);
    this.app.stage.scale.set(scale);
    const afterX = this.transform.toCanvasX(eventX);
    const afterY = this.transform.toCanvasY(eventY);
    this.app.stage.x += this.transform.toClientLength(afterX - beforeX);
    this.app.stage.y += this.transform.toClientLength(afterY - beforeY);
    this.boundary.update();
  }

  private centerOn(canvasX: number, canvasY: number): void {
    const scale = this.app.stage.scale.x;
    this.centerAnimation.start(
      this.app.stage.x,
      this.app.stage.y,
      window.innerWidth / 2 - canvasX * scale,
      window.innerHeight / 2 - canvasY * scale,
    );
  }

  private tick(ticker: Ticker): void {
    this.adaptScale();
    this.centerAnimation.tick(ticker.deltaMS);
    this.zoomAnimation.tick(ticker.deltaMS);
    this.scene.layout(ticker.deltaMS);
  }

  private adaptScale(): void {
    if (!this.needAdaptScale) {
      return;
    }
    let left = 0;
    let right = 0;
    let top = 0;
    let bottom = 0;
    for (const node of this.nodes) {
      const x = coordinate(node.x);
      const y = coordinate(node.y);
      const radius = nodeRadius(node);
      left = Math.min(left, x - radius);
      right = Math.max(right, x + radius);
      top = Math.min(top, y - radius);
      bottom = Math.max(bottom, y + radius);
    }
    const scale = Math.min(
      this.zoomConfig.autoFitMaxScale,
      0.8 * window.innerWidth / (right - left + 80),
      0.8 * window.innerHeight / (bottom - top + 80),
    );
    this.app.stage.scale.set(Math.max(this.zoomConfig.minScale, Math.min(this.zoomConfig.maxScale, scale)));
    this.app.stage.x = window.innerWidth / 2;
    this.app.stage.y = window.innerHeight / 2;
    this.needAdaptScale = false;
    this.boundary.update();
  }

  private removeLabel(): void {
    this.label?.remove();
    this.label = null;
  }
}

const renderer = new PixiGraphRenderer();
const api: NewGraphBrowserApi = {
  focusNode: (nodeId) => renderer.focusNode(nodeId),
  reloadPage: (...args) => renderer.reloadPage(...args),
};
window.AnkiNoteLinkerNewGraph = api;
Object.assign(window, { reloadPage: (...args: Parameters<NewGraphBrowserApi["reloadPage"]>) => api.reloadPage(...args) });
