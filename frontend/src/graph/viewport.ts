import type { Container } from "pixi.js";

export interface PointTransform {
  toCanvasX(clientX: number): number;
  toCanvasY(clientY: number): number;
  toCanvasLength(clientLength: number): number;
  toClientX(canvasX: number): number;
  toClientY(canvasY: number): number;
  toClientLength(canvasLength: number): number;
}

export function createPointTransform(stage: Container): PointTransform {
  return {
    toCanvasX: (clientX) => (clientX - stage.x) / stage.scale.x,
    toCanvasY: (clientY) => (clientY - stage.y) / stage.scale.y,
    toCanvasLength: (clientLength) => clientLength / stage.scale.x,
    toClientX: (canvasX) => canvasX * stage.scale.x + stage.x,
    toClientY: (canvasY) => canvasY * stage.scale.x + stage.y,
    toClientLength: (canvasLength) => canvasLength * stage.scale.x,
  };
}

export class ViewportBoundary {
  bottom = 0;
  left = 0;
  right = 0;
  top = 0;

  constructor(
    private readonly stage: Container,
    private readonly transform: PointTransform,
  ) {}

  contains(x: number, y: number, radius = 0): boolean {
    return x + radius > this.left && x - radius < this.right && y + radius > this.top && y - radius < this.bottom;
  }

  update(updateHitArea = true): void {
    this.left = this.transform.toCanvasX(0);
    this.top = this.transform.toCanvasY(0);
    this.right = this.transform.toCanvasX(window.innerWidth);
    this.bottom = this.transform.toCanvasY(window.innerHeight);
    if (updateHitArea) {
      this.stage.hitArea = new PIXI.Rectangle(
        this.left,
        this.top,
        this.right - this.left,
        this.bottom - this.top,
      );
    }
  }
}
