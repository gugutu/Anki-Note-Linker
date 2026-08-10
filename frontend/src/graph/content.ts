import type { GraphNode } from "./types";

const SOUND_MARKUP = /\[sound:[^\]]+\]/g;

export interface ProcessedNoteContent {
  imageSrc?: string;
  text: string;
}

function resolveMediaSource(source: string, mediaServerUrl: string): string {
  if (/^(?:https?:|data:|file:)/i.test(source)) {
    return source;
  }
  return new URL(source, mediaServerUrl).href;
}

export function processNoteContent(
  html: string | null,
  imagePreviewEnabled: boolean,
  mediaServerUrl: string,
): ProcessedNoteContent {
  let content = html ?? "";
  if (content.includes("&lt;")) {
    const escapedDocument = new DOMParser().parseFromString(content, "text/html");
    content = escapedDocument.documentElement.textContent;
  }
  content = content
    .replace(/image-occlusion:[^>\s]*?:oi=1/g, "")
    .replace(/oi-data:[^>\s]*?:oi=1/g, "");
  const documentNode = new DOMParser().parseFromString(content, "text/html");
  const image = imagePreviewEnabled ? documentNode.querySelector("img") : null;
  const source = image?.getAttribute("src")?.trim();
  const imageSrc = source ? resolveMediaSource(source, mediaServerUrl) : undefined;

  for (const element of documentNode.querySelectorAll("img, script, style")) {
    element.remove();
  }
  const visibleText = documentNode.body.innerText || documentNode.body.textContent || "";
  const text = visibleText
    .replace(SOUND_MARKUP, "")
    .replace(/image-occlusion:.*?:oi=1/g, "")
    .replace(/rect:left=.*?:oi=1/g, "")
    .replace(/\n+/g, " ")
    .trim();
  return imageSrc === undefined ? { text } : { imageSrc, text };
}

export function updateNodeContent(
  node: GraphNode,
  imagePreviewEnabled: boolean,
  mediaServerUrl: string,
): GraphNode {
  const processed = processNoteContent(node.mainField, imagePreviewEnabled, mediaServerUrl);
  node.renderText = processed.text;
  if (processed.imageSrc === undefined) {
    delete node.imageSrc;
  } else {
    node.imageSrc = processed.imageSrc;
  }
  return node;
}

export function preserveNodePosition(nextNode: GraphNode, previousNode: GraphNode | undefined): GraphNode {
  if (previousNode === undefined) {
    return nextNode;
  }
  const simulationKeys = ["x", "y", "vx", "vy", "fx", "fy", "index"] as const;
  for (const key of simulationKeys) {
    const value = previousNode[key];
    if (value !== undefined) {
      Object.assign(nextNode, { [key]: value });
    }
  }
  return nextNode;
}
