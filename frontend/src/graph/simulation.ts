import type { Simulation, SimulationLinkDatum } from "d3-force";

import type { GraphConnection, GraphNode } from "./types";

export type GraphSimulationLink = GraphConnection & SimulationLinkDatum<GraphNode>;

export function releaseReplacedForces(simulation: Simulation<GraphNode, GraphSimulationLink>): void {
  // Updating nodes reinitializes every attached force, including those about to be replaced.
  simulation.force("link", null).force("charge", null).force("collide", null);
}
