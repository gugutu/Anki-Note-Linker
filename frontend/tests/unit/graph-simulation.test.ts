import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3";
import type { Simulation } from "d3-force";
import { describe, expect, it, vi } from "vitest";

import { preserveNodePosition } from "../../src/graph/content";
import {
  linkDistance, nodeChargeStrength, nodeCollisionRadius, updateNodeDegreeSizing,
} from "../../src/graph/degree-sizing";
import { isResolvedLink } from "../../src/graph/scene";
import { releaseReplacedForces, type GraphSimulationLink } from "../../src/graph/simulation";
import type { GraphConnection, GraphNode, NodeDegreeSizingMode } from "../../src/graph/types";

type GraphSimulation = Simulation<GraphNode, GraphSimulationLink>;

function installForces(simulation: GraphSimulation, links: GraphSimulationLink[], state: { mode: NodeDegreeSizingMode }) {
  simulation
    .force("link", forceLink<GraphNode, GraphSimulationLink>(links)
      .id((node) => node.id)
      .distance((link) => isResolvedLink(link) ? linkDistance(link, state.mode) : 100))
    .force("charge", forceManyBody<GraphNode>().strength((node) => nodeChargeStrength(node, state.mode)))
    .force("collide", state.mode === "none" ? null : forceCollide<GraphNode>()
      .radius(nodeCollisionRadius).iterations(2).strength(0.9));
}

function createSimulation() {
  const state: { mode: NodeDegreeSizingMode } = { mode: "none" };
  const simulation: GraphSimulation = forceSimulation<GraphNode>([]).stop()
    .force("x", forceX<GraphNode>(0).strength(0.06))
    .force("y", forceY<GraphNode>(0).strength(0.06))
    .force("center", null)
    .velocityDecay(0.3);
  installForces(simulation, [], state);
  return { simulation, state };
}

function reload(
  context: ReturnType<typeof createSimulation>,
  nodes: GraphNode[],
  links: GraphConnection[],
  mode: NodeDegreeSizingMode,
  optimized: boolean,
) {
  const previous = new Map(context.simulation.nodes().map((node) => [node.id, node]));
  for (const node of nodes) preserveNodePosition(node, previous.get(node.id));
  context.state.mode = mode;
  updateNodeDegreeSizing(nodes, links, mode);
  if (optimized) releaseReplacedForces(context.simulation);
  context.simulation.nodes(nodes);
  installForces(context.simulation, links, context.state);
  context.simulation.alpha(1).alphaTarget(0).tick(5);
}

describe("graph simulation refresh", () => {
  it("does not reinitialize discarded forces and retains the axis forces", () => {
    const { simulation, state } = createSimulation();
    state.mode = "all";
    installForces(simulation, [], state);
    const axisX = simulation.force("x");
    const axisY = simulation.force("y");
    const initialize = ["link", "charge", "collide"].map((name) => {
      const force = simulation.force(name);
      if (force?.initialize === undefined) throw new Error("Missing force initializer");
      return vi.spyOn(force, "initialize");
    });
    releaseReplacedForces(simulation);
    simulation.nodes([{ id: 1, mainField: "Note", type: "normal" }]);
    for (const spy of initialize) expect(spy).not.toHaveBeenCalled();
    expect(simulation.force("x")).toBe(axisX);
    expect(simulation.force("y")).toBe(axisY);
    for (const name of ["link", "charge", "collide"]) expect(simulation.force(name)).toBeUndefined();
    simulation.stop();
  });

  it("matches the previous layout exactly across rewiring, mode changes, empty graphs and repeated ticks", () => {
    const previous = createSimulation();
    const optimized = createSimulation();
    const snapshots: { ids: (number | string)[]; links: GraphConnection[]; mode: NodeDegreeSizingMode }[] = [
      { ids: [1, 2, 3], links: [{ source: 1, target: 2 }, { source: 2, target: 3 }], mode: "none" },
      { ids: [1, 2, 3, "tag"], links: [{ source: 1, target: 3 }, { source: "tag", target: 1 }], mode: "all" },
      { ids: [1, 3, "tag"], links: [{ source: 3, target: 1 }, { source: 1, target: 1 }], mode: "out" },
      { ids: [1, 3], links: [{ source: 1, target: 3 }], mode: "none" },
      { ids: [], links: [], mode: "all" },
      { ids: [4, 5], links: [{ source: 4, target: 5 }], mode: "all" },
    ];
    try {
      for (const snapshot of snapshots) {
        for (const [context, useOptimization] of [[previous, false], [optimized, true]] as const) {
          const nodes = snapshot.ids.map((id) => ({ id, mainField: "Note", type: "normal", x: 0, y: 0, vx: 0, vy: 0 }));
          reload(context, nodes, snapshot.links.map((link) => ({ ...link })), snapshot.mode, useOptimization);
        }
        expect(optimized.simulation.nodes()).toEqual(previous.simulation.nodes());
        previous.simulation.tick(20);
        optimized.simulation.tick(20);
        expect(optimized.simulation.nodes()).toEqual(previous.simulation.nodes());
      }
    } finally {
      previous.simulation.stop();
      optimized.simulation.stop();
    }
  });
});
