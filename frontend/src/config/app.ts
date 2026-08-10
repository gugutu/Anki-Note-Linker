import { requireElement, setTranslatedLabel, setTranslatedText } from "../shared/dom";

interface NumberSetting {
  defaultValue: number;
  help: string;
  key: string;
  label: string;
  maximum: number;
  minimum: number;
  normalOnly?: boolean;
  smoothOnly?: boolean;
}

const graphZoomNumberSettings: readonly NumberSetting[] = [
  {
    defaultValue: 0.01,
    help: "Controls how far you can zoom out. Smaller values show more of a large graph at once; larger values keep nodes from becoming extremely tiny. Range: 0.001-1. Default: 0.01.",
    key: "graphZoom-zoomOutLimit",
    label: "Zoom-out limit",
    maximum: 1,
    minimum: 0.001,
  },
  {
    defaultValue: 100,
    help: "Controls how far you can zoom in. Larger values allow a closer view; smaller values stop zooming sooner. Range: 1-100. Default: 100.",
    key: "graphZoom-zoomInLimit",
    label: "Zoom-in limit",
    maximum: 100,
    minimum: 1,
  },
  {
    defaultValue: 1,
    help: "Controls wheel zoom sensitivity when smooth zoom is off. Lower values zoom more slowly; higher values zoom faster. Range: 0.1-5. Default: 1.",
    key: "graphZoom-normalZoomSpeed",
    label: "Normal zoom speed",
    maximum: 5,
    minimum: 0.1,
    normalOnly: true,
  },
  {
    defaultValue: 1,
    help: "Controls wheel zoom sensitivity when smooth zoom is on. Lower values zoom more slowly; higher values zoom faster. Range: 0.1-5. Default: 1.",
    key: "graphZoom-smoothZoomSpeed",
    label: "Smooth zoom speed",
    maximum: 5,
    minimum: 0.1,
    smoothOnly: true,
  },
  {
    defaultValue: 0.15,
    help: "Limits the size of each smooth zoom step. Lower values make rapid scrolling steadier; higher values react more strongly to each wheel event. Range: 0.01-1. Default: 0.15.",
    key: "graphZoom-smoothStepLimit",
    label: "Smooth zoom step limit",
    maximum: 1,
    minimum: 0.01,
    smoothOnly: true,
  },
  {
    defaultValue: 0.4,
    help: "Controls how far the animation target may get ahead of the current view while you keep scrolling. Lower values feel steadier; higher values feel more responsive but can overshoot more. Range: 0.05-2. Default: 0.4.",
    key: "graphZoom-smoothResponseRange",
    label: "Smooth zoom response range",
    maximum: 2,
    minimum: 0.05,
    smoothOnly: true,
  },
  {
    defaultValue: 250,
    help: "How long each smooth zoom animation lasts. Lower values feel snappier; higher values feel softer and slower. Range: 0-1000 ms. Default: 250 ms.",
    key: "graphZoom-smoothDurationMs",
    label: "Smooth zoom duration (ms)",
    maximum: 1000,
    minimum: 0,
    smoothOnly: true,
  },
  {
    defaultValue: 1.4,
    help: "Caps how much the graph may automatically zoom in when fitting nodes into view. Lower values keep the initial view wider; higher values let small graphs open closer. Range: 0.1-10. Default: 1.4.",
    key: "graphZoom-autoFitZoomInLimit",
    label: "Auto-fit zoom-in limit",
    maximum: 10,
    minimum: 0.1,
  },
];

const checkboxKeys = [
  "showLinksPageAutomatically",
  "showGraphPageAutomatically",
  "showLinksPageInReviewerAutomatically",
  "showGraphPageInReviewerAutomatically",
  "collapseClozeInLinksPage",
  "showForwardLinkTitleInLinksPage",
  "useHjpPreviewer",
  "enableImagePreview",
  "enableSmoothGraphZoom",
  "globalGraph-defaultShowSingleNode",
  "globalGraph-defaultShowTags",
  "globalGraph-defaultShowSuspended",
] as const;

const textKeys = [
  "splitRatio",
  "splitRatioBetweenLinksPageAndGraphPage",
  "splitRatioBetweenReviewerAndPanel",
  "linkMaxLines",
  "globalGraph-defaultSearchText",
  "globalGraph-defaultHighlightFilter",
  "shortcuts-copyNoteID",
  "shortcuts-copyNoteLink",
  "shortcuts-openNoteInNewWindow",
  "shortcuts-insertLinkWithClipboardID",
  "shortcuts-insertNewLink",
  "shortcuts-insertLinkTemplate",
] as const;

const colorKeys = [
  "globalGraph-nodeColor",
  "globalGraph-highlightedNodeColor",
  "globalGraph-tagNodeColor",
  "globalGraph-backgroundColor",
] as const;

let noteFields: string[] = [];

function input(id: string): HTMLInputElement {
  return requireElement(id, HTMLInputElement);
}

function clampNumber(value: unknown, fallback: number, minimum: number, maximum: number): number {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? Math.min(maximum, Math.max(minimum, number)) : fallback;
}

function booleanValue(config: AddonConfig, key: string, fallback = false): boolean {
  return typeof config[key] === "boolean" ? config[key] : fallback;
}

function stringValue(config: AddonConfig, key: string, fallback = ""): string {
  const value = config[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
}

function hexToRgb(hex: string): [number, number, number] {
  const match = /^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
  if (match === null) {
    throw new Error(`Invalid color value: ${hex}`);
  }
  return [Number.parseInt(match[1] ?? "00", 16), Number.parseInt(match[2] ?? "00", 16), Number.parseInt(match[3] ?? "00", 16)];
}

function rgbToHex(value: unknown): string {
  const rgb = Array.isArray(value) ? value.slice(0, 3) : [0, 0, 0];
  return `#${rgb.map((channel) => clampNumber(channel, 0, 0, 255).toString(16).padStart(2, "0")).join("")}`;
}

function readNumberSetting(config: AddonConfig, setting: NumberSetting): void {
  input(setting.key).value = String(
    clampNumber(config[setting.key], setting.defaultValue, setting.minimum, setting.maximum),
  );
}

function getNumberSetting(setting: NumberSetting): number {
  const element = input(setting.key);
  const value = clampNumber(element.value, setting.defaultValue, setting.minimum, setting.maximum);
  element.value = String(value);
  return value;
}

function updateSmoothGraphZoomControls(): void {
  const enabled = input("enableSmoothGraphZoom").checked;
  for (const setting of graphZoomNumberSettings.filter((item) => item.smoothOnly === true || item.normalOnly === true)) {
    const settingInput = input(setting.key);
    const helpButton = requireElement(`${setting.key}-help`, HTMLButtonElement);
    const row = settingInput.closest<HTMLElement>(".setting-row");
    const disabled = setting.smoothOnly === true ? !enabled : enabled;
    settingInput.disabled = disabled;
    helpButton.disabled = disabled;
    row?.classList.toggle("disabled-setting", disabled);
  }
}

function resizeScrollArea(): void {
  const scroll = requireElement("scroll", HTMLElement);
  const buttons = requireElement("buttons", HTMLElement);
  scroll.style.height = `${String(window.innerHeight - buttons.scrollHeight)}px`;
  scroll.style.maxWidth = `${String(window.innerWidth)}px`;
}

function renderNoteFields(): void {
  const container = requireElement("noteFieldsDisplayedInTheNoteSummary", HTMLElement);
  container.replaceChildren();
  noteFields.forEach((fieldName, index) => {
    const row = document.createElement("div");
    row.id = `fieldDiv${String(index)}`;
    const fieldInput = document.createElement("input");
    fieldInput.id = `field${String(index)}`;
    fieldInput.type = "text";
    fieldInput.value = fieldName;
    fieldInput.addEventListener("input", () => {
      noteFields[index] = fieldInput.value;
    });
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "X";
    removeButton.title = getTr("Remove field");
    removeButton.addEventListener("click", () => {
      noteFields.splice(index, 1);
      renderNoteFields();
    });
    row.append(fieldInput, removeButton);
    container.append(row);
  });
  window.noteFieldsDisplayedInTheNoteSummaryConfigTemp = noteFields;
}

function loadNoteFields(config: AddonConfig | null, useConfig = true): void {
  if (useConfig) {
    const configuredFields = config?.noteFieldsDisplayedInTheNoteSummary;
    noteFields = Array.isArray(configuredFields)
      ? configuredFields.filter((field): field is string => typeof field === "string")
      : [];
  } else {
    noteFields = window.noteFieldsDisplayedInTheNoteSummaryConfigTemp;
  }
  renderNoteFields();
}

function readConfig(config: AddonConfig): void {
  for (const key of checkboxKeys) {
    const fallback = key === "enableImagePreview";
    input(key).checked = booleanValue(config, key, fallback);
  }
  for (const setting of graphZoomNumberSettings) {
    readNumberSetting(config, setting);
  }
  updateSmoothGraphZoomControls();

  input("location-left-radio").checked = config.location === "left";
  input("location-right-radio").checked = config.location !== "left";
  input("positionRelativeToReviewer-left-radio").checked = config.positionRelativeToReviewer === "left";
  input("positionRelativeToReviewer-right-radio").checked = config.positionRelativeToReviewer !== "left";
  for (const key of textKeys) {
    input(key).value = stringValue(config, key);
  }
  loadNoteFields(config);

  const degreeSizing = stringValue(config, "globalGraph-nodeDegreeSizing", "none");
  input("globalGraph-nodeDegreeSizing-none-radio").checked = degreeSizing === "none";
  input("globalGraph-nodeDegreeSizing-out-radio").checked = degreeSizing === "out";
  input("globalGraph-nodeDegreeSizing-all-radio").checked = degreeSizing === "all";
  for (const key of colorKeys) {
    input(key).value = rgbToHex(config[key]);
  }
}

function setConfig(): void {
  const ratioPattern = /^\d+:\d+$/;
  const ratioKeys = ["splitRatio", "splitRatioBetweenLinksPageAndGraphPage", "splitRatioBetweenReviewerAndPanel"];
  if (ratioKeys.some((key) => !ratioPattern.test(input(key).value))) {
    alert(getTr('The format of "split ratio" is incorrect'));
    return;
  }
  if (input("linkMaxLines").value === "" || Number.parseInt(input("linkMaxLines").value, 10) === 0) {
    input("linkMaxLines").value = stringValue(userConfig, "linkMaxLines", "5");
  }

  for (const key of checkboxKeys) {
    userConfig[key] = input(key).checked;
  }
  const zoomValues: Record<string, number> = {};
  for (const setting of graphZoomNumberSettings) {
    zoomValues[setting.key] = getNumberSetting(setting);
  }
  if ((zoomValues["graphZoom-zoomOutLimit"] ?? 0.01) >= (zoomValues["graphZoom-zoomInLimit"] ?? 100)) {
    alert(getTr("Zoom-out limit must be smaller than zoom-in limit."));
    return;
  }
  Object.assign(userConfig, zoomValues);

  userConfig.location = input("location-left-radio").checked ? "left" : "right";
  userConfig.positionRelativeToReviewer = input("positionRelativeToReviewer-left-radio").checked ? "left" : "right";
  for (const key of textKeys) {
    userConfig[key] = input(key).value;
  }
  userConfig.noteFieldsDisplayedInTheNoteSummary = [...noteFields];
  userConfig["globalGraph-nodeDegreeSizing"] = input("globalGraph-nodeDegreeSizing-none-radio").checked
    ? "none"
    : input("globalGraph-nodeDegreeSizing-out-radio").checked
      ? "out"
      : "all";
  for (const key of colorKeys) {
    userConfig[key] = hexToRgb(input(key).value);
  }
  pycmd(`AnkiNoteLinker-config-ok${JSON.stringify(userConfig)}`);
}

function initializeTranslations(): void {
  const labels: Readonly<Record<string, string>> = {
    collapseClozeInLinksPage: "Collapse cloze in links panel",
    enableImagePreview: "Enable Image Previews",
    enableSmoothGraphZoom: "Enable Smooth Graph Zoom",
    "globalGraph-backgroundColor": "Graph background color",
    "globalGraph-defaultHighlightFilter": "Default filter text for highlighted nodes",
    "globalGraph-defaultSearchText": "Default search text",
    "globalGraph-defaultShowSingleNode": "Default display of single nodes",
    "globalGraph-defaultShowTags": "Default display of tag nodes",
    "globalGraph-defaultShowSuspended": "Default display of notes with all cards suspended",
    "globalGraph-highlightedNodeColor": "Highlighted node color",
    "globalGraph-nodeColor": "Node color",
    "globalGraph-nodeDegreeSizing": "Node size scaling by link count",
    "globalGraph-tagNodeColor": "Tag node color",
    linkMaxLines: "Max displayed lines per link in links panel",
    location: "The position of links/graph panel relative to the editor",
    noteFieldsDisplayedInTheNoteSummary: "Note fields displayed in the note summary",
    positionRelativeToReviewer: "The position of links/graph panel relative to the reviewer",
    "shortcuts-copyNoteID": "Copy current note ID",
    "shortcuts-copyNoteLink": "Copy current note link",
    "shortcuts-insertLinkTemplate": "Insert link template",
    "shortcuts-insertLinkWithClipboardID": "Insert link with copied note ID",
    "shortcuts-insertNewLink": "Insert new link",
    "shortcuts-openNoteInNewWindow": "Open current note in new window",
    showForwardLinkTitleInLinksPage: "Show forward link title above note summary in links panel",
    showGraphPageAutomatically: "Automatically show graph panel when entering editor",
    showGraphPageInReviewerAutomatically: "Automatically show graph panel when entering reviewer",
    showLinksPageAutomatically: "Automatically show links panel when entering editor",
    showLinksPageInReviewerAutomatically: "Automatically show links panel when entering reviewer",
    splitRatio: "Split ratio between editor and panels",
    splitRatioBetweenLinksPageAndGraphPage: "Split ratio between links panel and graph panel",
    splitRatioBetweenReviewerAndPanel: "Split ratio between reviewer and panel",
    useHjpPreviewer: 'If the "hjp-linkmaster" add-on is installed, use its previewer',
  };
  for (const [className, message] of Object.entries(labels)) {
    setTranslatedLabel(className, message);
  }
  for (const setting of graphZoomNumberSettings) {
    setTranslatedLabel(setting.key, setting.label);
    requireElement(`${setting.key}-help`, HTMLButtonElement).addEventListener("click", () => {
      alert(getTr(setting.help));
    });
  }

  const text: Readonly<Record<string, string>> = {
    advancedGraphZoomSummary: "Advanced Graph Zoom Settings",
    "button-cancel": "Cancel",
    "button-ok": "OK",
    "button-restoreDefaults": "Restore Defaults",
    "globalGraph-nodeDegreeSizing-all": "Total links",
    "globalGraph-nodeDegreeSizing-none": "Do not scale",
    "globalGraph-nodeDegreeSizing-out": "Outgoing links only",
    "location-left": "left",
    "location-right": "right",
    "positionRelativeToReviewer-left": "left",
    "positionRelativeToReviewer-right": "right",
    "title-basic": "Basic",
    "title-globalGraph": "Global Relationship Graph",
    "title-shortcuts": "Shortcut keys",
  };
  for (const [id, message] of Object.entries(text)) {
    setTranslatedText(id, message);
  }
}

window.loadNoteFields = loadNoteFields;
window.readConfig = readConfig;
window.setConfig = setConfig;
window.noteFieldsDisplayedInTheNoteSummaryConfigTemp = noteFields;

initializeTranslations();
requireElement("enableSmoothGraphZoom-help", HTMLButtonElement).addEventListener("click", () => {
  alert(getTr("Smoothly animates mouse wheel zoom. Leave off if zoom should feel immediate."));
});
input("enableSmoothGraphZoom").addEventListener("change", updateSmoothGraphZoomControls);
if (isMac) {
  requireElement("mac-shortcuts-help", HTMLButtonElement).style.display = "inline-flex";
}
window.addEventListener("resize", resizeScrollArea);
resizeScrollArea();
readConfig(userConfig);
