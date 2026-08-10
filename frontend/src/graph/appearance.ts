import type { Application } from "pixi.js";

export type RgbColor = [number, number, number];

export const DEFAULT_BACKGROUND: RgbColor = [16, 16, 32];

export function normalizeRgbColor(value: number[] | null | undefined): RgbColor {
  if (value?.length !== 3) {
    return DEFAULT_BACKGROUND;
  }
  return value.map((channel) => Math.max(0, Math.min(255, Math.round(channel)))) as RgbColor;
}

function contrastingTextColor([red, green, blue]: RgbColor): "#000" | "#fff" {
  const luminance = (
    (red / 255) ** 2.2 * 0.2126
    + (green / 255) ** 2.2 * 0.7152
    + (blue / 255) ** 2.2 * 0.0722
  ) ** 0.678;
  return luminance < 0.5 ? "#fff" : "#000";
}

export function applyGraphBackground(app: Application, color: RgbColor): void {
  app.renderer.background.color = `rgb(${color.join(", ")})`;
  document.documentElement.style.setProperty("--circleText-color", contrastingTextColor(color));
}
