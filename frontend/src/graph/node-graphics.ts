import type { GraphicsContext } from "pixi.js";

import { nodeRadius } from "./degree-sizing";
import type { GraphNode } from "./types";

export interface NodeColors {
  highlight: string;
  normal: string;
  tag: string;
}

export const DEFAULT_NODE_COLORS: NodeColors = {
  highlight: "rgb(244, 165, 0)",
  normal: "rgb(57, 125, 237)",
  tag: "rgb(127, 199, 132)",
};

export class NodeGraphicsFactory {
  private readonly cache = new Map<string, GraphicsContext>();

  constructor(private readonly colors: NodeColors) {}

  context(node: GraphNode): GraphicsContext {
    const radius = Math.max(4, Math.round(nodeRadius(node)));
    const cacheKey = `${node.type}:${String(radius)}`;
    const cached = this.cache.get(cacheKey);
    if (cached !== undefined) {
      return cached;
    }

    const context = new PIXI.GraphicsContext();
    switch (node.type) {
      case "highlight":
        context.circle(0, 0, radius).fill(this.colors.highlight);
        break;
      case "me":
        context
          .circle(0, 0, radius).fill("rgb(31, 115, 205)")
          .circle(0, 0, Math.max(6, radius * 0.6)).fill("rgb(28, 143, 251)");
        break;
      case "parent child":
        context
          .circle(0, 0, radius).fill("rgb(236, 61, 57)")
          .circle(0, 0, Math.max(6, radius * 0.7)).fill("rgb(226, 153, 2)");
        break;
      case "parent":
        context.circle(0, 0, radius).fill("rgb(236, 61, 57)");
        break;
      case "child":
        context.circle(0, 0, radius).fill("rgb(226, 153, 2)");
        break;
      case "tag":
        context.circle(0, 0, radius).fill(this.colors.tag);
        break;
      case "invalid":
        context.circle(0, 0, radius).fill("rgb(195, 195, 199)");
        break;
      default:
        context.circle(0, 0, radius).fill(this.colors.normal);
        break;
    }
    this.cache.set(cacheKey, context);
    return context;
  }
}
