type AddonConfig = Record<string, unknown>;

declare const PIXI: typeof import("pixi.js");
declare const ankiLanguage: string;
declare const ankiContext: "ADD_CARDS" | "BROWSER" | "EDIT_CURRENT" | "GLOBAL_GRAPH" | "REVIEWER";
declare const defaultConfig: AddonConfig;
declare const enableImagePreview: boolean;
declare const enableSmoothGraphZoom: boolean;
declare const graphZoomConfig: Record<string, unknown>;
declare const isMac: boolean;
declare const userConfig: AddonConfig;

declare const d3: typeof import("d3-force");

declare function getTr(message: string): string;
declare function pycmd(command: string): void;
declare function renderMathInElement(
  element: HTMLElement,
  options: {
    delimiters: { display: boolean; left: string; right: string }[];
    throwOnError: boolean;
  },
): void;

interface Window {
  AnkiNoteLinkerGraph: typeof import("./graph/browser-api").graphBrowserApi;
  AnkiNoteLinkerNewGraph: import("./graph/new-renderer").NewGraphBrowserApi;
  commands?: string[];
  loadNoteFields: (config: AddonConfig | null, useConfig?: boolean) => void;
  noteFieldsDisplayedInTheNoteSummaryConfigTemp: string[];
  readConfig: (config: AddonConfig) => void;
  reloadPage: (
    parentNodes?: import("./graph/types").GraphNode[],
    childNodes?: import("./graph/types").GraphNode[],
    waitingForShowAnswer?: boolean,
    showForwardLinkTitle?: boolean,
  ) => void;
  setConfig: () => void;
}
