export type NodeId = number | string;

export interface GraphNode {
  degree?: number;
  fx?: number | null;
  fy?: number | null;
  id: NodeId;
  imageSrc?: string;
  inDegree?: number;
  index?: number;
  linkTitle?: string | null;
  mainField: string | null;
  outDegree?: number;
  renderRadius?: number;
  renderText?: string;
  type: string;
  vx?: number;
  vy?: number;
  x?: number;
  y?: number;
}

export interface GraphConnection {
  source: GraphNode | NodeId;
  target: GraphNode | NodeId;
}

export interface ResolvedGraphConnection {
  source: GraphNode;
  target: GraphNode;
}

export type NodeDegreeSizingMode = "all" | "none" | "out";

export interface GraphZoomConfig {
  autoFitMaxScale: number;
  maxScale: number;
  minScale: number;
  normalZoomSpeed: number;
  smoothDurationMs: number;
  smoothResponseRange: number;
  smoothStepLimit: number;
  smoothZoomSpeed: number;
}
