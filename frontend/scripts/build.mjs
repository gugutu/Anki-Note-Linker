import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

import { build } from "esbuild";

const projectRoot = resolve(import.meta.dirname, "..", "..");
const outputDirectory = resolve(projectRoot, "src", "addon", "web", "dist");

await rm(outputDirectory, { force: true, recursive: true });
await mkdir(resolve(outputDirectory, "vendor"), { recursive: true });
await build({
  absWorkingDir: projectRoot,
  bundle: true,
  entryNames: "[name]",
  entryPoints: {
    config: "frontend/src/config/app.ts",
    editor: "frontend/src/editor/app.ts",
    "graph-core": "frontend/src/graph/browser-api.ts",
    links: "frontend/src/links/app.ts",
    "new-graph": "frontend/src/graph/new-renderer.ts",
  },
  format: "iife",
  legalComments: "none",
  minify: false,
  outdir: outputDirectory,
  platform: "browser",
  sourcemap: "linked",
  target: ["es2020"],
});

await build({
  absWorkingDir: projectRoot,
  bundle: true,
  entryNames: "vendor/[name]",
  entryPoints: {
    d3: "frontend/src/vendor/d3.ts",
    "force-graph": "frontend/src/vendor/force-graph.ts",
    katex: "frontend/src/vendor/katex.ts",
    pixi: "frontend/src/vendor/pixi.ts",
  },
  format: "iife",
  legalComments: "inline",
  minify: false,
  outdir: outputDirectory,
  platform: "browser",
  sourcemap: false,
  target: ["es2020"],
});

const katexDistribution = resolve(projectRoot, "frontend", "node_modules", "katex", "dist");
await cp(resolve(katexDistribution, "katex.css"), resolve(outputDirectory, "vendor", "katex.css"));
await cp(resolve(katexDistribution, "fonts"), resolve(outputDirectory, "vendor", "fonts"), { recursive: true });
