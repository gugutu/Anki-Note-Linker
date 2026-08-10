import { describe, expect, it } from "vitest";

import {
  linkDistance,
  nodeChargeStrength,
  normalizeDegreeSizingMode,
  updateNodeDegreeSizing,
} from "../../src/graph/degree-sizing";
import type { GraphConnection, GraphNode, ResolvedGraphConnection } from "../../src/graph/types";

describe("graph degree sizing", () => {
  it("counts outgoing and total links independently", () => {
    const nodes: GraphNode[] = [
      { id: 1, mainField: "one", type: "normal" },
      { id: 2, mainField: "two", type: "normal" },
      { id: 3, mainField: "three", type: "normal" },
    ];
    const links: GraphConnection[] = [
      { source: 1, target: 2 },
      { source: 3, target: 2 },
    ];

    updateNodeDegreeSizing(nodes, links, "all");

    expect(nodes.map((node) => node.degree)).toEqual([1, 2, 1]);
    expect(nodes[1]?.renderRadius).toBe(32);
  });

  it("uses conservative defaults for unknown modes and disabled sizing", () => {
    const source: GraphNode = { id: 1, mainField: "one", type: "normal" };
    const target: GraphNode = { id: 2, mainField: "two", type: "normal" };
    const link: ResolvedGraphConnection = { source, target };

    expect(normalizeDegreeSizingMode("unexpected")).toBe("none");
    expect(linkDistance(link, "none")).toBe(100);
    expect(nodeChargeStrength(source, "none")).toBe(-700);
  });
});
