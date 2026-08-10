import type { FederatedWheelEvent } from "pixi.js";

import type { GraphZoomConfig } from "./types";
import { clampScale, wheelZoomStep } from "./zoom";

export interface ZoomTarget {
  apply(scale: number, eventX: number, eventY: number): void;
  currentScale(): number;
  draggingCanvas(): boolean;
}

export class ZoomAnimation {
  private base = 1;
  private change = 0;
  private eventX = 0;
  private eventY = 0;
  private running = false;
  private time = 0;

  constructor(
    private readonly target: ZoomTarget,
    private readonly config: GraphZoomConfig,
    private readonly smooth: boolean,
  ) {}

  start(event: FederatedWheelEvent): void {
    if (event.deltaY === 0 || this.target.draggingCanvas()) {
      return;
    }
    const step = wheelZoomStep(event.deltaY, this.smooth, this.config);
    const current = this.target.currentScale();
    if ((current >= this.config.maxScale && step > 0) || (current <= this.config.minScale && step < 0)) {
      return;
    }

    if (this.running) {
      const currentTarget = this.base + this.change;
      const requestedTarget = step > 0 ? currentTarget * (1 + step) : currentTarget / (1 - step);
      const boundedTarget = Math.max(
        current * (1 - this.config.smoothResponseRange),
        Math.min(current * (1 + this.config.smoothResponseRange), requestedTarget),
      );
      this.change = boundedTarget - current;
    } else {
      this.change = step > 0 ? current * step : current / (1 - step) - current;
    }

    if (!this.smooth) {
      this.target.apply(clampScale(current + this.change, this.config), event.x, event.y);
      this.running = false;
      return;
    }
    this.time = 0;
    this.base = current;
    this.eventX = event.x;
    this.eventY = event.y;
    this.running = true;
  }

  tick(deltaMilliseconds: number): void {
    if (!this.running) {
      return;
    }
    this.time += deltaMilliseconds;
    const duration = this.config.smoothDurationMs;
    const progress = duration <= 0 ? 1 : Math.min(1, this.time / duration);
    const easedProgress = 1 - (1 - progress) ** 3;
    const value = clampScale(this.base + this.change * easedProgress, this.config);
    this.target.apply(value, this.eventX, this.eventY);
    if (progress >= 1 || value === this.config.minScale || value === this.config.maxScale) {
      this.running = false;
    }
  }
}

export class CenterAnimation {
  private baseX = 0;
  private baseY = 0;
  private changeX = 0;
  private changeY = 0;
  private running = false;
  private time = 0;

  constructor(private readonly apply: (x: number, y: number) => void) {}

  start(fromX: number, fromY: number, targetX: number, targetY: number): void {
    this.time = 0;
    this.baseX = fromX;
    this.baseY = fromY;
    this.changeX = targetX - fromX;
    this.changeY = targetY - fromY;
    this.running = true;
  }

  tick(deltaMilliseconds: number): void {
    if (!this.running) {
      return;
    }
    this.time += deltaMilliseconds;
    const duration = 180;
    const progress = Math.min(1, this.time / duration);
    const easedProgress = 1 - 2 ** (-10 * progress);
    this.apply(
      this.baseX + this.changeX * (progress === 1 ? 1 : easedProgress),
      this.baseY + this.changeY * (progress === 1 ? 1 : easedProgress),
    );
    if (progress === 1) {
      this.running = false;
    }
  }
}
