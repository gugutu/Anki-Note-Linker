import type { GraphConnection, GraphNode, NodeDegreeSizingMode, NodeId, ResolvedGraphConnection } from "./types";

const DEFAULT_RADIUS = 20;
const CURRENT_NODE_RADIUS = 25;
const MAX_SIZED_DEGREE = 10;
const RADIUS_PER_DEGREE = 6;

export function normalizeDegreeSizingMode(value: unknown): NodeDegreeSizingMode {
  return value === "all" || value === "out" ? value : "none";
}

export function endpointId(endpoint: GraphNode | NodeId): NodeId {
  return typeof endpoint === "object" ? endpoint.id : endpoint;
}

export function baseNodeRadius(type: string | undefined): number {
  return type === "me" ? CURRENT_NODE_RADIUS : DEFAULT_RADIUS;
}

export function nodeRadius(node: GraphNode): number {
  return node.renderRadius ?? baseNodeRadius(node.type);
}

function updateIndexedDegreeSizing(
  nodes: GraphNode[],
  links: GraphConnection[],
  mode: NodeDegreeSizingMode,
  nodeIndex: ReadonlyMap<NodeId, GraphNode>,
): void {
  for (const node of nodes) {
    node.outDegree = 0;
    node.inDegree = 0;
  }
  for (const link of links) {
    const source = nodeIndex.get(endpointId(link.source));
    const target = nodeIndex.get(endpointId(link.target));
    if (source !== undefined) source.outDegree = (source.outDegree ?? 0) + 1;
    if (target !== undefined) target.inDegree = (target.inDegree ?? 0) + 1;
  }
  for (const node of nodes) {
    // Copy canonical counts so repeated IDs retain the original counting behavior.
    const indexed = nodeIndex.get(node.id);
    node.outDegree = indexed?.outDegree ?? 0;
    node.inDegree = indexed?.inDegree ?? 0;
    node.degree = mode === "all" ? node.outDegree + node.inDegree : node.outDegree;
    const baseRadius = baseNodeRadius(node.type);
    node.renderRadius = mode === "none"
      ? baseRadius
      : baseRadius + Math.min(node.degree, MAX_SIZED_DEGREE) * RADIUS_PER_DEGREE;
  }
}

export function updateNodeDegreeSizing(
  nodes: GraphNode[],
  links: GraphConnection[],
  mode: NodeDegreeSizingMode,
  nodeIndex?: ReadonlyMap<NodeId, GraphNode>,
): void {
  if (nodeIndex !== undefined) {
    updateIndexedDegreeSizing(nodes, links, mode, nodeIndex);
    return;
  }
  const outgoing = new Map<NodeId, number>();
  const incoming = new Map<NodeId, number>();
  for (const link of links) {
    const sourceId = endpointId(link.source);
    const targetId = endpointId(link.target);
    outgoing.set(sourceId, (outgoing.get(sourceId) ?? 0) + 1);
    incoming.set(targetId, (incoming.get(targetId) ?? 0) + 1);
  }

  for (const node of nodes) {
    node.outDegree = outgoing.get(node.id) ?? 0;
    node.inDegree = incoming.get(node.id) ?? 0;
    node.degree = mode === "all" ? node.outDegree + node.inDegree : node.outDegree;
    const baseRadius = baseNodeRadius(node.type);
    node.renderRadius = mode === "none"
      ? baseRadius
      : baseRadius + Math.min(node.degree, MAX_SIZED_DEGREE) * RADIUS_PER_DEGREE;
  }
}

export function nodeCollisionRadius(node: GraphNode): number {
  return nodeRadius(node) + 18;
}

export function nodeChargeStrength(node: GraphNode, mode: NodeDegreeSizingMode): number {
  if (mode === "none") {
    return -700;
  }
  const degree = Math.min(node.degree ?? 0, 26);
  const extraRadius = Math.max(0, nodeRadius(node) - baseNodeRadius(node.type));
  return -700 - degree * 72 - extraRadius * 24;
}

export function linkDistance(link: ResolvedGraphConnection, mode: NodeDegreeSizingMode): number {
  if (mode === "none") {
    return 100;
  }
  const radiusBonus = Math.max(0, nodeRadius(link.source) + nodeRadius(link.target) - DEFAULT_RADIUS * 2);
  const averageDegree = ((link.source.degree ?? 0) + (link.target.degree ?? 0)) / 2;
  const degreeBonus = Math.min(24, Math.sqrt(averageDegree) * 8);
  return 100 + Math.min(52, radiusBonus * 0.85 + degreeBonus);
}
