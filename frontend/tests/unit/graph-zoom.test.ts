import { describe, expect, it } from "vitest";

import { clampScale, normalizeZoomConfig, wheelZoomStep } from "../../src/graph/zoom";

describe("normalizeZoomConfig", () => {
  it("clamps values and repairs invalid scale ordering", () => {
    const config = normalizeZoomConfig({
      maxScale: 1,
      minScale: 1,
      smoothDurationMs: 5000,
    });

    expect(config.minScale).toBe(0.01);
    expect(config.maxScale).toBe(100);
    expect(config.smoothDurationMs).toBe(1000);
  });
});

describe("zoom calculations", () => {
  const config = normalizeZoomConfig({ smoothStepLimit: 0.15 });

  it("caps smooth wheel steps", () => {
    expect(wheelZoomStep(-1000, true, config)).toBe(0.15);
    expect(wheelZoomStep(1000, true, config)).toBe(-0.15);
  });

  it("leaves normal wheel steps uncapped and clamps final scale", () => {
    expect(wheelZoomStep(-1000, false, config)).toBe(2.5);
    expect(clampScale(1000, config)).toBe(100);
    expect(clampScale(0, config)).toBe(0.01);
  });
});
