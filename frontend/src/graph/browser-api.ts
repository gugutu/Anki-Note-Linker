import { preserveNodePosition, processNoteContent, updateNodeContent } from "./content";
import { clampScale, normalizeZoomConfig, wheelZoomStep } from "./zoom";

export const graphBrowserApi = {
  clampScale,
  normalizeZoomConfig,
  preserveNodePosition,
  processNoteContent,
  updateNodeContent,
  wheelZoomStep,
};

window.AnkiNoteLinkerGraph = graphBrowserApi;
