import type { GraphZoomConfig } from "./types";

const DEFAULT_ZOOM_CONFIG: GraphZoomConfig = {
  autoFitMaxScale: 1.4,
  maxScale: 100,
  minScale: 0.01,
  normalZoomSpeed: 1,
  smoothDurationMs: 250,
  smoothResponseRange: 0.4,
  smoothStepLimit: 0.15,
  smoothZoomSpeed: 1,
};

function clampNumber(value: unknown, fallback: number, minimum: number, maximum: number): number {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? Math.min(maximum, Math.max(minimum, number)) : fallback;
}

export function normalizeZoomConfig(source: Record<string, unknown>): GraphZoomConfig {
  const result: GraphZoomConfig = {
    autoFitMaxScale: clampNumber(source.autoFitMaxScale, 1.4, 0.1, 10),
    maxScale: clampNumber(source.maxScale, 100, 1, 100),
    minScale: clampNumber(source.minScale, 0.01, 0.001, 1),
    normalZoomSpeed: clampNumber(source.normalZoomSpeed, 1, 0.1, 5),
    smoothDurationMs: clampNumber(source.smoothDurationMs, 250, 0, 1000),
    smoothResponseRange: clampNumber(source.smoothResponseRange, 0.4, 0.05, 2),
    smoothStepLimit: clampNumber(source.smoothStepLimit, 0.15, 0.01, 1),
    smoothZoomSpeed: clampNumber(source.smoothZoomSpeed, 1, 0.1, 5),
  };
  if (result.minScale >= result.maxScale) {
    result.minScale = DEFAULT_ZOOM_CONFIG.minScale;
    result.maxScale = DEFAULT_ZOOM_CONFIG.maxScale;
  }
  return result;
}

export function clampScale(scale: number, config: GraphZoomConfig): number {
  return Math.min(config.maxScale, Math.max(config.minScale, scale));
}

export function wheelZoomStep(deltaY: number, smooth: boolean, config: GraphZoomConfig): number {
  const divisor = smooth ? 1200 : 400;
  const speed = smooth ? config.smoothZoomSpeed : config.normalZoomSpeed;
  const rawStep = (-deltaY * speed) / divisor;
  return smooth
    ? Math.max(-config.smoothStepLimit, Math.min(config.smoothStepLimit, rawStep))
    : rawStep;
}
