import { describe, expect, it } from "vitest";

import {
  linkDistance,
  nodeChargeStrength,
  normalizeDegreeSizingMode,
  updateNodeDegreeSizing,
} from "../../src/graph/degree-sizing";
import type { GraphConnection, GraphNode, NodeDegreeSizingMode, ResolvedGraphConnection } from "../../src/graph/types";

describe("graph degree sizing", () => {
  it.each<NodeDegreeSizingMode>(["none", "out", "all"])("indexed counts match the original for %s sizing", (mode) => {
    const inputs: GraphNode[] = [
      { id: 1, mainField: "First", type: "normal", outDegree: 999, inDegree: 999 },
      { id: 1, mainField: "Duplicate ID", type: "me" },
      { id: "1", mainField: "String ID", type: "tag" },
      { id: 2, mainField: "Second", type: "child" },
      { id: 3, mainField: "Single", type: "normal" },
    ];
    const links: GraphConnection[] = [
      { source: 1, target: 2 }, { source: 1, target: 2 }, { source: 1, target: 1 },
      { source: "1", target: 1 }, { source: 2, target: "missing" },
      { source: { id: 1, mainField: null, type: "invalid" }, target: "1" },
    ];
    const original = inputs.map((node) => ({ ...node }));
    const indexed = inputs.map((node) => ({ ...node }));
    const index = new Map(indexed.map((node) => [node.id, node]));
    for (let iteration = 0; iteration < 5; iteration += 1) {
      updateNodeDegreeSizing(original, links, mode);
      updateNodeDegreeSizing(indexed, links, mode, index);
      expect(indexed).toEqual(original);
    }
    updateNodeDegreeSizing(original, [], mode);
    updateNodeDegreeSizing(indexed, [], mode, index);
    expect(indexed).toEqual(original);
    expect(indexed.every((node) => node.inDegree === 0 && node.outDegree === 0)).toBe(true);
  });

  it("matches original counts on a dense graph without replacing the borrowed index", () => {
    const nodes = Array.from({ length: 1000 }, (_, id) => ({ id, mainField: "Note", type: "normal" }));
    const links = Array.from({ length: 10000 }, (_, i) => ({ source: i % nodes.length, target: (i * 17 + 1) % nodes.length }));
    const original = nodes.map((node) => ({ ...node }));
    const indexed = nodes.map((node) => ({ ...node }));
    const index = new Map(indexed.map((node) => [node.id, node]));
    updateNodeDegreeSizing(original, links, "all");
    updateNodeDegreeSizing(indexed, links, "all", index);
    expect(indexed).toEqual(original);
    expect(index.size).toBe(nodes.length);
    for (const node of indexed) expect(index.get(node.id)).toBe(node);
  });

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
