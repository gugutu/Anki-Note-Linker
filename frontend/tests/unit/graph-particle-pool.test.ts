import { Graphics, GraphicsContext } from "pixi.js";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ParticlePool } from "../../src/graph/particle-pool";

vi.hoisted(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("graph particle pool", () => {
  it("bounds both the free pool and each context's listeners, and releases overflow", () => {
    vi.stubGlobal("PIXI", { Graphics, GraphicsContext });
    const pool = new ParticlePool();
    const particles = Array.from({ length: 900 }, () => pool.acquire());
    const contexts = [...new Set(particles.map((particle) => particle.context))];
    expect(contexts).toHaveLength(3);
    expect(contexts.every((context) => context.listenerCount("update") <= 384)).toBe(true);
    for (const particle of particles) pool.release(particle);
    expect(pool.size).toBe(384);
    expect(particles.filter((particle) => particle.destroyed)).toHaveLength(516);
    expect(contexts.reduce((sum, context) => sum + context.listenerCount("update"), 0)).toBe(384);
    expect(contexts.reduce((sum, context) => sum + context.listenerCount("unload"), 0)).toBe(384);
    const reused = Array.from({ length: 384 }, () => pool.acquire());
    expect(reused.every((particle) => particles.includes(particle) && !particle.destroyed)).toBe(true);
    expect(pool.size).toBe(0);
    for (const particle of reused) pool.release(particle);
    pool.destroy();
    pool.destroy();
    expect(particles.every((particle) => particle.destroyed)).toBe(true);
    expect(contexts.every((context) => context.destroyed && context.listenerCount("update") === 0)).toBe(true);
  });

  it("keeps unrelated context listeners when retiring an individual particle", () => {
    vi.stubGlobal("PIXI", { Graphics, GraphicsContext });
    const pool = new ParticlePool();
    const particles = Array.from({ length: 386 }, () => pool.acquire());
    const retained = particles[385];
    const retired = particles[384];
    if (retained === undefined || retired === undefined) throw new Error("Missing test particles");
    const context = retained.context;
    const listener = vi.fn();
    context.on("update", listener);
    for (const particle of particles.slice(0, 385)) pool.release(particle);
    expect(retired.destroyed).toBe(true);
    expect(retained.destroyed).toBe(false);
    expect(context.destroyed).toBe(false);
    expect(context.listenerCount("update")).toBe(2);
    context.emit("update", context);
    expect(listener).toHaveBeenCalledOnce();
    retained.destroy();
    pool.destroy();
    expect(context.destroyed).toBe(true);
  });
});
