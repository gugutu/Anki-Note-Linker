import type { Graphics, GraphicsContext } from "pixi.js";

const POOL_CAPACITY = 384;
const CONTEXT_CAPACITY = 384;

interface ContextGroup {
  context: GraphicsContext;
  live: number;
}

export class ParticlePool {
  private readonly disposalContext = new PIXI.GraphicsContext();
  private readonly free: Graphics[] = [];
  private readonly groups = new Set<ContextGroup>();
  private owners = new WeakMap<Graphics, ContextGroup>();
  private current: ContextGroup | null = null;
  private destroyed = false;

  get size(): number {
    return this.free.length;
  }

  acquire(): Graphics {
    if (this.destroyed) throw new Error("Particle pool has been destroyed");
    const reused = this.free.pop();
    if (reused !== undefined) return reused;
    if (this.current === null || this.current.live >= CONTEXT_CAPACITY) {
      this.current = {
        context: new PIXI.GraphicsContext().circle(0, 0, 1).fill("rgb(102, 102, 112)"),
        live: 0,
      };
      this.groups.add(this.current);
    }
    const particle = new PIXI.Graphics(this.current.context);
    particle.eventMode = "none";
    this.current.live += 1;
    this.owners.set(particle, this.current);
    return particle;
  }

  release(particle: Graphics): void {
    particle.renderable = false;
    if (this.free.length < POOL_CAPACITY) {
      this.free.push(particle);
    } else {
      this.destroyParticle(particle);
    }
  }

  destroy(): void {
    if (this.destroyed) return;
    while (this.free.length > 0) {
      const particle = this.free.pop();
      if (particle !== undefined) this.destroyParticle(particle);
    }
    for (const group of this.groups) group.context.destroy();
    this.groups.clear();
    this.current = null;
    this.owners = new WeakMap();
    this.disposalContext.destroy();
    this.destroyed = true;
  }

  private destroyParticle(particle: Graphics): void {
    const group = this.owners.get(particle);
    if (group === undefined) throw new Error("Particle does not belong to this pool");
    // The public context setter removes the old context's listeners. This private,
    // unrendered context exists only for retirement and never owns renderer hooks.
    particle.context = this.disposalContext;
    particle.destroy();
    this.disposalContext.removeAllListeners();
    this.owners.delete(particle);
    group.live -= 1;
    if (group.live === 0) {
      group.context.destroy();
      this.groups.delete(group);
      if (this.current === group) this.current = null;
    }
  }
}
